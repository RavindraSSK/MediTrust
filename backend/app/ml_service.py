from pathlib import Path
import joblib
import os
import pandas as pd
import numpy as np
import shap
from dotenv import load_dotenv
from google import genai
from google.genai import types


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / "backend" / ".env"
load_dotenv()
load_dotenv(dotenv_path=ENV_PATH)

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
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_TIMEOUT_MS = int(os.getenv("GEMINI_TIMEOUT_MS", "10000"))
GEMINI_SYSTEM_INSTRUCTION = (
    "You are a cardiologist's AI assistant. Summarize heart risk scores in under 50 words. "
    'Translate "ca" to "vessel health", "cp" to "chest pain type", and "thal" to "stress test results". '
    "focus on why the score is high or low."
)

CLINICAL_FEATURE_LABELS = {
    "age": "age",
    "chol": "total cholesterol",
    "trestbps": "resting blood pressure",
    "oldpeak": "exercise-induced ST depression",
    "exang": "exercise-induced angina",
    "thalach": "maximum heart rate achieved",
    "ca": "major vessel involvement",
    "thal": "thallium stress test result",
    "cp": "chest pain pattern",
    "restecg": "resting ECG findings",
    "fbs": "fasting blood sugar",
    "slope": "ST-segment slope",
    "sex": "sex",
}

GEMINI_FEATURE_LABELS = {
    "age": "age",
    "sex": "sex",
    "cp": "chest pain type",
    "trestbps": "resting blood pressure",
    "chol": "cholesterol",
    "fbs": "fasting blood sugar",
    "restecg": "resting ECG result",
    "thalach": "maximum heart rate",
    "exang": "exercise-induced angina",
    "oldpeak": "ST depression",
    "slope": "ST-segment slope",
    "ca": "major vessel involvement",
    "thal": "thallium stress test result",
}


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


def _get_clinical_feature_label(feature: str) -> str:
    return CLINICAL_FEATURE_LABELS.get(feature, feature.replace("_", " "))


def _get_gemini_feature_label(feature: str) -> str:
    return GEMINI_FEATURE_LABELS.get(feature, feature.replace("_", " "))


def _get_gemini_client(api_key: str) -> genai.Client:
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=GEMINI_TIMEOUT_MS,
            clientArgs={"trust_env": False},
            asyncClientArgs={"trust_env": False},
        ),
    )


def _coerce_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_risk_percent(risk_percent: float) -> float | None:
    normalized = _coerce_float(risk_percent)
    if normalized is None:
        return None
    if 0.0 <= normalized <= 1.0:
        normalized *= 100.0
    return max(0.0, min(normalized, 100.0))


def _extract_shap_pairs(shap_values: dict) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    if not isinstance(shap_values, dict):
        return [], []

    pairs = []
    for feature, value in shap_values.items():
        impact = value.get("impact") if isinstance(value, dict) else value
        numeric_impact = _coerce_float(impact)
        if numeric_impact is None:
            continue
        pairs.append((str(feature), numeric_impact))

    positive = [item for item in pairs if item[1] > 0]
    negative = [item for item in pairs if item[1] < 0]
    positive.sort(key=lambda item: item[1], reverse=True)
    negative.sort(key=lambda item: item[1])
    return positive[:2], negative[:2]


def _format_feature_group(features: list[tuple[str, float]], empty_text: str) -> str:
    if not features:
        return empty_text
    labels = [_get_gemini_feature_label(feature) for feature, _ in features]
    return ", ".join(labels)


def _build_clinical_summary_prompt(
    risk_percent: float,
    positive_features: list[tuple[str, float]],
    negative_features: list[tuple[str, float]],
) -> str:
    drivers_text = _format_feature_group(positive_features, "no clear risk drivers identified")
    protective_text = _format_feature_group(negative_features, "no clear protective factors identified")

    return (
        f"Heart risk score: {int(round(risk_percent))}%.\n"
        f"Risk Drivers: {drivers_text}.\n"
        f"Protective Factors: {protective_text}.\n"
        "Write exactly 2 sentences under 50 words total. "
        "Sentence 1 should explain what is pushing risk higher. "
        "Sentence 2 should explain what is lowering risk and end with a short final clinical observation. "
        "Use simple clinical language only. Do not mention AI, SHAP, patient names, or raw values."
    )


def get_clinical_summary(risk_percent: float, shap_values: dict) -> str | None:
    load_dotenv(dotenv_path=ENV_PATH)

    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    normalized_risk = _normalize_risk_percent(risk_percent)
    if not api_key or normalized_risk is None or not isinstance(shap_values, dict):
        return None

    positive_features, negative_features = _extract_shap_pairs(shap_values)
    if not positive_features and not negative_features:
        return None

    prompt = _build_clinical_summary_prompt(normalized_risk, positive_features, negative_features)

    try:
        client = _get_gemini_client(api_key)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=GEMINI_SYSTEM_INSTRUCTION,
                temperature=0.2,
                max_output_tokens=80,
            ),
        )
        text = getattr(response, "text", None)
        return text.strip() if text else None
    except Exception as e:
        print("Gemini error:", e)
        return None


def _build_gemini_prompt(
    top_features: list[dict],
    risk_level: str,
    risk_probability: float | None = None,
    triage_recommendation: str | None = None,
    explanation_summary: str | None = None,
) -> str:
    percent_text = "N/A"
    normalized_probability = _coerce_float(risk_probability)
    if normalized_probability is not None:
        if 0.0 <= normalized_probability <= 1.0:
            normalized_probability *= 100.0
        percent_text = f"{int(round(max(0.0, min(normalized_probability, 100.0))))}%"

    feature_descriptions = []
    for item in top_features[:3]:
        if not isinstance(item, dict) or not item.get("feature"):
            continue

        label = _get_gemini_feature_label(str(item["feature"]))
        direction = str(item.get("direction") or "affects risk").strip().lower()
        if direction == "increases risk":
            direction_text = "increased estimated risk"
        elif direction == "decreases risk":
            direction_text = "lowered estimated risk"
        else:
            direction_text = direction

        feature_descriptions.append(f"{label} ({direction_text})")

    features_text = ", ".join(feature_descriptions) if feature_descriptions else "No major contributing factors available"
    recommendation_text = (triage_recommendation or "No triage recommendation provided").strip()
    explanation_text = (explanation_summary or "No explanation summary provided").strip()

    return (
        "Generate a 2 sentence clinical summary for this cardiovascular risk assessment. "
        "Use simple professional language. Do not mention SHAP or AI. "
        "Do not give diagnosis. Do not add medication advice.\n"
        f"Risk level: {risk_level}.\n"
        f"Risk probability: {percent_text}.\n"
        f"Triage recommendation: {recommendation_text}.\n"
        f"Clinical explanation: {explanation_text}.\n"
        f"Key contributing factors: {features_text}."
    )

def generate_gemini_summary(
    top_features: list[dict],
    risk_level: str,
    risk_probability: float | None = None,
    triage_recommendation: str | None = None,
    explanation_summary: str | None = None,
) -> str | None:
    if not top_features:
        return None

    load_dotenv()
    load_dotenv(dotenv_path=ENV_PATH)
    api_key = os.getenv("GEMINI_API_KEY")

    print("Gemini key loaded:", bool(api_key))
    if not api_key:
        print("Gemini skipped: GEMINI_API_KEY not found")
        return None

    prompt = _build_gemini_prompt(
        top_features=top_features,
        risk_level=risk_level,
        risk_probability=risk_probability,
        triage_recommendation=triage_recommendation,
        explanation_summary=explanation_summary,
    )
    proxy_keys = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ]
    broken_proxy_values = {"http://127.0.0.1:9", "https://127.0.0.1:9"}
    removed_proxies = {}

    try:
        for key in proxy_keys:
            value = os.environ.get(key)
            if value in broken_proxy_values:
                removed_proxies[key] = value
                os.environ.pop(key, None)

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        summary_text = response.text.strip() if getattr(response, "text", None) else None
        print("Gemini summary generated:", bool(summary_text))
        return summary_text
    except Exception as e:
        print("Gemini error:", repr(e))
        return None
    finally:
        for key, value in removed_proxies.items():
            os.environ[key] = value


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
