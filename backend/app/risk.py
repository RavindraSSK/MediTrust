"""
Map a probability of coronary artery disease onto the triage bands.

The rule-out / rule-in thresholds come from ``model_metadata.json`` produced by
the training pipeline (clinically oriented threshold optimisation). They can be
overridden with RISK_RULE_OUT / RISK_RULE_IN for experimentation.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache

from .config import env_float, settings

logger = logging.getLogger(__name__)

DEFAULT_RULE_OUT = 0.30
DEFAULT_RULE_IN = 0.65

TRIAGE_MESSAGES = {
    "Low": "Standard evaluation recommended",
    "Medium": "Priority review recommended",
    "High": "Immediate physician evaluation recommended",
}


@lru_cache(maxsize=1)
def get_thresholds() -> tuple[float, float]:
    rule_out = env_float("RISK_RULE_OUT", 0.0)
    rule_in = env_float("RISK_RULE_IN", 0.0)
    if 0 < rule_out < rule_in < 1:
        logger.info("Using risk thresholds from environment: %.2f / %.2f", rule_out, rule_in)
        return rule_out, rule_in

    metadata_path = settings.model_dir / "model_metadata.json"
    try:
        data = json.loads(metadata_path.read_text())
        thresholds = data["thresholds"]
        rule_out = float(thresholds["rule_out"])
        rule_in = float(thresholds["rule_in"])
        if 0 < rule_out < rule_in < 1:
            return rule_out, rule_in
        logger.warning("Model card thresholds are invalid (%s); using defaults", thresholds)
    except FileNotFoundError:
        logger.warning("No model card at %s; using default risk thresholds", metadata_path)
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        logger.warning("Could not read thresholds from model card: %s", exc)
    return DEFAULT_RULE_OUT, DEFAULT_RULE_IN


def reset_threshold_cache() -> None:
    get_thresholds.cache_clear()


def risk_level_from_probability(p: float, thresholds: tuple[float, float] | None = None) -> tuple[str, str]:
    rule_out, rule_in = thresholds or get_thresholds()
    if p >= rule_in:
        level = "High"
    elif p >= rule_out:
        level = "Medium"
    else:
        level = "Low"
    return level, TRIAGE_MESSAGES[level]


def normalize_risk_level(value: str | None) -> str:
    cleaned = (value or "").strip().lower()
    return {"high": "High", "medium": "Medium", "low": "Low"}.get(cleaned, "Unknown")


def priority_for_risk(risk_level: str | None) -> str:
    level = normalize_risk_level(risk_level)
    if level == "High":
        return "Urgent"
    if level == "Medium":
        return "Monitor"
    return "Routine"
