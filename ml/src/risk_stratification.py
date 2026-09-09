"""
Map a predicted probability of coronary artery disease onto the ED triage
bands. Thresholds come from the tuned model card when available so the
training pipeline and the API always agree.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DEFAULT_RULE_OUT = 0.30
DEFAULT_RULE_IN = 0.65
METADATA_PATH = Path(__file__).resolve().parents[1] / "models" / "model_metadata.json"

TRIAGE_MESSAGES = {
    "Low": "Standard evaluation recommended",
    "Medium": "Priority review recommended",
    "High": "Immediate physician evaluation recommended",
}


@lru_cache(maxsize=1)
def load_thresholds(path: Path = METADATA_PATH) -> tuple[float, float]:
    try:
        data = json.loads(Path(path).read_text())
        thresholds = data["thresholds"]
        rule_out = float(thresholds["rule_out"])
        rule_in = float(thresholds["rule_in"])
        if 0 < rule_out < rule_in < 1:
            return rule_out, rule_in
    except (OSError, KeyError, ValueError, TypeError, json.JSONDecodeError):
        pass
    return DEFAULT_RULE_OUT, DEFAULT_RULE_IN


def risk_level_from_probability(p: float, thresholds: tuple[float, float] | None = None):
    """Return ``(level, triage_message)`` for a probability of disease."""
    rule_out, rule_in = thresholds or load_thresholds()
    if p >= rule_in:
        level = "High"
    elif p >= rule_out:
        level = "Medium"
    else:
        level = "Low"
    return level, TRIAGE_MESSAGES[level]
