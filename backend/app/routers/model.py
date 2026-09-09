"""Model card endpoints (no patient data; safe to expose publicly)."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from ..clinical_encoding import (
    CATEGORY_CODES,
    CATEGORY_LABELS,
    ENCODING_VERSION,
    FEATURE_LABELS,
    FEATURE_ORDER,
    FEATURE_UNITS,
    NUMERIC_RANGES,
)
from ..config import settings
from ..ml_service import ModelNotLoadedError, model_service
from ..risk import TRIAGE_MESSAGES, get_thresholds

router = APIRouter(prefix="/model", tags=["Model"])


@router.get("/info")
def model_info():
    try:
        loaded = model_service.ensure_loaded()
    except ModelNotLoadedError:
        loaded = None
    rule_out, rule_in = get_thresholds()
    if loaded is None:
        return {
            "status": "unavailable",
            "error": "Model metadata is currently unavailable.",
            "active_thresholds": {"rule_out": rule_out, "rule_in": rule_in},
            "triage_messages": TRIAGE_MESSAGES,
        }
    meta = loaded.metadata
    info = {
        "status": "ready",
        "model_name": loaded.name,
        "model_class": meta.get("model_class") or type(loaded.model).__name__,
        "model_version": loaded.version,
        "trained_at": meta.get("trained_at"),
        "encoding_version": meta.get("encoding_version", ENCODING_VERSION),
        "label_definition": meta.get("label_definition"),
        "positive_class_meaning": meta.get("positive_class_meaning"),
        "features": meta.get("features", FEATURE_ORDER),
        "selection_criterion": meta.get("selection_criterion"),
        "cross_validation": meta.get("cross_validation"),
        "test_metrics": meta.get("test_metrics"),
        "thresholds": meta.get("thresholds"),
        "risk_bands": meta.get("risk_bands"),
        "leaderboard": meta.get("leaderboard"),
        "global_feature_importance": loaded.global_importance,
        "library_versions": meta.get("library_versions"),
        "dataset": meta.get("dataset"),
        "explainer": type(loaded.explainer).__name__ if loaded.explainer else None,
        "artifact_source": loaded.source,
        "loaded_at": loaded.loaded_at,
    }
    info["active_thresholds"] = {"rule_out": rule_out, "rule_in": rule_in}
    info["triage_messages"] = TRIAGE_MESSAGES
    return info


@router.get("/encoding")
def model_encoding():
    return {
        "encoding_version": ENCODING_VERSION,
        "features": FEATURE_ORDER,
        "labels": FEATURE_LABELS,
        "units": FEATURE_UNITS,
        "numeric_ranges": {k: list(v) for k, v in NUMERIC_RANGES.items()},
        "category_codes": CATEGORY_CODES,
        "category_labels": {k: {str(code): label for code, label in v.items()} for k, v in CATEGORY_LABELS.items()},
    }


@router.get("/roc-curve")
def model_roc_curve():
    path = settings.model_dir / "roc_curve.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="ROC curve data is not available.")
    return json.loads(path.read_text())
