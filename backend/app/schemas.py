from pydantic import BaseModel, EmailStr, Field


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


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class AuthOut(BaseModel):
    ok: bool
    message: str



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


class PredictResponse(BaseModel):
    risk_probability: float = Field(..., ge=0.0, le=1.0)
    risk_level: str
    triage_recommendation: str