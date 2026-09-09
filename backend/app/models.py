from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from .db import Base


class Assessment(Base):
    """Legacy Sprint 1 table kept for historical rows; no longer written to."""

    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    risk_level = Column(String, nullable=False)
    risk_score = Column(Float, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="Doctor")
    role_status = Column(String, nullable=False, default="pending")
    hospital_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)


class DoctorNurseAssignment(Base):
    __tablename__ = "doctor_nurse_assignments"
    __table_args__ = (UniqueConstraint("doctor_id", "nurse_id", name="uq_doctor_nurse_assignment"),)

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    nurse_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)

    age = Column(Float)
    sex = Column(Integer)
    cp = Column(Integer)
    trestbps = Column(Float)
    chol = Column(Float)
    fbs = Column(Integer)
    restecg = Column(Integer)
    thalach = Column(Float)
    exang = Column(Integer)
    oldpeak = Column(Float)
    slope = Column(Integer)
    ca = Column(Integer)
    thal = Column(Integer)

    risk_probability = Column(Float)
    risk_level = Column(String)

    # Provenance added with the JWT/RAG release. Rows created by the previous
    # (label-inverted) model have model_version NULL and should be treated as legacy.
    model_version = Column(String, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    explanation_summary = Column(Text, nullable=True)
    clinical_context = Column(Text, nullable=True)  # JSON payload of the RAG context shown to the clinician

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CaseEscalation(Base):
    __tablename__ = "case_escalations"
    __table_args__ = (UniqueConstraint("case_id", name="uq_case_escalation_case_id"),)

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("prediction_logs.id"), nullable=False, index=True)
    nurse_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, nullable=False, default="Escalated")
    doctor_decision = Column(String, nullable=True)
    doctor_note = Column(String, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
