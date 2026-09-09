"""
Global SHAP feature importance for the trained MediTrust model.

Aggregates SHAP values of the one-hot expanded columns back onto the raw
clinical features so the model card can show "how much does chest pain type
matter overall" rather than "how much does cat__cp_4 matter".
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import shap

SRC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))

from data_dictionary import FEATURE_LABELS, FEATURE_ORDER  # noqa: E402


def raw_feature_for_column(column_name: str) -> str:
    cleaned = column_name.split("__", 1)[1] if "__" in column_name else column_name
    for raw in FEATURE_ORDER:
        if cleaned == raw or cleaned.startswith(raw + "_"):
            return raw
    return cleaned


def _to_dense(matrix):
    return matrix.toarray() if hasattr(matrix, "toarray") else np.asarray(matrix)


def positive_class_probability(model):
    """Callable returning P(disease) so every explainer works in probability space."""

    def predict(X):
        return np.asarray(model.predict_proba(X))[:, 1]

    return predict


def is_tree_model(model) -> bool:
    return hasattr(model, "estimators_") or hasattr(model, "get_booster")


def build_explainer(model, background: np.ndarray, feature_names: list[str]):
    """
    Explain P(disease) in probability space so contributions are additive on
    the same scale the clinician sees. Tree models get the exact TreeExplainer;
    everything else uses the model-agnostic permutation explainer.
    """
    if is_tree_model(model):
        try:
            return shap.TreeExplainer(
                model, data=background, model_output="probability", feature_perturbation="interventional"
            )
        except Exception:
            pass
    return shap.Explainer(positive_class_probability(model), background, feature_names=feature_names)


def positive_class_values(shap_output) -> np.ndarray:
    values = np.asarray(getattr(shap_output, "values", shap_output))
    if values.ndim == 3:
        if values.shape[-1] == 2:
            return values[:, :, 1]
        if values.shape[1] == 2:
            return values[:, 1, :]
        return values.reshape(values.shape[0], -1)
    return values


def compute_global_importance(model, preprocessor, X_raw: pd.DataFrame, background_raw: pd.DataFrame) -> dict:
    feature_names = list(preprocessor.get_feature_names_out())
    X_t = _to_dense(preprocessor.transform(X_raw[FEATURE_ORDER]))
    background = _to_dense(preprocessor.transform(background_raw[FEATURE_ORDER]))

    explainer = build_explainer(model, background, feature_names)
    shap_output = explainer(X_t)
    values = positive_class_values(shap_output)

    frame = pd.DataFrame(values, columns=feature_names)
    grouped_abs: dict[str, float] = {}
    grouped_signed: dict[str, float] = {}
    for column in feature_names:
        raw = raw_feature_for_column(column)
        grouped_abs[raw] = grouped_abs.get(raw, 0.0) + float(frame[column].abs().mean())
        grouped_signed[raw] = grouped_signed.get(raw, 0.0) + float(frame[column].mean())

    total = sum(grouped_abs.values()) or 1.0
    ranking = sorted(grouped_abs.items(), key=lambda item: item[1], reverse=True)
    features = [
        {
            "feature": name,
            "label": FEATURE_LABELS.get(name, name),
            "mean_abs_shap": round(score, 6),
            "share": round(score / total, 4),
            "mean_shap": round(grouped_signed[name], 6),
            "rank": rank,
        }
        for rank, (name, score) in enumerate(ranking, start=1)
    ]
    return {
        "method": type(explainer).__name__,
        "samples": int(len(X_raw)),
        "output": "probability of disease (class 1)",
        "features": features,
    }


def plot_global_importance(importance: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    features = list(reversed(importance["features"]))
    labels = [item["label"] for item in features]
    scores = [item["mean_abs_shap"] for item in features]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.barh(labels, scores, color="#2563eb")
    ax.set_xlabel("Mean |SHAP value| (probability of disease)")
    ax.set_title("Global feature importance (SHAP, held-out test set)")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)
