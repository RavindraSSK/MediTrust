from pathlib import Path
import joblib
import pandas as pd
import numpy as np
import shap


BASE_DIR = Path(__file__).resolve().parents[2]

MODEL_PATH_CANDIDATES = [
    BASE_DIR / "ml" / "models" / "model.joblib",
    BASE_DIR / "backend" / "ml" / "models" / "model.joblib",
]
PREPROCESSOR_PATH_CANDIDATES = [
    BASE_DIR / "ml" / "models" / "preprocessor.joblib",
    BASE_DIR / "backend" / "ml" / "models" / "preprocessor.joblib",
]
BACKGROUND_DATA_PATH_CANDIDATES = [
    BASE_DIR / "ml" / "data" / "processed" / "heart_disease_clean.csv",
    BASE_DIR / "backend" / "ml" / "data" / "processed" / "heart_disease_clean.csv",
]


RAW_FEATURE_ORDER = [
    "age",
    "sex",
    "cp",
    "trestbps",
    "chol",
    "fbs",
    "restecg",
    "thalach",
    "exang",
    "oldpeak",
    "slope",
    "ca",
    "thal",
]

_model = None
_preprocessor = None
_explainer = None
_background_dense = None


def _resolve_existing_path(candidates: list[Path], label: str) -> Path:
    for path in candidates:
        if path.exists():
            return path

    searched = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"{label} not found. Looked in: {searched}")


def _load_background_frame() -> pd.DataFrame:
    """
    Load a small representative background dataset for SHAP.
    This should be the cleaned training-style feature table.
    """
    background_path = None
    for candidate in BACKGROUND_DATA_PATH_CANDIDATES:
        if candidate.exists():
            background_path = candidate
            break

    if background_path is None:
        raise FileNotFoundError(
            "Background data not found. "
            f"Looked in: {', '.join(str(path) for path in BACKGROUND_DATA_PATH_CANDIDATES)}"
        )

    df = pd.read_csv(background_path)

    # Keep only model input columns
    missing = [col for col in RAW_FEATURE_ORDER if col not in df.columns]
    if missing:
        raise ValueError(
            f"Background data is missing required columns: {missing}"
        )

    df = df[RAW_FEATURE_ORDER].copy()

    # Use a small sample for SHAP background
    if len(df) > 100:
        df = df.sample(n=100, random_state=42)

    return df


def _to_dense(matrix):
    if hasattr(matrix, "toarray"):
        return matrix.toarray()
    return np.asarray(matrix)


def _get_feature_names(preprocessor) -> list[str]:
    if hasattr(preprocessor, "get_feature_names_out"):
        return list(preprocessor.get_feature_names_out())
    return RAW_FEATURE_ORDER.copy()


def _load_artifacts():
    global _model, _preprocessor, _explainer, _background_dense

    if _preprocessor is None:
        _preprocessor = joblib.load(
            _resolve_existing_path(PREPROCESSOR_PATH_CANDIDATES, "Preprocessor")
        )

    if _model is None:
        _model = joblib.load(
            _resolve_existing_path(MODEL_PATH_CANDIDATES, "Model")
        )
        if not hasattr(_model, "multi_class"):
            _model.multi_class = "auto"

    if _background_dense is None and _explainer is None:
        try:
            background_df = _load_background_frame()
            background_transformed = _preprocessor.transform(background_df)
            _background_dense = _to_dense(background_transformed)
        except Exception:
            _background_dense = None

    if _explainer is None and _background_dense is not None:
        # Preferred for tree models: probability-space explanation
        try:
            _explainer = shap.TreeExplainer(
                _model,
                data=_background_dense,
                model_output="probability"
            )
        except Exception:
            # Generic explainer fallback with proper background/masker
            _explainer = shap.Explainer(
                _model.predict_proba,
                _background_dense,
                feature_names=_get_feature_names(_preprocessor)
            )

    return _model, _preprocessor, _explainer, _background_dense


def _make_dataframe(payload: dict) -> pd.DataFrame:
    row = {feature: payload[feature] for feature in RAW_FEATURE_ORDER}
    return pd.DataFrame([row], columns=RAW_FEATURE_ORDER)


def predict_probability(payload: dict) -> float:
    model, preprocessor, _, _ = _load_artifacts()
    df = _make_dataframe(payload)
    X_t = preprocessor.transform(df)
    prob = model.predict_proba(X_t)[:, 1][0]
    return float(prob)


def _normalize_feature_name(name: str) -> str:
    cleaned = name

    if "__" in cleaned:
        cleaned = cleaned.split("__", 1)[1]

    for raw in RAW_FEATURE_ORDER:
        if cleaned == raw:
            return raw
        if cleaned.startswith(raw + "_"):
            return raw

    return cleaned


def _extract_shap_array(shap_output):
    """
    Normalize SHAP outputs into a 1D contribution vector for class 1 probability.
    """
    values = getattr(shap_output, "values", shap_output)
    arr = np.asarray(values)

    if arr.ndim == 3:
        # Expected cases:
        # (n_samples, n_features, n_classes)
        # or (n_samples, n_classes, n_features)
        if arr.shape[-1] == 2:
            arr = arr[0, :, 1]
        elif arr.shape[1] == 2:
            arr = arr[0, 1, :]
        else:
            arr = arr[0].reshape(-1)
    elif arr.ndim == 2:
        arr = arr[0]
    elif arr.ndim == 1:
        arr = arr
    else:
        arr = arr.reshape(-1)

    return np.asarray(arr, dtype=float)


def _get_base_value(shap_output):
    """
    Get a base value compatible with class 1 probability explanation.
    """
    base_values = getattr(shap_output, "base_values", None)

    if base_values is None:
        return 0.0

    arr = np.asarray(base_values)

    if arr.ndim == 0:
        return float(arr)

    if arr.ndim == 1:
        if len(arr) == 2:
            return float(arr[1])
        return float(arr[0])

    if arr.ndim == 2:
        if arr.shape[-1] == 2:
            return float(arr[0, 1])
        return float(arr[0, 0])

    return float(arr.reshape(-1)[0])


def _aggregate_shap_values(feature_names: list[str], shap_values: np.ndarray, payload: dict):
    """
    Aggregate transformed-feature SHAP values back to raw feature names.
    Example:
      num__chol -> chol
      cat__cp_3 -> cp
    """
    grouped = {}

    for idx, name in enumerate(feature_names):
        base_name = _normalize_feature_name(name)
        grouped[base_name] = grouped.get(base_name, 0.0) + float(shap_values[idx])

    explanations = []
    for feature, impact in grouped.items():
        if feature not in payload:
            continue

        explanations.append(
            {
                "feature": feature,
                "value": float(payload[feature]),
                "impact": float(impact),  # do not round here
                "direction": "increases risk" if impact >= 0 else "decreases risk",
            }
        )

    explanations.sort(key=lambda item: abs(item["impact"]), reverse=True)
    return explanations


def _aggregate_linear_contributions(model, preprocessor, payload: dict):
    """
    Fallback explanation path when SHAP background data is unavailable.
    For linear models, use transformed-feature coefficient contributions.
    """
    if not hasattr(model, "coef_"):
        return []

    df = _make_dataframe(payload)
    X_t = preprocessor.transform(df)
    X_dense = _to_dense(X_t)
    feature_names = _get_feature_names(preprocessor)
    contributions = X_dense[0] * np.asarray(model.coef_[0], dtype=float)
    return _aggregate_shap_values(feature_names, contributions, payload)


def explain_prediction(payload: dict, risk_level: str):
    """
    Returns:
      top_features: top SHAP-ranked features
      all_features: all SHAP-ranked features
      base_value: base probability
      summary: summary sentence
    """
    model, preprocessor, explainer, _ = _load_artifacts()

    df = _make_dataframe(payload)
    X_t = preprocessor.transform(df)
    X_dense = _to_dense(X_t)
    feature_names = _get_feature_names(preprocessor)

    if explainer is not None:
        shap_output = explainer(X_dense)
        shap_values = _extract_shap_array(shap_output)
        base_value = _get_base_value(shap_output)
        all_features = _aggregate_shap_values(feature_names, shap_values, payload)
    else:
        base_value = float(getattr(model, "intercept_", [0.0])[0])
        all_features = _aggregate_linear_contributions(model, preprocessor, payload)

    top_features = all_features[:6]

    if not top_features:
        summary = (
            "The model generated a prediction, but detailed SHAP-based feature contributions "
            "were not available for this request."
        )
        return [], [], float(base_value), summary

    increasing = [item["feature"] for item in top_features if item["direction"] == "increases risk"]
    decreasing = [item["feature"] for item in top_features if item["direction"] == "decreases risk"]

    if increasing and decreasing:
        summary = (
            f"The SHAP explanation indicates that {', '.join(increasing)} are the strongest "
            f"factors increasing the estimated cardiovascular risk, while "
            f"{', '.join(decreasing)} offset the prediction to some extent. "
            f"Overall, this pattern is consistent with a {risk_level.lower()} predicted risk profile."
        )
    elif increasing:
        summary = (
            f"The SHAP explanation indicates that {', '.join(increasing)} are the strongest "
            f"factors increasing the estimated cardiovascular risk. "
            f"Overall, this pattern is consistent with a {risk_level.lower()} predicted risk profile."
        )
    else:
        summary = (
            f"The SHAP explanation indicates that {', '.join(decreasing)} are the strongest "
            f"factors supporting a lower estimated cardiovascular risk. "
            f"Overall, this pattern is consistent with a {risk_level.lower()} predicted risk profile."
        )

    return top_features, all_features, float(base_value), summary
