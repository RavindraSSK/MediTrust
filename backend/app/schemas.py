from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional


class AssessmentIn(BaseModel):
    full_name: str
    age: int


class AssessmentOut(BaseModel):
    risk_level: str
    risk_score: float
    saved_id: int


class RegisterIn(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: Optional[str] = "Doctor"
    hospital_name: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class AuthOut(BaseModel):
    ok: bool
    message: str


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


class PredictRequest(BaseModel):
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


class FeatureExplanation(BaseModel):
    feature: str
    value: float
    impact: float
    direction: str


class PredictResponse(BaseModel):
    risk_probability: float = Field(..., ge=0.0, le=1.0)
    risk_level: str
    triage_recommendation: str
    explanation_summary: str
    top_features: List[FeatureExplanation]
    all_features: List[FeatureExplanation]
    base_value: float