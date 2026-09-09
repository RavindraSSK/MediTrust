"""Row -> dict helpers shared by the routers."""

from __future__ import annotations

import json
from datetime import UTC

from .clinical_encoding import FEATURE_LABELS
from .models import User
from .risk import normalize_risk_level, priority_for_risk, risk_level_from_probability

FEATURE_MEANINGS = {
    "age": "Age helps estimate baseline cardiovascular risk.",
    "sex": "Sex is used as one demographic risk signal in the heart disease model.",
    "cp": "Chest pain type describes the pattern of chest discomfort reported during assessment.",
    "trestbps": "Resting blood pressure reflects pressure on the cardiovascular system at rest.",
    "chol": "Total cholesterol can indicate lipid-related cardiovascular burden.",
    "fbs": "Fasting blood sugar helps identify glucose-related risk patterns.",
    "restecg": "Resting ECG findings show electrical patterns seen before exertion.",
    "thalach": "Maximum heart rate achieved reflects exercise response and cardiac reserve.",
    "exang": "Exercise-induced angina indicates chest discomfort triggered by exertion.",
    "oldpeak": "Exercise-induced ST depression can reflect stress-related ECG changes.",
    "slope": "ST-segment slope describes how the ECG changes during exercise.",
    "ca": "Major vessel involvement reflects the number of visible affected vessels.",
    "thal": "Thallium stress test result reflects blood-flow patterns during cardiac stress testing.",
}


def compose_full_name(first_name: str, last_name: str) -> str:
    return f"{(first_name or '').strip()} {(last_name or '').strip()}".strip()


def patient_display_name(row) -> str:
    name = compose_full_name(row.first_name or "", row.last_name or "")
    return name or row.full_name or f"Patient #{row.id}"


def timestamp_sort_value(value) -> float:
    if not value:
        return 0.0
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.timestamp()


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "full_name": user.full_name,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "role": user.role,
        "role_status": getattr(user, "role_status", "approved") or "approved",
        "hospital_name": user.hospital_name,
        "created_at": getattr(user, "created_at", None),
        "last_login_at": getattr(user, "last_login_at", None),
    }


def serialize_prediction_log(row) -> dict:
    return {
        "id": row.id,
        "full_name": row.full_name,
        "first_name": row.first_name,
        "last_name": row.last_name,
        "patient_name": patient_display_name(row),
        "risk_probability": row.risk_probability,
        "risk_level": row.risk_level,
        "age": row.age,
        "sex": row.sex,
        "cp": row.cp,
        "trestbps": row.trestbps,
        "chol": row.chol,
        "fbs": row.fbs,
        "restecg": row.restecg,
        "thalach": row.thalach,
        "exang": row.exang,
        "oldpeak": row.oldpeak,
        "slope": row.slope,
        "ca": row.ca,
        "thal": row.thal,
        "model_version": getattr(row, "model_version", None),
        "legacy_model": getattr(row, "model_version", None) is None,
        "created_by_user_id": getattr(row, "created_by_user_id", None),
        "created_at": row.created_at,
        "triage_message": risk_level_from_probability(float(row.risk_probability or 0))[1],
    }


def serialize_triage_case(row, escalation=None) -> dict:
    escalated = escalation is not None
    review_status = getattr(escalation, "status", None) if escalation else None
    return {
        **serialize_prediction_log(row),
        "patient_id": row.id,
        "status": review_status or ("Escalated" if escalated else "Pending"),
        "priority": priority_for_risk(row.risk_level),
        "escalated": escalated,
        "escalation_id": escalation.id if escalation else None,
        "escalated_at": escalation.created_at if escalation else None,
        "nurse_id": escalation.nurse_id if escalation else None,
        "doctor_id": getattr(escalation, "doctor_id", None) if escalation else None,
        "doctor_decision": getattr(escalation, "doctor_decision", None) if escalation else None,
        "doctor_note": getattr(escalation, "doctor_note", None) if escalation else None,
        "reviewed_at": getattr(escalation, "reviewed_at", None) if escalation else None,
    }


def serialize_assignment(assignment, doctor: User, nurse: User) -> dict:
    return {
        "id": assignment.id,
        "doctor_id": assignment.doctor_id,
        "nurse_id": assignment.nurse_id,
        "doctor_name": doctor.full_name,
        "doctor_email": doctor.email,
        "nurse_name": nurse.full_name,
        "nurse_email": nurse.email,
        "created_at": assignment.created_at,
    }


def feature_to_clinical_text(item: dict) -> dict:
    feature = str(item.get("feature") or "").strip()
    direction = str(item.get("direction") or "").strip().lower()
    label = FEATURE_LABELS.get(feature, feature.replace("_", " ").title() if feature else "Clinical feature")
    meaning = FEATURE_MEANINGS.get(feature, "This feature contributed to the model's risk estimate.")
    if direction == "increases risk":
        effect = "This finding pushed the estimated risk higher."
    elif direction == "decreases risk":
        effect = "This finding helped lower the estimated risk."
    else:
        effect = "This finding influenced the estimated risk."
    return {
        "feature": feature,
        "label": label,
        "value": item.get("value"),
        "impact": item.get("impact"),
        "direction": item.get("direction") or "influences risk",
        "explanation": f"{meaning} {effect}",
    }


def build_fallback_explanation(top_features: list[dict], risk_level: str) -> str:
    increasing = [feature_to_clinical_text(i)["label"] for i in top_features if i.get("direction") == "increases risk"]
    reducing = [feature_to_clinical_text(i)["label"] for i in top_features if i.get("direction") == "decreases risk"]
    drivers = ", ".join(increasing[:3]) if increasing else "the available clinical features"
    offsets = ", ".join(reducing[:2]) if reducing else "no strong risk-reducing factor"
    return (
        f"{drivers} contributed most to this {risk_level.lower()} risk prediction. "
        f"{offsets} offset the prediction to some extent. The AI model suggests this risk pattern, "
        "but the final decision must be made by the clinician."
    )


def load_clinical_context(row) -> dict | None:
    raw = getattr(row, "clinical_context", None)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except (TypeError, ValueError):
        return None


__all__ = [
    "compose_full_name",
    "patient_display_name",
    "timestamp_sort_value",
    "serialize_user",
    "serialize_prediction_log",
    "serialize_triage_case",
    "serialize_assignment",
    "feature_to_clinical_text",
    "build_fallback_explanation",
    "load_clinical_context",
    "normalize_risk_level",
]
