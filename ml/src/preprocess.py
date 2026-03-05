import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
import joblib

DATA_PATH = Path("ml/data/processed/heart_disease_clean.csv")
OUT_DIR = Path("ml/data/processed")
MODEL_DIR = Path("ml/models")

TARGET = "target"

# Numeric features (continuous)
NUM_COLS = ["age", "trestbps", "chol", "thalach", "oldpeak"]

# Categorical-coded features (should be one-hot encoded)
CAT_COLS = ["sex", "cp", "fbs", "restecg", "exang", "slope", "ca", "thal"]

def build_preprocessor():
    numeric = Pipeline(steps=[
        ("scaler", StandardScaler())
    ])

    categorical = Pipeline(steps=[
        ("onehot", OneHotEncoder(handle_unknown="ignore"))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric, NUM_COLS),
            ("cat", categorical, CAT_COLS),
        ],
        remainder="drop"
    )
    return preprocessor

def main():
    df = pd.read_csv(DATA_PATH)

    X = df.drop(columns=[TARGET])
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    preprocessor = build_preprocessor()
    preprocessor.fit(X_train)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Save preprocessor for later API inference
    joblib.dump(preprocessor, MODEL_DIR / "preprocessor.joblib")

    # Save split data (raw X/y) for training scripts
    X_train.to_csv(OUT_DIR / "X_train_raw.csv", index=False)
    X_test.to_csv(OUT_DIR / "X_test_raw.csv", index=False)
    y_train.to_csv(OUT_DIR / "y_train.csv", index=False)
    y_test.to_csv(OUT_DIR / "y_test.csv", index=False)

    print(" Preprocessor saved:", MODEL_DIR / "preprocessor.joblib")
    print(" Train/Test raw split saved in:", OUT_DIR)
    print("Train:", X_train.shape, "Test:", X_test.shape)

if __name__ == "__main__":
    main()