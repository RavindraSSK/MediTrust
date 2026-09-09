from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel, EmailStr, Field


# ----------------------------------------------------------------------- auth
class RegisterIn(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=80)
    last_name: str = Field(..., min_length=1, max_length=80)
    email: EmailStr
    password: str
    role: str | None = "Doctor"
    hospital_name: str | None = Field(default=None, max_length=160)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class AuthOut(BaseModel):
    ok: bool
    message: str


class UserOut(BaseModel):
    id: int
    full_name: str
    first_name: str
    last_name: str
    email: str
    role: str
    role_status: str
    hospital_name: str | None = None
    created_at: Any | None = None
    last_login_at: Any | None = None


class LoginOut(BaseModel):
    ok: bool
    message: str
    access_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
    user: UserOut | None = None
    # Flat fields kept for backwards compatibility with older clients.
    id: int | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    role: str | None = None
    role_status: str | None = None


class GenericMessageOut(BaseModel):
    ok: bool
    message: str


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class VerifyResetCodeIn(BaseModel):
    email: EmailStr
    code: str


class ResetPasswordIn(BaseModel):
    email: EmailStr
    new_password: str


class ChangePasswordIn(BaseModel):
    email: EmailStr | None = None
    current_password: str
    new_password: str


# ---------------------------------------------------------------------- admin
class AdminRoleUpdateIn(BaseModel):
    role: str


class AdminRoleStatusUpdateIn(BaseModel):
    role_status: str


class DoctorNurseAssignmentIn(BaseModel):
    doctor_id: int
    nurse_id: int


class TriageDecisionIn(BaseModel):
    decision: str
    note: str | None = None


# ----------------------------------------------------------------- prediction
class PredictRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=80)
    last_name: str = Field(..., min_length=1, max_length=80)
    age: float
    sex: int
    cp: int
    trestbps: float
    chol: float
    fbs: int
    restecg: int
    thalach: float
    exang: int
    oldpeak: float
    slope: int
    ca: int
    thal: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "first_name": "Demo",
                "last_name": "Patient",
                "age": 58,
                "sex": 1,
                "cp": 4,
                "trestbps": 156,
                "chol": 286,
                "fbs": 1,
                "restecg": 1,
                "thalach": 118,
                "exang": 1,
                "oldpeak": 2.8,
                "slope": 2,
                "ca": 2,
                "thal": 7,
            }
        }
    }


class FeatureExplanation(BaseModel):
    feature: str
    label: str | None = None
    value: float
    impact: float
    direction: str


class PredictResponse(BaseModel):
    case_id: int | None = None
    risk_probability: float = Field(..., ge=0.0, le=1.0)
    risk_level: str
    triage_recommendation: str
    thresholds: dict | None = None
    explanation_summary: str
    gemini_summary: str | None = None
    top_features: List[FeatureExplanation]
    all_features: List[FeatureExplanation]
    base_value: float
    model_version: str | None = None
    model_name: str | None = None
    clinical_context: dict | None = None
    generated_at: str | None = None
