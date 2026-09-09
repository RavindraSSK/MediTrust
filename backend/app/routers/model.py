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
from ..ml_service import model_service
from ..risk import TRIAGE_MESSAGES, get_thresholds

router = APIRouter(prefix="/model", tags=["Model"])


@router.get("/info")
def model_info():
    info = model_service.info()
    rule_out, rule_in = get_thresholds()
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
