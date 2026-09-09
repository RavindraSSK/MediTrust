import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluate import band_for_probability, binary_metrics, optimize_thresholds, threshold_sweep  # noqa: E402


def _synthetic(n=400, seed=0):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, size=n)
    # Informative but imperfect scores.
    p = np.clip(0.55 * y + 0.25 + rng.normal(0, 0.18, size=n), 0.001, 0.999)
    return y, p


def test_binary_metrics_confusion_counts_add_up():
    y, p = _synthetic()
    m = binary_metrics(y, p, 0.5)
    assert m["tp"] + m["tn"] + m["fp"] + m["fn"] == len(y)
    assert 0.8 < m["roc_auc"] <= 1.0
    assert 0 <= m["sensitivity"] <= 1 and 0 <= m["specificity"] <= 1


def test_threshold_sweep_is_monotone_in_sensitivity():
    y, p = _synthetic()
    sweep = threshold_sweep(y, p)
    sens = sweep["sensitivity"].to_numpy()
    assert np.all(np.diff(sens) <= 1e-12)


def test_optimize_thresholds_respects_clinical_floors():
    y, p = _synthetic()
    decision = optimize_thresholds(y, p, min_sensitivity=0.95, min_specificity=0.85)
    assert 0.05 <= decision.rule_out < decision.rule_in <= 0.95
    assert decision.rule_out_metrics["sensitivity"] >= 0.95
    assert decision.rule_in_metrics["specificity"] >= 0.85
    assert sum(decision.band_distribution.values()) == len(y)


def test_optimize_thresholds_falls_back_when_unachievable():
    # Half of the diseased patients score ~0 and every healthy patient scores ~1,
    # so neither the sensitivity floor nor the specificity floor is reachable.
    y = np.array([1] * 20 + [0] * 20)
    p = np.array([0.001] * 10 + [0.9] * 10 + [0.999] * 20)
    decision = optimize_thresholds(y, p)
    assert decision.rule_out < decision.rule_in
    assert decision.rule_out == 0.05 and decision.rule_in == 0.95
    assert len(decision.notes) == 2  # documents both fallbacks


def test_band_for_probability_boundaries():
    assert band_for_probability(0.29, 0.30, 0.65) == "Low"
    assert band_for_probability(0.30, 0.30, 0.65) == "Medium"
    assert band_for_probability(0.65, 0.30, 0.65) == "High"
