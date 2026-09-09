"""
Canonical clinical encoding for the MediTrust cardiovascular risk model.

This module is the single source of truth for feature names, allowed value
codes, human-readable labels and validation ranges. The canonical encoding
follows the original UCI Cleveland Heart Disease attribute documentation
(Detrano et al., 1989), which is also what clinicians see in the UI:

    cp       1 typical angina, 2 atypical angina, 3 non-anginal pain, 4 asymptomatic
    restecg  0 normal, 1 ST-T wave abnormality, 2 probable/definite LV hypertrophy
    slope    1 upsloping, 2 flat, 3 downsloping
    thal     3 normal, 6 fixed defect, 7 reversible defect
    ca       0-3 major vessels coloured by fluoroscopy
    target   1 = angiographic coronary disease (UCI ``num`` > 0), 0 = no disease

The widely redistributed Kaggle ``heart.csv`` copy of this dataset silently
re-coded the categorical attributes and, crucially, INVERTED the label: its
``target = 1`` rows are the UCI ``num = 0`` (no disease) patients. Training on
that file as-is produces a model whose "risk" is really the probability of
being healthy. ``KAGGLE_TO_CANONICAL`` records the exact re-coding so the raw
file can be decoded deterministically and the mistake cannot recur.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

ENCODING_VERSION = "cleveland-canonical-v2"
TARGET = "target"

FEATURE_ORDER = [
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

NUMERIC_FEATURES = ["age", "trestbps", "chol", "thalach", "oldpeak"]
CATEGORICAL_FEATURES = ["sex", "cp", "fbs", "restecg", "exang", "slope", "ca", "thal"]

# Allowed codes per categorical feature (canonical encoding).
CATEGORY_CODES: dict[str, list[int]] = {
    "sex": [0, 1],
    "cp": [1, 2, 3, 4],
    "fbs": [0, 1],
    "restecg": [0, 1, 2],
    "exang": [0, 1],
    "slope": [1, 2, 3],
    "ca": [0, 1, 2, 3],
    "thal": [3, 6, 7],
}

CATEGORY_LABELS: dict[str, dict[int, str]] = {
    "sex": {0: "female", 1: "male"},
    "cp": {
        1: "typical angina",
        2: "atypical angina",
        3: "non-anginal pain",
        4: "asymptomatic",
    },
    "fbs": {0: "fasting blood sugar 120 mg/dL or below", 1: "fasting blood sugar above 120 mg/dL"},
    "restecg": {
        0: "normal",
        1: "ST-T wave abnormality",
        2: "left ventricular hypertrophy pattern",
    },
    "exang": {0: "absent", 1: "present"},
    "slope": {1: "upsloping", 2: "flat", 3: "downsloping"},
    "ca": {0: "0 vessels", 1: "1 vessel", 2: "2 vessels", 3: "3 vessels"},
    "thal": {3: "normal", 6: "fixed defect", 7: "reversible defect"},
}

FEATURE_LABELS: dict[str, str] = {
    "age": "Age",
    "sex": "Sex",
    "cp": "Chest pain type",
    "trestbps": "Resting blood pressure",
    "chol": "Total cholesterol",
    "fbs": "Fasting blood sugar",
    "restecg": "Resting ECG result",
    "thalach": "Maximum heart rate achieved",
    "exang": "Exercise-induced angina",
    "oldpeak": "Exercise-induced ST depression",
    "slope": "Peak exercise ST-segment slope",
    "ca": "Major vessels on fluoroscopy",
    "thal": "Thallium stress test result",
}

FEATURE_UNITS: dict[str, str] = {
    "age": "years",
    "trestbps": "mmHg",
    "chol": "mg/dL",
    "thalach": "bpm",
    "oldpeak": "mm",
}

# Plausibility bounds used for API validation (inclusive).
NUMERIC_RANGES: dict[str, tuple[float, float]] = {
    "age": (1, 120),
    "trestbps": (50, 260),
    "chol": (50, 800),
    "thalach": (30, 250),
    "oldpeak": (0.0, 10.0),
}

# Mapping from the Kaggle ``heart.csv`` re-coding back to the canonical codes.
# ``None`` marks values that were missing ("?") in the original UCI file.
KAGGLE_TO_CANONICAL: dict[str, dict[int, int | None]] = {
    "cp": {0: 4, 1: 2, 2: 3, 3: 1},
    "restecg": {0: 2, 1: 0, 2: 1},
    "slope": {0: 3, 1: 2, 2: 1},
    "thal": {0: None, 1: 6, 2: 3, 3: 7},
    "ca": {0: 0, 1: 1, 2: 2, 3: 3, 4: None},
    # Kaggle target=1 corresponds to UCI num=0 (no disease).
    TARGET: {0: 1, 1: 0},
}


def decode_kaggle_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert a Kaggle-encoded frame into the canonical encoding.

    Rows whose categorical values decode to ``None`` (missing in UCI) are
    dropped, as are exact duplicate rows.
    """
    out = df.copy()
    out.columns = [str(c).strip().lstrip("﻿") for c in out.columns]

    missing = [c for c in FEATURE_ORDER + [TARGET] if c not in out.columns]
    if missing:
        raise ValueError(f"Kaggle frame is missing columns: {missing}")

    for column, mapping in KAGGLE_TO_CANONICAL.items():
        unknown = sorted(set(out[column].unique()) - set(mapping))
        if unknown:
            raise ValueError(f"Unexpected {column} codes in Kaggle frame: {unknown}")
        out[column] = out[column].map(mapping)

    before = len(out)
    out = out.dropna(subset=list(KAGGLE_TO_CANONICAL))
    out = out.drop_duplicates()
    out = out.reset_index(drop=True)

    for column in CATEGORICAL_FEATURES + [TARGET]:
        out[column] = out[column].astype(int)
    for column in NUMERIC_FEATURES:
        out[column] = out[column].astype(float)

    out.attrs["rows_dropped"] = before - len(out)
    return out[FEATURE_ORDER + [TARGET]]


def validate_record(record: dict[str, Any]) -> list[str]:
    """Return a list of human-readable validation errors (empty when valid)."""
    errors: list[str] = []

    for feature in FEATURE_ORDER:
        if feature not in record or record[feature] is None:
            errors.append(f"{feature} is required.")

    for feature, (low, high) in NUMERIC_RANGES.items():
        value = record.get(feature)
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            errors.append(f"{feature} must be a number.")
            continue
        if not (low <= numeric <= high):
            errors.append(f"{feature} must be between {low:g} and {high:g}.")

    for feature, codes in CATEGORY_CODES.items():
        value = record.get(feature)
        if value is None:
            continue
        try:
            code = int(value)
        except (TypeError, ValueError):
            errors.append(f"{feature} must be one of {codes}.")
            continue
        if code != float(value) or code not in codes:
            errors.append(f"{feature} must be one of {codes}.")

    return errors


def describe_value(feature: str, value: Any) -> str:
    """Human-readable description of a single feature value."""
    if feature in CATEGORY_LABELS:
        try:
            code = int(round(float(value)))
        except (TypeError, ValueError):
            return str(value)
        return CATEGORY_LABELS[feature].get(code, str(value))

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)

    text = f"{numeric:g}"
    unit = FEATURE_UNITS.get(feature)
    return f"{text} {unit}" if unit else text
