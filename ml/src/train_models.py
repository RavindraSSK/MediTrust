"""
Benchmark Logistic Regression, Random Forest and XGBoost for cardiovascular
risk prediction with repeated stratified cross-validation and hyperparameter
search, select the best model by cross-validated ROC-AUC, tune clinically
oriented decision thresholds on out-of-fold predictions, and persist the model
together with a model card (``model_metadata.json``).

Run from anywhere:  python3 ml/src/train_models.py
Prerequisite:       python3 ml/src/preprocess.py
"""

from __future__ import annotations

import json
import platform
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from scipy.stats import loguniform, randint, uniform
from sklearn.calibration import calibration_curve
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import (
    GridSearchCV,
    RandomizedSearchCV,
    RepeatedStratifiedKFold,
    StratifiedKFold,
    cross_val_predict,
)

SRC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))

from data_dictionary import ENCODING_VERSION, FEATURE_ORDER  # noqa: E402
from evaluate import binary_metrics, optimize_thresholds, roc_points, threshold_sweep  # noqa: E402
from explain_global import compute_global_importance, plot_global_importance  # noqa: E402

ML_DIR = SRC_DIR.parent
DATA_DIR = ML_DIR / "data" / "processed"
MODEL_DIR = ML_DIR / "models"
REPORT_DIR = ML_DIR / "reports"

RANDOM_STATE = 42
CV = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=RANDOM_STATE)
OOF_CV = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
MIN_SENSITIVITY = 0.95
MIN_SPECIFICITY = 0.85
N_JOBS = -1

try:
    import xgboost
    from xgboost import XGBClassifier

    XGBOOST_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when xgboost is absent
    XGBOOST_AVAILABLE = False


def candidate_searches() -> dict[str, object]:
    searches: dict[str, object] = {
        "LogisticRegression": GridSearchCV(
            LogisticRegression(max_iter=5000, solver="lbfgs"),
            param_grid={
                "C": [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0],
                "class_weight": [None, "balanced"],
            },
            scoring="roc_auc",
            cv=CV,
            n_jobs=N_JOBS,
            refit=True,
        ),
        "RandomForest": RandomizedSearchCV(
            RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=1),
            param_distributions={
                "n_estimators": [200, 300, 500],
                "max_depth": [None, 3, 4, 6, 8, 12],
                "min_samples_leaf": [1, 2, 3, 5, 8],
                "max_features": ["sqrt", 0.5, None],
                "class_weight": [None, "balanced"],
            },
            n_iter=30,
            scoring="roc_auc",
            cv=CV,
            n_jobs=N_JOBS,
            random_state=RANDOM_STATE,
            refit=True,
        ),
    }

    if XGBOOST_AVAILABLE:
        searches["XGBoost"] = RandomizedSearchCV(
            XGBClassifier(
                objective="binary:logistic",
                eval_metric="logloss",
                tree_method="hist",
                random_state=RANDOM_STATE,
                n_jobs=1,
            ),
            param_distributions={
                "n_estimators": randint(100, 600),
                "max_depth": randint(2, 7),
                "learning_rate": loguniform(0.01, 0.3),
                "subsample": uniform(0.6, 0.4),
                "colsample_bytree": uniform(0.5, 0.5),
                "min_child_weight": randint(1, 8),
                "reg_lambda": loguniform(0.3, 10),
                "gamma": uniform(0.0, 1.0),
            },
            n_iter=40,
            scoring="roc_auc",
            cv=CV,
            n_jobs=N_JOBS,
            random_state=RANDOM_STATE,
            refit=True,
        )
    return searches


def json_safe(value):
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def plot_roc_curves(curves: dict[str, dict], aucs: dict[str, float], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.5, 6))
    for name, curve in curves.items():
        ax.plot(curve["fpr"], curve["tpr"], lw=2, label=f"{name} (AUC = {aucs[name]:.3f})")
    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.6)
    ax.set_xlabel("False positive rate (1 - specificity)")
    ax.set_ylabel("True positive rate (sensitivity)")
    ax.set_title("ROC curves on the held-out test set")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_threshold_analysis(sweep: pd.DataFrame, rule_out: float, rule_in: float, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.plot(sweep["threshold"], sweep["sensitivity"], label="Sensitivity", lw=2)
    ax.plot(sweep["threshold"], sweep["specificity"], label="Specificity", lw=2)
    ax.plot(sweep["threshold"], sweep["ppv"], label="PPV", lw=1.5, alpha=0.8)
    ax.plot(sweep["threshold"], sweep["npv"], label="NPV", lw=1.5, alpha=0.8)
    ax.axvspan(0, rule_out, color="#16a34a", alpha=0.08, label="Low band")
    ax.axvspan(rule_out, rule_in, color="#f59e0b", alpha=0.10, label="Medium band")
    ax.axvspan(rule_in, 1, color="#ef4444", alpha=0.08, label="High band")
    ax.axvline(rule_out, color="#16a34a", ls="--", lw=1)
    ax.axvline(rule_in, color="#ef4444", ls="--", lw=1)
    ax.set_xlabel("Decision threshold on predicted probability of disease")
    ax.set_ylabel("Metric (out-of-fold, training data)")
    ax.set_title(f"Threshold analysis: rule-out {rule_out:.2f}, rule-in {rule_in:.2f}")
    ax.set_ylim(0, 1.02)
    ax.legend(loc="lower left", fontsize=8, ncol=2)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_calibration(y_test, probabilities: dict[str, np.ndarray], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 6))
    for name, probs in probabilities.items():
        frac_pos, mean_pred = calibration_curve(y_test, probs, n_bins=6, strategy="quantile")
        ax.plot(mean_pred, frac_pos, marker="o", lw=1.5, label=name)
    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.6, label="Perfect calibration")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed fraction with disease")
    ax.set_title("Calibration on the held-out test set")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> None:
    started = time.time()
    X_train = pd.read_csv(DATA_DIR / "X_train_raw.csv")[FEATURE_ORDER]
    X_test = pd.read_csv(DATA_DIR / "X_test_raw.csv")[FEATURE_ORDER]
    y_train = pd.read_csv(DATA_DIR / "y_train.csv").values.ravel().astype(int)
    y_test = pd.read_csv(DATA_DIR / "y_test.csv").values.ravel().astype(int)

    preprocessor = joblib.load(MODEL_DIR / "preprocessor.joblib")
    X_train_t = np.asarray(preprocessor.transform(X_train))
    X_test_t = np.asarray(preprocessor.transform(X_test))

    leaderboard: list[dict] = []
    fitted: dict[str, object] = {}
    curves: dict[str, dict] = {}
    test_aucs: dict[str, float] = {}
    test_probs: dict[str, np.ndarray] = {}

    for name, search in candidate_searches().items():
        print(f"\n=== {name}: tuning with {CV.get_n_splits()} stratified folds ===")
        t0 = time.time()
        search.fit(X_train_t, y_train)
        best_idx = search.best_index_
        cv_mean = float(search.cv_results_["mean_test_score"][best_idx])
        cv_std = float(search.cv_results_["std_test_score"][best_idx])

        model = search.best_estimator_
        probs = model.predict_proba(X_test_t)[:, 1]
        test = binary_metrics(y_test, probs, 0.5)

        fitted[name] = model
        curves[name] = roc_points(y_test, probs)
        test_aucs[name] = test["roc_auc"]
        test_probs[name] = probs

        row = {
            "model": name,
            "cv_roc_auc_mean": round(cv_mean, 4),
            "cv_roc_auc_std": round(cv_std, 4),
            "test_roc_auc": round(test["roc_auc"], 4),
            "test_pr_auc": round(test["pr_auc"], 4),
            "test_brier": round(test["brier"], 4),
            "test_accuracy@0.5": round(test["accuracy"], 4),
            "test_f1@0.5": round(test["f1"], 4),
            "test_sensitivity@0.5": round(test["sensitivity"], 4),
            "test_specificity@0.5": round(test["specificity"], 4),
            "n_candidates": int(len(search.cv_results_["mean_test_score"])),
            "tuning_seconds": round(time.time() - t0, 1),
            "best_params": json_safe(search.best_params_),
        }
        leaderboard.append(row)
        print(
            f"CV ROC-AUC {cv_mean:.4f} +/- {cv_std:.4f} | test ROC-AUC {test['roc_auc']:.4f} "
            f"| PR-AUC {test['pr_auc']:.4f} | Brier {test['brier']:.4f} ({row['tuning_seconds']}s)"
        )
        print("best params:", row["best_params"])

    # Model selection: cross-validated ROC-AUC only (never the test set).
    # Ties within 0.005 go to the simpler model (order of definition).
    best_cv = max(row["cv_roc_auc_mean"] for row in leaderboard)
    winner = next(row for row in leaderboard if row["cv_roc_auc_mean"] >= best_cv - 0.005)
    best_name = winner["model"]
    best_model = fitted[best_name]
    print(f"\nSelected model: {best_name} (CV ROC-AUC {winner['cv_roc_auc_mean']:.4f})")

    # Clinically oriented thresholds from out-of-fold predictions on the training data.
    oof = cross_val_predict(sklearn.base.clone(best_model), X_train_t, y_train, cv=OOF_CV, method="predict_proba")[:, 1]
    decision = optimize_thresholds(y_train, oof, min_sensitivity=MIN_SENSITIVITY, min_specificity=MIN_SPECIFICITY)
    print(
        f"Thresholds: rule-out {decision.rule_out:.2f} (sens {decision.rule_out_metrics['sensitivity']:.3f}) "
        f"| rule-in {decision.rule_in:.2f} (spec {decision.rule_in_metrics['specificity']:.3f}) "
        f"| Youden {decision.youden:.2f}"
    )
    for note in decision.notes:
        print("note:", note)

    winner_probs = test_probs[best_name]
    test_at_rule_out = binary_metrics(y_test, winner_probs, decision.rule_out)
    test_at_rule_in = binary_metrics(y_test, winner_probs, decision.rule_in)
    oof_metrics = binary_metrics(y_train, oof, 0.5)

    # Global explainability on the held-out test set.
    background = X_train.sample(n=min(100, len(X_train)), random_state=RANDOM_STATE)
    importance = compute_global_importance(best_model, preprocessor, X_test, background)

    # Persist artifacts.
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, MODEL_DIR / "model.joblib")
    pd.DataFrame(
        [{k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in row.items()} for row in leaderboard]
    ).to_csv(MODEL_DIR / "model_results.csv", index=False)
    (MODEL_DIR / "roc_curve.json").write_text(json.dumps(json_safe(curves), indent=2))
    (MODEL_DIR / "global_feature_importance.json").write_text(json.dumps(importance, indent=2))

    dataset_summary = {}
    summary_path = DATA_DIR / "dataset_summary.json"
    if summary_path.exists():
        dataset_summary = json.loads(summary_path.read_text())

    metadata = {
        "model_name": best_name,
        "model_class": type(best_model).__name__,
        "model_version": datetime.now(UTC).strftime("%Y%m%d-%H%M%S"),
        "trained_at": datetime.now(UTC).isoformat(),
        "encoding_version": ENCODING_VERSION,
        "label_definition": "1 = angiographic coronary artery disease (UCI Cleveland num > 0), 0 = no disease",
        "positive_class_meaning": "probability of coronary artery disease",
        "features": FEATURE_ORDER,
        "transformed_feature_names": list(preprocessor.get_feature_names_out()),
        "best_params": winner["best_params"],
        "selection_criterion": "highest mean ROC-AUC over 5-fold x 3-repeat stratified cross-validation (ties within 0.005 -> simpler model)",
        "cross_validation": {
            "scheme": "RepeatedStratifiedKFold",
            "n_splits": 5,
            "n_repeats": 3,
            "random_state": RANDOM_STATE,
            "roc_auc_mean": winner["cv_roc_auc_mean"],
            "roc_auc_std": winner["cv_roc_auc_std"],
        },
        "out_of_fold_metrics": oof_metrics,
        "test_metrics": {
            "at_0.5": binary_metrics(y_test, winner_probs, 0.5),
            "at_rule_out": test_at_rule_out,
            "at_rule_in": test_at_rule_in,
        },
        "thresholds": decision.to_dict(),
        "risk_bands": {
            "Low": f"probability < {decision.rule_out:.2f}",
            "Medium": f"{decision.rule_out:.2f} <= probability < {decision.rule_in:.2f}",
            "High": f"probability >= {decision.rule_in:.2f}",
        },
        "leaderboard": leaderboard,
        "global_feature_importance": importance,
        "dataset": dataset_summary,
        "library_versions": {
            "python": platform.python_version(),
            "scikit-learn": sklearn.__version__,
            "xgboost": xgboost.__version__ if XGBOOST_AVAILABLE else None,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "training_seconds": round(time.time() - started, 1),
    }
    (MODEL_DIR / "model_metadata.json").write_text(json.dumps(json_safe(metadata), indent=2))

    plot_roc_curves(curves, test_aucs, REPORT_DIR / "roc_curves.png")
    plot_threshold_analysis(
        threshold_sweep(y_train, oof), decision.rule_out, decision.rule_in, REPORT_DIR / "threshold_analysis.png"
    )
    plot_calibration(y_test, test_probs, REPORT_DIR / "calibration.png")
    plot_global_importance(importance, REPORT_DIR / "global_feature_importance.png")

    print("\nLeaderboard:")
    print(
        pd.DataFrame(leaderboard)[
            ["model", "cv_roc_auc_mean", "cv_roc_auc_std", "test_roc_auc", "test_pr_auc", "test_brier"]
        ].to_string(index=False)
    )
    print(f"\nSaved model -> {MODEL_DIR / 'model.joblib'}")
    print(f"Saved model card -> {MODEL_DIR / 'model_metadata.json'}")
    print(f"Reports -> {REPORT_DIR}")
    print(f"Total time {time.time() - started:.1f}s")


if __name__ == "__main__":
    main()
