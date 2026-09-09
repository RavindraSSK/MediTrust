"""
Evaluation utilities: classification metrics, threshold sweeps and the
clinically oriented two-threshold (rule-out / rule-in) selection used to map
model probabilities onto the Low / Medium / High triage bands.

Design rationale
----------------
In an emergency-department screening context a false negative (a diseased
patient labelled *Low*) is far more costly than a false positive, so the
lower ("rule-out") threshold is chosen to keep sensitivity at or above a
floor (default 95%). The upper ("rule-in") threshold is chosen to keep
specificity at or above a floor (default 85%) so that *High* flags remain
actionable. Everything in between is *Medium* and routed for priority review.
Thresholds are selected on out-of-fold predictions from cross-validation,
never on the held-out test set.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    log_loss,
    roc_auc_score,
    roc_curve,
)

DEFAULT_RULE_OUT = 0.30
DEFAULT_RULE_IN = 0.65


def binary_metrics(y_true, y_prob, threshold: float = 0.5) -> dict:
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob, dtype=float)
    y_pred = (y_prob >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    sensitivity = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    ppv = tp / (tp + fp) if (tp + fp) else 0.0
    npv = tn / (tn + fn) if (tn + fn) else 0.0
    f1 = 2 * ppv * sensitivity / (ppv + sensitivity) if (ppv + sensitivity) else 0.0
    beta_sq = 4.0
    f2 = (1 + beta_sq) * ppv * sensitivity / (beta_sq * ppv + sensitivity) if (beta_sq * ppv + sensitivity) else 0.0

    metrics = {
        "threshold": float(threshold),
        "accuracy": float((tp + tn) / max(len(y_true), 1)),
        "sensitivity": float(sensitivity),
        "specificity": float(specificity),
        "ppv": float(ppv),
        "npv": float(npv),
        "f1": float(f1),
        "f2": float(f2),
        "youden_j": float(sensitivity + specificity - 1),
        "tp": int(tp),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
    }

    if len(np.unique(y_true)) == 2:
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
        metrics["pr_auc"] = float(average_precision_score(y_true, y_prob))
        metrics["brier"] = float(brier_score_loss(y_true, y_prob))
        clipped = np.clip(y_prob, 1e-7, 1 - 1e-7)
        metrics["log_loss"] = float(log_loss(y_true, clipped))
    return metrics


def threshold_sweep(y_true, y_prob, thresholds=None) -> pd.DataFrame:
    if thresholds is None:
        thresholds = np.round(np.arange(0.02, 0.99, 0.01), 2)
    rows = [binary_metrics(y_true, y_prob, float(t)) for t in thresholds]
    return pd.DataFrame(rows)


def select_rule_out_threshold(sweep: pd.DataFrame, min_sensitivity: float = 0.95) -> float | None:
    """Largest threshold whose sensitivity still meets the floor."""
    eligible = sweep[sweep["sensitivity"] >= min_sensitivity]
    if eligible.empty:
        return None
    return float(eligible["threshold"].max())


def select_rule_in_threshold(sweep: pd.DataFrame, min_specificity: float = 0.85) -> float | None:
    """Smallest threshold whose specificity meets the floor."""
    eligible = sweep[sweep["specificity"] >= min_specificity]
    if eligible.empty:
        return None
    return float(eligible["threshold"].min())


def select_youden_threshold(sweep: pd.DataFrame) -> float:
    idx = sweep["youden_j"].idxmax()
    return float(sweep.loc[idx, "threshold"])


@dataclass
class ThresholdDecision:
    rule_out: float
    rule_in: float
    youden: float
    min_sensitivity: float
    min_specificity: float
    rule_out_metrics: dict = field(default_factory=dict)
    rule_in_metrics: dict = field(default_factory=dict)
    band_distribution: dict = field(default_factory=dict)
    band_prevalence: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "rule_out": self.rule_out,
            "rule_in": self.rule_in,
            "youden": self.youden,
            "min_sensitivity": self.min_sensitivity,
            "min_specificity": self.min_specificity,
            "rule_out_metrics": self.rule_out_metrics,
            "rule_in_metrics": self.rule_in_metrics,
            "band_distribution": self.band_distribution,
            "band_prevalence": self.band_prevalence,
            "notes": self.notes,
        }


def band_for_probability(p: float, rule_out: float, rule_in: float) -> str:
    if p >= rule_in:
        return "High"
    if p >= rule_out:
        return "Medium"
    return "Low"


def optimize_thresholds(
    y_true,
    y_prob,
    min_sensitivity: float = 0.95,
    min_specificity: float = 0.85,
    floor: float = 0.05,
    ceiling: float = 0.95,
) -> ThresholdDecision:
    """
    Choose rule-out / rule-in thresholds from (out-of-fold) predictions.

    Guarantees ``floor <= rule_out < rule_in <= ceiling``. When the constraints
    cannot both be met on the supplied data the Youden-optimal threshold is used
    as an anchor and the situation is recorded in ``notes``.
    """
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob, dtype=float)
    sweep = threshold_sweep(y_true, y_prob)
    notes: list[str] = []

    youden = select_youden_threshold(sweep)
    rule_out = select_rule_out_threshold(sweep, min_sensitivity)
    rule_in = select_rule_in_threshold(sweep, min_specificity)

    if rule_out is None:
        rule_out = floor
        notes.append(f"No threshold reached sensitivity >= {min_sensitivity:.2f}; using floor {floor:.2f}.")
    if rule_in is None:
        rule_in = ceiling
        notes.append(f"No threshold reached specificity >= {min_specificity:.2f}; using ceiling {ceiling:.2f}.")

    rule_out = float(min(max(rule_out, floor), ceiling))
    rule_in = float(min(max(rule_in, floor), ceiling))

    if rule_out >= rule_in:
        notes.append(f"Rule-out ({rule_out:.2f}) was not below rule-in ({rule_in:.2f}); re-centred around Youden J.")
        rule_out = float(max(floor, min(rule_out, youden - 0.05)))
        rule_in = float(min(ceiling, max(rule_in, youden + 0.05)))
        if rule_out >= rule_in:
            rule_out, rule_in = DEFAULT_RULE_OUT, DEFAULT_RULE_IN
            notes.append("Fell back to default bands 0.30 / 0.65.")

    bands = np.array([band_for_probability(p, rule_out, rule_in) for p in y_prob])
    distribution = {band: int((bands == band).sum()) for band in ("Low", "Medium", "High")}
    prevalence = {}
    for band in ("Low", "Medium", "High"):
        mask = bands == band
        prevalence[band] = float(y_true[mask].mean()) if mask.any() else None

    return ThresholdDecision(
        rule_out=round(rule_out, 2),
        rule_in=round(rule_in, 2),
        youden=round(youden, 2),
        min_sensitivity=min_sensitivity,
        min_specificity=min_specificity,
        rule_out_metrics=binary_metrics(y_true, y_prob, rule_out),
        rule_in_metrics=binary_metrics(y_true, y_prob, rule_in),
        band_distribution=distribution,
        band_prevalence=prevalence,
        notes=notes,
    )


def roc_points(y_true, y_prob, max_points: int = 200) -> dict:
    fpr, tpr, thr = roc_curve(y_true, y_prob)
    if len(fpr) > max_points:
        idx = np.linspace(0, len(fpr) - 1, max_points).astype(int)
        fpr, tpr, thr = fpr[idx], tpr[idx], thr[idx]
    return {
        "fpr": [float(x) for x in fpr],
        "tpr": [float(x) for x in tpr],
        "thresholds": [float(x) if np.isfinite(x) else 1.0 for x in thr],
    }
