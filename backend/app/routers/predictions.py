"""Risk prediction, explainability, triage workflow and patient records."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..db import get_db
from ..llm import gemini_client
from ..ml_service import model_service
from ..models import User
from ..observability import PREDICTION_LATENCY, PREDICTIONS_TOTAL
from ..rag import get_clinical_context_service
from ..risk import get_thresholds, normalize_risk_level, risk_level_from_probability
from ..schemas import PredictRequest, PredictResponse, TriageDecisionIn
from ..security import ROLE_ADMIN, ROLE_DOCTOR, ROLE_NURSE, require_clinical_user, require_roles
from ..serializers import (
    build_fallback_explanation,
    compose_full_name,
    feature_to_clinical_text,
    load_clinical_context,
    patient_display_name,
    serialize_prediction_log,
    serialize_triage_case,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Prediction"])

VALID_TRIAGE_DECISIONS = {"Immediate physician review", "Priority monitoring", "Routine follow-up"}
CLINICAL_FEATURES = [
    "age",
    "sex",
    "cp",
    "trestbps",
    "chol",
    "fbs",
    "restecg",
    "thalach",
    "exang",
    "oldpeak",
    "slope",
    "ca",
    "thal",
]


def _legacy_gemini_summary(top_features, risk_level, risk_probability, triage, explanation_summary) -> str | None:
    """Short 2-sentence summary kept for the existing UI; only runs when Gemini is configured."""
    if not gemini_client.available or not top_features:
        return None
    labels = ", ".join(
        f"{item.get('label') or item['feature']} ({item.get('direction') or 'affects risk'})"
        for item in top_features[:3]
    )
    prompt = (
        "Generate a 2 sentence clinical summary for this cardiovascular risk assessment. "
        "Use simple professional language. Do not mention SHAP or AI. Do not give a diagnosis. "
        "Do not add medication advice. Do not change the numbers.\n"
        f"Risk level: {risk_level}.\nRisk probability: {int(round(risk_probability * 100))}%.\n"
        f"Triage recommendation: {triage}.\nClinical explanation: {explanation_summary}.\n"
        f"Key contributing factors: {labels}."
    )
    return gemini_client.generate(prompt, temperature=0.2, max_output_tokens=120)


def _build_clinical_context(payload, prob, level, msg, top_features) -> dict | None:
    if not settings.rag_enabled:
        return None
    try:
        return get_clinical_context_service().build(payload, prob, level, msg, top_features)
    except Exception as exc:  # noqa: BLE001 - RAG must never break predictions
        logger.warning("Clinical context unavailable: %s", exc)
        return None


def get_case_or_404(case_id: int, db: Session) -> models.PredictionLog:
    case = db.query(models.PredictionLog).filter(models.PredictionLog.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case


@router.post("/predict", response_model=PredictResponse)
def predict(
    req: PredictRequest,
    user: User = Depends(require_clinical_user),
    db: Session = Depends(get_db),
):
    started = time.perf_counter()
    raw = req.model_dump()
    first_name = raw.pop("first_name").strip()
    last_name = raw.pop("last_name").strip()
    payload = model_service.validate(raw)

    prob = model_service.predict_probability(payload)
    level, msg = risk_level_from_probability(prob)
    top_features, all_features, base_value, explanation_summary = model_service.explain(payload, level)

    clinical_context = _build_clinical_context(payload, prob, level, msg, top_features)
    gemini_summary = _legacy_gemini_summary(top_features, level, prob, msg, explanation_summary)

    log = models.PredictionLog(
        full_name=compose_full_name(first_name, last_name),
        first_name=first_name,
        last_name=last_name,
        **payload,
        risk_probability=prob,
        risk_level=level,
        model_version=model_service.model_version,
        created_by_user_id=user.id,
        explanation_summary=explanation_summary,
        clinical_context=json.dumps(clinical_context) if clinical_context else None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    PREDICTIONS_TOTAL.labels(level).inc()
    PREDICTION_LATENCY.observe(time.perf_counter() - started)
    rule_out, rule_in = get_thresholds()
    logger.info(
        "Prediction case=%s level=%s p=%.3f by=%s rag=%s",
        log.id,
        level,
        prob,
        user.email,
        clinical_context["mode"] if clinical_context else "off",
        extra={"event": "predict", "user": user.email},
    )

    return PredictResponse(
        case_id=log.id,
        risk_probability=prob,
        risk_level=level,
        triage_recommendation=msg,
        thresholds={"rule_out": rule_out, "rule_in": rule_in},
        explanation_summary=explanation_summary,
        gemini_summary=gemini_summary,
        top_features=top_features,
        all_features=all_features,
        base_value=base_value,
        model_version=model_service.model_version,
        model_name=model_service.info().get("model_name"),
        clinical_context=clinical_context,
        generated_at=datetime.now(UTC).isoformat(),
    )


@router.get("/predictions/recent")
def recent_predictions(limit: int = 10, user: User = Depends(require_clinical_user), db: Session = Depends(get_db)):
    limit = max(1, min(limit, 100))
    rows = db.query(models.PredictionLog).order_by(models.PredictionLog.id.desc()).limit(limit).all()
    return [serialize_prediction_log(r) for r in rows]


@router.get("/predictions/urgent")
def urgent_predictions(limit: int = 10, user: User = Depends(require_clinical_user), db: Session = Depends(get_db)):
    limit = max(1, min(limit, 100))
    rows = (
        db.query(models.PredictionLog)
        .filter(models.PredictionLog.risk_level == "High")
        .order_by(models.PredictionLog.id.desc())
        .limit(limit)
        .all()
    )
    return [serialize_prediction_log(r) for r in rows]


@router.get("/dashboard/summary", tags=["Dashboard"])
def dashboard_summary(user: User = Depends(require_clinical_user), db: Session = Depends(get_db)):
    def count(level: str | None = None) -> int:
        query = db.query(models.PredictionLog)
        if level:
            query = query.filter(models.PredictionLog.risk_level == level)
        return query.count()

    escalations = db.query(models.CaseEscalation)
    return {
        "total_predictions": count(),
        "urgent_cases": count("High"),
        "medium_cases": count("Medium"),
        "low_cases": count("Low"),
        "total_users": db.query(User).count(),
        "pending_users": db.query(User).filter(User.role_status == "pending").count(),
        "open_escalations": escalations.filter(models.CaseEscalation.status == "Escalated").count(),
        "reviewed_escalations": escalations.filter(models.CaseEscalation.status == "Reviewed").count(),
        "model_version": model_service.model_version,
    }


# ------------------------------------------------------------------- triage
@router.get("/cases/triage-queue", tags=["Cases"])
def triage_queue(user: User = Depends(require_clinical_user), db: Session = Depends(get_db)):
    rows = (
        db.query(models.PredictionLog)
        .order_by(models.PredictionLog.created_at.desc(), models.PredictionLog.id.desc())
        .limit(100)
        .all()
    )
    escalations = {item.case_id: item for item in db.query(models.CaseEscalation).all()}
    return [serialize_triage_case(row, escalations.get(row.id)) for row in rows]


@router.post("/cases/{case_id}/escalate", tags=["Cases"])
def escalate_case(
    case_id: int,
    user: User = Depends(require_roles(ROLE_NURSE, ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    case = get_case_or_404(case_id, db)
    if normalize_risk_level(case.risk_level) not in {"High", "Medium"}:
        raise HTTPException(status_code=400, detail="Only high-risk or selected medium-risk cases can be escalated.")

    existing = db.query(models.CaseEscalation).filter(models.CaseEscalation.case_id == case.id).first()
    if existing:
        return {
            "ok": False,
            "message": "This case is already escalated.",
            "case": serialize_triage_case(case, existing),
        }

    escalation = models.CaseEscalation(case_id=case.id, nurse_id=user.id)
    db.add(escalation)
    db.commit()
    db.refresh(escalation)
    logger.info("Case %s escalated by %s", case.id, user.email, extra={"event": "escalate", "user": user.email})
    return {
        "ok": True,
        "message": "Case escalated to doctor for review.",
        "case": serialize_triage_case(case, escalation),
    }


@router.get("/doctor/escalations", tags=["Doctor"])
def doctor_escalations(user: User = Depends(require_roles(ROLE_DOCTOR, ROLE_ADMIN)), db: Session = Depends(get_db)):
    rows = (
        db.query(models.CaseEscalation, models.PredictionLog)
        .join(models.PredictionLog, models.CaseEscalation.case_id == models.PredictionLog.id)
        .order_by(models.CaseEscalation.created_at.desc(), models.CaseEscalation.id.desc())
        .all()
    )
    return [serialize_triage_case(case, escalation) for escalation, case in rows]


@router.post("/doctor/escalations/{escalation_id}/decision", tags=["Doctor"])
def doctor_triage_decision(
    escalation_id: int,
    data: TriageDecisionIn,
    user: User = Depends(require_roles(ROLE_DOCTOR, ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    decision = (data.decision or "").strip()
    if decision not in VALID_TRIAGE_DECISIONS:
        raise HTTPException(status_code=400, detail="Unsupported triage decision.")

    row = (
        db.query(models.CaseEscalation, models.PredictionLog)
        .join(models.PredictionLog, models.CaseEscalation.case_id == models.PredictionLog.id)
        .filter(models.CaseEscalation.id == escalation_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Escalation not found.")

    escalation, case = row
    escalation.status = "Reviewed"
    escalation.doctor_id = user.id
    escalation.doctor_decision = decision
    escalation.doctor_note = (data.note or "").strip()[:500] or None
    escalation.reviewed_at = datetime.now(UTC)
    db.commit()
    db.refresh(escalation)
    logger.info(
        "Escalation %s reviewed by %s: %s",
        escalation.id,
        user.email,
        decision,
        extra={"event": "triage_decision", "user": user.email},
    )
    return {"ok": True, "message": "Doctor triage decision saved.", "case": serialize_triage_case(case, escalation)}


@router.get("/cases/{case_id}/explainability", tags=["Cases"])
def case_explainability(case_id: int, user: User = Depends(require_clinical_user), db: Session = Depends(get_db)):
    case = get_case_or_404(case_id, db)
    payload = {feature: getattr(case, feature) for feature in CLINICAL_FEATURES}
    if any(value is None for value in payload.values()):
        raise HTTPException(status_code=400, detail="This case is missing model inputs needed for explainability.")

    try:
        payload = model_service.validate(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"This case was recorded with an encoding the current model does not accept: {exc}",
        ) from exc

    risk_level = normalize_risk_level(case.risk_level)
    triage_recommendation = risk_level_from_probability(float(case.risk_probability or 0))[1]
    top_features, all_features, base_value, explanation_summary = model_service.explain(payload, risk_level)

    clinical_context = load_clinical_context(case)
    if clinical_context is None:
        clinical_context = _build_clinical_context(
            payload, float(case.risk_probability or 0), risk_level, triage_recommendation, top_features
        )

    gemini_summary = _legacy_gemini_summary(
        top_features, risk_level, float(case.risk_probability or 0), triage_recommendation, explanation_summary
    )
    increasing = [feature_to_clinical_text(i) for i in top_features if i.get("direction") == "increases risk"]
    reducing = [feature_to_clinical_text(i) for i in top_features if i.get("direction") == "decreases risk"]
    clinical_summary = gemini_summary or build_fallback_explanation(top_features, risk_level)

    return {
        "case": serialize_prediction_log(case),
        "patient": {"id": case.id, "name": patient_display_name(case), "age": case.age},
        "risk_probability": case.risk_probability,
        "risk_level": risk_level,
        "triage_recommendation": triage_recommendation,
        "legacy_model": case.model_version is None,
        "model_version": case.model_version,
        "current_model_version": model_service.model_version,
        "risk_increasing_factors": increasing,
        "risk_reducing_factors": reducing,
        "clinical_interpretation": clinical_summary,
        "suggested_next_action": (
            "Arrange immediate physician review and correlate with symptoms, ECG, vitals, and troponin pathway."
            if risk_level == "High"
            else "Continue priority monitoring and escalate if symptoms, ECG, or vitals worsen."
            if risk_level == "Medium"
            else "Continue routine clinical review and patient education based on clinician judgment."
        ),
        "confidence_note": "AI model suggests this risk level, but final decision must be made by clinician.",
        "gemini_summary": gemini_summary,
        "fallback_summary": None if gemini_summary else clinical_summary,
        "explanation_summary": explanation_summary,
        "top_features": [feature_to_clinical_text(i) for i in top_features],
        "all_features": all_features,
        "base_value": base_value,
        "clinical_context": clinical_context,
    }


# ----------------------------------------------------------------- patients
def _unique_patients(rows, limit: int) -> list[dict]:
    seen: set[tuple] = set()
    patients: list[dict] = []
    for row in rows:
        key = (row.first_name or "", row.last_name or "", row.full_name or "")
        if key in seen:
            continue
        seen.add(key)
        patients.append(serialize_prediction_log(row))
        if len(patients) >= limit:
            break
    return patients


@router.get("/patients/recent", tags=["Patients"])
def recent_patients(limit: int = 5, user: User = Depends(require_clinical_user), db: Session = Depends(get_db)):
    rows = (
        db.query(models.PredictionLog)
        .filter(models.PredictionLog.full_name.isnot(None))
        .filter(models.PredictionLog.full_name != "")
        .order_by(models.PredictionLog.created_at.desc(), models.PredictionLog.id.desc())
        .all()
    )
    return _unique_patients(rows, max(1, min(limit, 20)))


@router.get("/patients/search", tags=["Patients"])
def search_patients(q: str = "", user: User = Depends(require_clinical_user), db: Session = Depends(get_db)):
    query = q.strip()
    if not query:
        return []
    rows = (
        db.query(models.PredictionLog)
        .filter(models.PredictionLog.full_name.isnot(None))
        .filter(models.PredictionLog.full_name.ilike(f"%{query}%"))
        .order_by(models.PredictionLog.created_at.desc(), models.PredictionLog.id.desc())
        .all()
    )
    return _unique_patients(rows, 20)


@router.get("/patients/records", tags=["Patients"])
def patient_records(
    first_name: str,
    last_name: str,
    user: User = Depends(require_clinical_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.PredictionLog)
        .filter(models.PredictionLog.first_name == first_name.strip())
        .filter(models.PredictionLog.last_name == last_name.strip())
        .order_by(models.PredictionLog.created_at.desc(), models.PredictionLog.id.desc())
        .all()
    )
    return [serialize_prediction_log(row) for row in rows]
