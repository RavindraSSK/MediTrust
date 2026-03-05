from pathlib import Path
import joblib
import pandas as pd

# NOTE: these paths are relative to repo root when you run uvicorn from repo root
MODEL_PATH = Path("ml/models/model.joblib")
PREPROCESSOR_PATH = Path("ml/models/preprocessor.joblib")

_model = None
_preprocessor = None

def _load_artifacts():
    global _model, _preprocessor

    if _preprocessor is None:
        if not PREPROCESSOR_PATH.exists():
            raise FileNotFoundError(f"Preprocessor not found: {PREPROCESSOR_PATH}")
        _preprocessor = joblib.load(PREPROCESSOR_PATH)

    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
        _model = joblib.load(MODEL_PATH)

    return _model, _preprocessor

def predict_probability(payload: dict) -> float:
    """
    Returns probability of disease (class 1).
    """
    model, preprocessor = _load_artifacts()
    df = pd.DataFrame([payload])
    X_t = preprocessor.transform(df)
    prob = model.predict_proba(X_t)[:, 1][0]
    return float(prob)