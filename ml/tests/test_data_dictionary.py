import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_dictionary import (  # noqa: E402
    CATEGORY_CODES,
    CATEGORY_LABELS,
    FEATURE_ORDER,
    decode_kaggle_frame,
    describe_value,
    validate_record,
)

RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "heart_kaggle.csv"


def test_every_categorical_code_has_a_label():
    for feature, codes in CATEGORY_CODES.items():
        assert set(codes) == set(CATEGORY_LABELS[feature])


def test_decoding_inverts_label_and_recodes_categories():
    raw = pd.read_csv(RAW, encoding="utf-8-sig")
    clean = decode_kaggle_frame(raw)

    assert list(clean.columns) == FEATURE_ORDER + ["target"]
    assert set(clean["cp"].unique()) <= {1, 2, 3, 4}
    assert set(clean["thal"].unique()) <= {3, 6, 7}
    assert set(clean["slope"].unique()) <= {1, 2, 3}
    assert clean["ca"].max() <= 3
    # Kaggle target=1 rows are the healthy (UCI num == 0) patients.
    assert clean["target"].mean() < 0.5
    # Disease should correlate with exercise-induced angina and ST depression.
    diseased = clean[clean["target"] == 1]
    healthy = clean[clean["target"] == 0]
    assert diseased["exang"].mean() > healthy["exang"].mean()
    assert diseased["oldpeak"].mean() > healthy["oldpeak"].mean()
    assert diseased["ca"].mean() > healthy["ca"].mean()
    assert diseased["thalach"].mean() < healthy["thalach"].mean()


def test_validate_record_flags_bad_codes():
    good = dict(
        age=58,
        sex=1,
        cp=4,
        trestbps=156,
        chol=286,
        fbs=1,
        restecg=1,
        thalach=118,
        exang=1,
        oldpeak=2.8,
        slope=2,
        ca=2,
        thal=7,
    )
    assert validate_record(good) == []
    bad = dict(good, cp=0, thal=2, trestbps=900)
    errors = validate_record(bad)
    assert any("cp" in e for e in errors)
    assert any("thal" in e for e in errors)
    assert any("trestbps" in e for e in errors)


def test_describe_value():
    assert describe_value("cp", 4) == "asymptomatic"
    assert describe_value("thal", 7) == "reversible defect"
    assert describe_value("trestbps", 156) == "156 mmHg"
