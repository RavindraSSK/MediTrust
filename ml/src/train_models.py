import pandas as pd
import joblib
from pathlib import Path

from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

DATA_DIR = Path("ml/data/processed")
MODEL_DIR = Path("ml/models")

PREPROCESSOR_PATH = MODEL_DIR / "preprocessor.joblib"

X_TRAIN_RAW = DATA_DIR / "X_train_raw.csv"
X_TEST_RAW = DATA_DIR / "X_test_raw.csv"
Y_TRAIN = DATA_DIR / "y_train.csv"
Y_TEST = DATA_DIR / "y_test.csv"

def eval_metrics(name, model, X_test_t, y_test):
    y_pred = model.predict(X_test_t)
    y_prob = model.predict_proba(X_test_t)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)

    print(f"\n=== {name} ===")
    print(f"Accuracy: {acc:.4f}")
    print(f"F1-score:  {f1:.4f}")
    print(f"ROC-AUC:   {auc:.4f}")

    return {"model": name, "accuracy": acc, "f1": f1, "roc_auc": auc}

def main():
    # Load raw splits
    X_train = pd.read_csv(X_TRAIN_RAW)
    X_test = pd.read_csv(X_TEST_RAW)
    y_train = pd.read_csv(Y_TRAIN).values.ravel()
    y_test = pd.read_csv(Y_TEST).values.ravel()

    # Load preprocessor and transform
    preprocessor = joblib.load(PREPROCESSOR_PATH)
    X_train_t = preprocessor.transform(X_train)
    X_test_t = preprocessor.transform(X_test)

    # Models
    logreg = LogisticRegression(max_iter=2000)
    rf = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        class_weight="balanced"
    )

    # Train
    logreg.fit(X_train_t, y_train)
    rf.fit(X_train_t, y_train)

    # Evaluate
    results = []
    results.append(eval_metrics("LogisticRegression", logreg, X_test_t, y_test))
    results.append(eval_metrics("RandomForest", rf, X_test_t, y_test))

    # Pick best by ROC-AUC then F1
    best = sorted(results, key=lambda x: (x["roc_auc"], x["f1"]), reverse=True)[0]
    best_name = best["model"]

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    best_model = logreg if best_name == "LogisticRegression" else rf
    joblib.dump(best_model, MODEL_DIR / "model.joblib")

    pd.DataFrame(results).to_csv(MODEL_DIR / "model_results.csv", index=False)

    print("\n Best model:", best_name)
    print(" Saved best model -> ml/models/model.joblib")
    print(" Saved metrics -> ml/models/model_results.csv")

if __name__ == "__main__":
    main()