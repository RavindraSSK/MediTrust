"""
Decode the raw Kaggle heart-disease CSV into the canonical clinical encoding,
create a stratified train/test split and fit the inference preprocessor.

Run from anywhere:  python3 ml/src/preprocess.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SRC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))

from data_dictionary import (  # noqa: E402
    CATEGORICAL_FEATURES,
    CATEGORY_CODES,
    ENCODING_VERSION,
    FEATURE_ORDER,
    NUMERIC_FEATURES,
    TARGET,
    decode_kaggle_frame,
)

ML_DIR = SRC_DIR.parent
RAW_PATH = ML_DIR / "data" / "raw" / "heart_kaggle.csv"
OUT_DIR = ML_DIR / "data" / "processed"
CLEAN_PATH = OUT_DIR / "heart_disease_clean.csv"
MODEL_DIR = ML_DIR / "models"

RANDOM_STATE = 42
TEST_SIZE = 0.2


def build_preprocessor() -> ColumnTransformer:
    numeric = Pipeline(steps=[("scaler", StandardScaler())])
    categorical = Pipeline(
        steps=[
            (
                "onehot",
                OneHotEncoder(
                    categories=[CATEGORY_CODES[c] for c in CATEGORICAL_FEATURES],
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
            )
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric, NUMERIC_FEATURES),
            ("cat", categorical, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


def load_clean_frame() -> pd.DataFrame:
    raw = pd.read_csv(RAW_PATH, encoding="utf-8-sig")
    return decode_kaggle_frame(raw)


def main() -> None:
    df = load_clean_frame()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN_PATH, index=False)

    X = df[FEATURE_ORDER]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    preprocessor = build_preprocessor()
    preprocessor.fit(X_train)
    joblib.dump(preprocessor, MODEL_DIR / "preprocessor.joblib")

    X_train.to_csv(OUT_DIR / "X_train_raw.csv", index=False)
    X_test.to_csv(OUT_DIR / "X_test_raw.csv", index=False)
    y_train.to_csv(OUT_DIR / "y_train.csv", index=False)
    y_test.to_csv(OUT_DIR / "y_test.csv", index=False)

    summary = {
        "encoding_version": ENCODING_VERSION,
        "source_file": RAW_PATH.name,
        "rows_raw": int(len(pd.read_csv(RAW_PATH, encoding="utf-8-sig"))),
        "rows_clean": int(len(df)),
        "rows_dropped": int(df.attrs.get("rows_dropped", 0)),
        "positives": int(y.sum()),
        "prevalence": round(float(y.mean()), 4),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "test_size": TEST_SIZE,
        "random_state": RANDOM_STATE,
        "feature_names_out": list(preprocessor.get_feature_names_out()),
    }
    (OUT_DIR / "dataset_summary.json").write_text(json.dumps(summary, indent=2))

    print(
        f"Clean canonical dataset -> {CLEAN_PATH} ({summary['rows_clean']} rows, "
        f"{summary['rows_dropped']} dropped, prevalence {summary['prevalence']:.3f})"
    )
    print(f"Preprocessor saved -> {MODEL_DIR / 'preprocessor.joblib'}")
    print(f"Train: {X_train.shape}  Test: {X_test.shape}")


if __name__ == "__main__":
    main()
