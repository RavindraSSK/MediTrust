"""
Model registry, inference and patient-level SHAP explanations.

Artifacts (``model.joblib``, ``preprocessor.joblib``, ``model_metadata.json``,
``global_feature_importance.json``) are produced by ``ml/src/train_models.py``
and loaded from ``MODEL_DIR`` (default ``ml/models``). When ``MODEL_S3_URI`` is
set the artifacts are first synchronised from S3 so EC2 instances always run
the model that CI published.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import joblib
import numpy as np
import pandas as pd

from .clinical_encoding import ENCODING_VERSION, FEATURE_ORDER, feature_label, validate_record
from .config import settings
from .observability import MODEL_INFO, MODEL_LOADED

logger = logging.getLogger(__name__)

REQUIRED_ARTIFACTS = ("model.joblib", "preprocessor.joblib")
OPTIONAL_ARTIFACTS = ("model_metadata.json", "global_feature_importance.json", "roc_curve.json", "model_results.csv")
BACKGROUND_SAMPLE_SIZE = 100
TOP_FEATURES = 6


class ModelNotLoadedError(RuntimeError):
    pass


class InvalidClinicalInputError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass
class LoadedModel:
    model: object
    preprocessor: object
    metadata: dict
    feature_names: list[str]
    background: np.ndarray | None
    explainer: object | None
    global_importance: dict | None
    loaded_at: float
    source: str

    @property
    def name(self) -> str:
        return str(self.metadata.get("model_name") or type(self.model).__name__)

    @property
    def version(self) -> str:
        return str(self.metadata.get("model_version") or "unversioned")


def _to_dense(matrix) -> np.ndarray:
    if hasattr(matrix, "toarray"):
        return matrix.toarray()
    return np.asarray(matrix, dtype=float)


def _positive_probability(model):
    def predict(X):
        return np.asarray(model.predict_proba(X))[:, 1]

    return predict


def _is_tree_model(model) -> bool:
    return hasattr(model, "estimators_") or hasattr(model, "get_booster")


def _build_explainer(model, background: np.ndarray | None, feature_names: list[str]):
    if background is None:
        return None
    import shap

    if _is_tree_model(model):
        try:
            return shap.TreeExplainer(
                model, data=background, model_output="probability", feature_perturbation="interventional"
            )
        except Exception as exc:  # noqa: BLE001
            logger.info("TreeExplainer unavailable (%s); using permutation explainer", exc)
    return shap.Explainer(_positive_probability(model), background, feature_names=feature_names)


def _extract_shap_array(shap_output) -> np.ndarray:
    values = np.asarray(getattr(shap_output, "values", shap_output))
    if values.ndim == 3:
        if values.shape[-1] == 2:
            values = values[0, :, 1]
        elif values.shape[1] == 2:
            values = values[0, 1, :]
        else:
            values = values[0].reshape(-1)
    elif values.ndim == 2:
        values = values[0]
    else:
        values = values.reshape(-1)
    return np.asarray(values, dtype=float)


def _extract_base_value(shap_output) -> float:
    base = getattr(shap_output, "base_values", None)
    if base is None:
        return 0.0
    arr = np.asarray(base, dtype=float)
    if arr.ndim == 0:
        return float(arr)
    if arr.ndim == 1:
        return float(arr[1]) if arr.shape[0] == 2 else float(arr[0])
    if arr.ndim == 2:
        return float(arr[0, 1]) if arr.shape[-1] == 2 else float(arr[0, 0])
    return float(arr.reshape(-1)[0])


def raw_feature_for_column(column: str) -> str:
    cleaned = column.split("__", 1)[1] if "__" in column else column
    for raw in FEATURE_ORDER:
        if cleaned == raw or cleaned.startswith(raw + "_"):
            return raw
    return cleaned


def aggregate_contributions(feature_names: list[str], contributions: np.ndarray, payload: dict) -> list[dict]:
    grouped: dict[str, float] = {}
    for idx, name in enumerate(feature_names):
        raw = raw_feature_for_column(name)
        grouped[raw] = grouped.get(raw, 0.0) + float(contributions[idx])

    explanations = []
    for feature, impact in grouped.items():
        if feature not in payload:
            continue
        explanations.append(
            {
                "feature": feature,
                "label": feature_label(feature),
                "value": float(payload[feature]),
                "impact": float(impact),
                "direction": "increases risk" if impact >= 0 else "decreases risk",
            }
        )
    explanations.sort(key=lambda item: abs(item["impact"]), reverse=True)
    return explanations


def build_explanation_summary(top_features: list[dict], risk_level: str) -> str:
    if not top_features:
        return (
            "The model generated a prediction, but detailed SHAP-based feature contributions "
            "were not available for this request."
        )
    increasing = [item["label"].lower() for item in top_features if item["direction"] == "increases risk"]
    decreasing = [item["label"].lower() for item in top_features if item["direction"] == "decreases risk"]
    level = risk_level.lower()
    if increasing and decreasing:
        return (
            f"SHAP attribution indicates that {', '.join(increasing)} are the strongest factors increasing "
            f"the estimated probability of coronary artery disease, while {', '.join(decreasing)} offset the "
            f"prediction to some extent. Overall this pattern is consistent with a {level} predicted risk profile."
        )
    if increasing:
        return (
            f"SHAP attribution indicates that {', '.join(increasing)} are the strongest factors increasing "
            f"the estimated probability of coronary artery disease. Overall this pattern is consistent with a "
            f"{level} predicted risk profile."
        )
    return (
        f"SHAP attribution indicates that {', '.join(decreasing)} are the strongest factors supporting a lower "
        f"estimated probability of coronary artery disease. Overall this pattern is consistent with a {level} "
        "predicted risk profile."
    )


class ModelService:
    def __init__(
        self,
        model_dir: Path | None = None,
        background_path: Path | None = None,
        s3_uri: str | None = None,
    ):
        self.model_dir = Path(model_dir or settings.model_dir)
        self.background_path = Path(background_path or settings.background_data_path)
        self.s3_uri = s3_uri if s3_uri is not None else settings.model_s3_uri
        self._loaded: LoadedModel | None = None
        self._lock = threading.Lock()
        self.last_error: str | None = None

    # ------------------------------------------------------------------ loading
    @property
    def is_loaded(self) -> bool:
        return self._loaded is not None

    def sync_from_s3(self) -> bool:
        """Download artifacts from ``MODEL_S3_URI`` (s3://bucket/prefix). Never raises."""
        if not self.s3_uri:
            return False
        try:
            import boto3
        except ImportError:
            logger.warning("MODEL_S3_URI is set but boto3 is not installed; using local artifacts")
            return False

        parsed = urlparse(self.s3_uri)
        bucket = parsed.netloc
        prefix = parsed.path.strip("/")
        if parsed.scheme != "s3" or not bucket:
            logger.warning("MODEL_S3_URI must look like s3://bucket/prefix (got %r)", self.s3_uri)
            return False

        client = boto3.client("s3", region_name=settings.aws_region or None)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        downloaded = 0
        for name in REQUIRED_ARTIFACTS + OPTIONAL_ARTIFACTS:
            key = f"{prefix}/{name}" if prefix else name
            target = self.model_dir / name
            try:
                client.download_file(bucket, key, str(target))
                downloaded += 1
            except Exception as exc:  # noqa: BLE001
                if name in REQUIRED_ARTIFACTS:
                    logger.error("Failed to download required artifact %s from s3://%s/%s: %s", name, bucket, key, exc)
                    return False
                logger.info("Optional artifact %s not found in S3 (%s)", name, exc)
        logger.info("Synchronised %d model artifacts from %s", downloaded, self.s3_uri)
        return downloaded > 0

    def _load_background(self) -> pd.DataFrame | None:
        if not self.background_path.exists():
            logger.warning("SHAP background data not found at %s", self.background_path)
            return None
        df = pd.read_csv(self.background_path, encoding="utf-8-sig")
        missing = [c for c in FEATURE_ORDER if c not in df.columns]
        if missing:
            logger.warning("Background data is missing columns %s", missing)
            return None
        df = df[FEATURE_ORDER].copy()
        if len(df) > BACKGROUND_SAMPLE_SIZE:
            df = df.sample(n=BACKGROUND_SAMPLE_SIZE, random_state=42)
        return df

    def load(self, force: bool = False) -> LoadedModel:
        with self._lock:
            if self._loaded is not None and not force:
                return self._loaded

            source = "local"
            if self.sync_from_s3():
                source = self.s3_uri

            model_path = self.model_dir / "model.joblib"
            preprocessor_path = self.model_dir / "preprocessor.joblib"
            if not model_path.exists() or not preprocessor_path.exists():
                self.last_error = f"Model artifacts not found in {self.model_dir}"
                MODEL_LOADED.set(0)
                raise ModelNotLoadedError(self.last_error)

            try:
                model = joblib.load(model_path)
                preprocessor = joblib.load(preprocessor_path)
                if not hasattr(model, "multi_class"):  # older LogisticRegression pickles
                    try:
                        model.multi_class = "auto"
                    except Exception:  # noqa: BLE001
                        pass

                metadata: dict = {}
                metadata_path = self.model_dir / "model_metadata.json"
                if metadata_path.exists():
                    metadata = json.loads(metadata_path.read_text())

                global_importance = None
                importance_path = self.model_dir / "global_feature_importance.json"
                if importance_path.exists():
                    global_importance = json.loads(importance_path.read_text())
                elif metadata.get("global_feature_importance"):
                    global_importance = metadata["global_feature_importance"]

                if hasattr(preprocessor, "get_feature_names_out"):
                    feature_names = list(preprocessor.get_feature_names_out())
                else:
                    feature_names = list(FEATURE_ORDER)

                background = None
                background_df = self._load_background()
                if background_df is not None:
                    background = _to_dense(preprocessor.transform(background_df))

                explainer = None
                try:
                    explainer = _build_explainer(model, background, feature_names)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Could not build SHAP explainer: %s", exc)

                loaded = LoadedModel(
                    model=model,
                    preprocessor=preprocessor,
                    metadata=metadata,
                    feature_names=feature_names,
                    background=background,
                    explainer=explainer,
                    global_importance=global_importance,
                    loaded_at=time.time(),
                    source=source,
                )
            except ModelNotLoadedError:
                raise
            except Exception as exc:  # noqa: BLE001
                self.last_error = f"Failed to load model: {exc}"
                MODEL_LOADED.set(0)
                logger.exception("Failed to load model artifacts")
                raise ModelNotLoadedError(self.last_error) from exc

            encoding = loaded.metadata.get("encoding_version")
            if encoding and encoding != ENCODING_VERSION:
                logger.warning(
                    "Model encoding %s differs from API encoding %s; retrain with ml/src/train_models.py",
                    encoding,
                    ENCODING_VERSION,
                )

            self._loaded = loaded
            self.last_error = None
            MODEL_LOADED.set(1)
            MODEL_INFO.labels(loaded.name, loaded.version).set(1)
            logger.info(
                "Loaded %s (version %s) from %s with %d transformed features; explainer=%s",
                loaded.name,
                loaded.version,
                source,
                len(feature_names),
                type(explainer).__name__ if explainer else "none",
            )
            return loaded

    def ensure_loaded(self) -> LoadedModel:
        if self._loaded is None:
            return self.load()
        return self._loaded

    # ---------------------------------------------------------------- inference
    @staticmethod
    def _frame(payload: dict) -> pd.DataFrame:
        row = {feature: payload[feature] for feature in FEATURE_ORDER}
        return pd.DataFrame([row], columns=FEATURE_ORDER)

    @staticmethod
    def validate(payload: dict) -> dict:
        errors = validate_record(payload)
        if errors:
            raise InvalidClinicalInputError(errors)
        cleaned = {}
        for feature in FEATURE_ORDER:
            value = payload[feature]
            cleaned[feature] = (
                float(value) if feature in ("age", "trestbps", "chol", "thalach", "oldpeak") else int(value)
            )
        return cleaned

    def predict_probability(self, payload: dict) -> float:
        loaded = self.ensure_loaded()
        cleaned = self.validate(payload)
        X_t = loaded.preprocessor.transform(self._frame(cleaned))
        prob = float(np.asarray(loaded.model.predict_proba(X_t))[:, 1][0])
        return min(max(prob, 0.0), 1.0)

    def explain(self, payload: dict, risk_level: str) -> tuple[list[dict], list[dict], float, str]:
        loaded = self.ensure_loaded()
        cleaned = self.validate(payload)
        X_dense = _to_dense(loaded.preprocessor.transform(self._frame(cleaned)))

        if loaded.explainer is not None:
            shap_output = loaded.explainer(X_dense)
            contributions = _extract_shap_array(shap_output)
            base_value = _extract_base_value(shap_output)
            all_features = aggregate_contributions(loaded.feature_names, contributions, cleaned)
        elif hasattr(loaded.model, "coef_"):
            coef = np.asarray(loaded.model.coef_, dtype=float).reshape(-1)
            contributions = X_dense[0] * coef
            base_value = float(np.asarray(getattr(loaded.model, "intercept_", [0.0])).reshape(-1)[0])
            all_features = aggregate_contributions(loaded.feature_names, contributions, cleaned)
        else:
            all_features, base_value = [], 0.0

        top_features = all_features[:TOP_FEATURES]
        summary = build_explanation_summary(top_features, risk_level)
        return top_features, all_features, float(base_value), summary

    # ------------------------------------------------------------------- info
    def info(self) -> dict:
        try:
            loaded = self.ensure_loaded()
        except ModelNotLoadedError as exc:
            return {"status": "unavailable", "error": str(exc)}

        meta = loaded.metadata
        return {
            "status": "ready",
            "model_name": loaded.name,
            "model_class": meta.get("model_class") or type(loaded.model).__name__,
            "model_version": loaded.version,
            "trained_at": meta.get("trained_at"),
            "encoding_version": meta.get("encoding_version", ENCODING_VERSION),
            "label_definition": meta.get("label_definition"),
            "positive_class_meaning": meta.get("positive_class_meaning"),
            "features": meta.get("features", FEATURE_ORDER),
            "selection_criterion": meta.get("selection_criterion"),
            "cross_validation": meta.get("cross_validation"),
            "test_metrics": meta.get("test_metrics"),
            "thresholds": meta.get("thresholds"),
            "risk_bands": meta.get("risk_bands"),
            "leaderboard": meta.get("leaderboard"),
            "global_feature_importance": loaded.global_importance,
            "library_versions": meta.get("library_versions"),
            "dataset": meta.get("dataset"),
            "explainer": type(loaded.explainer).__name__ if loaded.explainer else None,
            "artifact_source": loaded.source,
            "loaded_at": loaded.loaded_at,
        }

    @property
    def model_version(self) -> str:
        return self._loaded.version if self._loaded else "unloaded"


model_service = ModelService()


# Backwards-compatible module-level helpers -----------------------------------
def predict_probability(payload: dict) -> float:
    return model_service.predict_probability(payload)


def explain_prediction(payload: dict, risk_level: str):
    return model_service.explain(payload, risk_level)
