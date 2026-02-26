from pydantic import BaseModel, EmailStr


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