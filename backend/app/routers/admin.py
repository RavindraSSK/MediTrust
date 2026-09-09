"""Administration: user approval, roles, doctor-nurse assignments, audit view."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..db import get_db
from ..models import User
from ..schemas import AdminRoleStatusUpdateIn, AdminRoleUpdateIn, DoctorNurseAssignmentIn
from ..security import VALID_ROLES, require_admin
from ..serializers import (
    normalize_risk_level,
    patient_display_name,
    serialize_assignment,
    serialize_triage_case,
    serialize_user,
    timestamp_sort_value,
)
from .auth import normalize_role

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])

VALID_ROLE_STATUSES = {"pending", "approved", "rejected"}


def is_universal_admin(user: User) -> bool:
    return (user.email or "").lower().strip() == settings.admin_email


def get_user_or_404(user_id: int, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.get("/users")
def admin_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return [serialize_user(user) for user in db.query(User).order_by(User.id.asc()).all()]


@router.patch("/users/{user_id}/role")
def admin_update_user_role(
    user_id: int, data: AdminRoleUpdateIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    user = get_user_or_404(user_id, db)
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Admins cannot change their own role from this screen.")
    if is_universal_admin(user):
        raise HTTPException(status_code=400, detail="The universal admin account role cannot be changed.")

    role = normalize_role(data.role)
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Unsupported role.")

    user.role = role
    db.commit()
    db.refresh(user)
    logger.info("Admin %s set role of %s to %s", admin.email, user.email, role, extra={"event": "admin_role"})
    return {"ok": True, "message": "User role updated.", "user": serialize_user(user)}


@router.patch("/users/{user_id}/role-status")
def admin_update_user_role_status(
    user_id: int, data: AdminRoleStatusUpdateIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    user = get_user_or_404(user_id, db)
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Admins cannot change their own approval status from this screen.")
    if is_universal_admin(user):
        raise HTTPException(status_code=400, detail="The universal admin account status cannot be changed.")

    role_status = (data.role_status or "").strip().lower()
    if role_status not in VALID_ROLE_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported approval status.")

    user.role_status = role_status
    db.commit()
    db.refresh(user)
    logger.info(
        "Admin %s set status of %s to %s", admin.email, user.email, role_status, extra={"event": "admin_status"}
    )
    return {"ok": True, "message": "User approval status updated.", "user": serialize_user(user)}


@router.delete("/users/{user_id}")
def admin_delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = get_user_or_404(user_id, db)
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Admins cannot delete their own account.")
    if is_universal_admin(user):
        raise HTTPException(status_code=400, detail="The universal admin account cannot be deleted.")

    db.query(models.DoctorNurseAssignment).filter(
        (models.DoctorNurseAssignment.doctor_id == user.id) | (models.DoctorNurseAssignment.nurse_id == user.id)
    ).delete(synchronize_session=False)
    db.delete(user)
    db.commit()
    logger.info("Admin %s deleted user %s", admin.email, user.email, extra={"event": "admin_delete"})
    return {"ok": True, "message": "User account deleted."}


@router.get("/doctor-nurse-assignments")
def admin_doctor_nurse_assignments(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rows = db.query(models.DoctorNurseAssignment).order_by(models.DoctorNurseAssignment.id.asc()).all()
    users = {u.id: u for u in db.query(User).all()}
    result = []
    for row in rows:
        doctor, nurse = users.get(row.doctor_id), users.get(row.nurse_id)
        if doctor and nurse:
            result.append(serialize_assignment(row, doctor, nurse))
    return result


@router.post("/doctor-nurse-assignments")
def admin_create_doctor_nurse_assignment(
    data: DoctorNurseAssignmentIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    doctor = get_user_or_404(data.doctor_id, db)
    nurse = get_user_or_404(data.nurse_id, db)

    if doctor.role != "Doctor" or (doctor.role_status or "approved") != "approved":
        raise HTTPException(status_code=400, detail="Select an approved doctor.")
    if nurse.role != "Nurse" or (nurse.role_status or "approved") != "approved":
        raise HTTPException(status_code=400, detail="Select an approved nurse.")

    existing = (
        db.query(models.DoctorNurseAssignment)
        .filter(models.DoctorNurseAssignment.doctor_id == doctor.id, models.DoctorNurseAssignment.nurse_id == nurse.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="This doctor-nurse assignment already exists.")

    assignment = models.DoctorNurseAssignment(doctor_id=doctor.id, nurse_id=nurse.id)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return {
        "ok": True,
        "message": "Nurse assigned to doctor.",
        "assignment": serialize_assignment(assignment, doctor, nurse),
    }


@router.delete("/doctor-nurse-assignments/{assignment_id}")
def admin_delete_doctor_nurse_assignment(
    assignment_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    assignment = db.query(models.DoctorNurseAssignment).filter(models.DoctorNurseAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    db.delete(assignment)
    db.commit()
    return {"ok": True, "message": "Nurse unassigned from doctor."}


@router.get("/cases")
def admin_cases(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rows = (
        db.query(models.PredictionLog)
        .order_by(models.PredictionLog.created_at.desc(), models.PredictionLog.id.desc())
        .limit(100)
        .all()
    )
    escalations = {item.case_id: item for item in db.query(models.CaseEscalation).all()}
    return [serialize_triage_case(row, escalations.get(row.id)) for row in rows]


@router.get("/audit-log")
def admin_audit_log(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    events = []
    for user in db.query(User).order_by(User.id.desc()).limit(20).all():
        events.append(
            {
                "type": "User",
                "title": f"{user.role} account: {user.full_name}",
                "description": f"Approval status: {(user.role_status or 'approved').title()}",
                "created_at": user.created_at,
            }
        )

    predictions = (
        db.query(models.PredictionLog)
        .order_by(models.PredictionLog.created_at.desc(), models.PredictionLog.id.desc())
        .limit(20)
        .all()
    )
    for row in predictions:
        events.append(
            {
                "type": "Prediction",
                "title": f"Case #{row.id}: {patient_display_name(row)}",
                "description": (
                    f"{normalize_risk_level(row.risk_level)} risk, "
                    f"{round(float(row.risk_probability or 0) * 100)}% probability"
                    + (" (legacy model)" if row.model_version is None else f" (model {row.model_version})")
                ),
                "created_at": row.created_at,
            }
        )

    escalations = (
        db.query(models.CaseEscalation)
        .order_by(models.CaseEscalation.created_at.desc(), models.CaseEscalation.id.desc())
        .limit(20)
        .all()
    )
    for row in escalations:
        events.append(
            {
                "type": "Escalation",
                "title": f"Escalation #{row.id} for case #{row.case_id}",
                "description": row.doctor_decision or row.status or "Escalated to doctor",
                "created_at": row.reviewed_at or row.created_at,
            }
        )

    return sorted(events, key=lambda item: timestamp_sort_value(item["created_at"]), reverse=True)[:40]
