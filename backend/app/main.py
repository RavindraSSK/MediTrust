from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from passlib.context import CryptContext

from .db import Base, engine, get_db
from . import models
from .models import User
from .schemas import (
    AssessmentIn,
    AssessmentOut,
    RegisterIn,
    LoginIn,
    AuthOut,
)


app = FastAPI(title="MediTrust API", version="0.1")

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# CORS Configuration (for Live Server frontend)

ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:5501",
    "http://localhost:5501",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,   # IMPORTANT (since we are not using cookies)
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup: Create Tables Automatically

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

# --------------------------------------------------
# Basic Routes
# --------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "MediTrust API running",
        "docs": "/docs",
        "health": "/health",
        "db": "/db-health",
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/db-health")
def db_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"database": "PostgreSQL connected "}

# --------------------------------------------------
# AUTH ROUTES
# --------------------------------------------------
@app.post("/auth/register", response_model=AuthOut)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if len(data.password.encode("utf-8")) > 72:
        return {"ok": False, "message": "Password too long (max 72 characters)."}

    email = data.email.lower().strip()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return {"ok": False, "message": "Email already registered."}

    user = User(
        full_name=data.full_name.strip(),
        email=email,
        password_hash=pwd_context.hash(data.password),
    )
    db.add(user)
    db.commit()
    return {"ok": True, "message": "Account created successfully."}

@app.post("/auth/login", response_model=AuthOut)
def login(data: LoginIn, db: Session = Depends(get_db)):

    email = data.email.lower().strip()

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"ok": False, "message": "Invalid email or password."}

    if not pwd_context.verify(data.password, user.password_hash):
        return {"ok": False, "message": "Invalid email or password."}

    return {"ok": True, "message": "Login successful."}

# --------------------------------------------------
# RISK ASSESSMENT ROUTE
# --------------------------------------------------
@app.post("/assess", response_model=AssessmentOut)
def assess(data: AssessmentIn, db: Session = Depends(get_db)):

    # Sprint 1 dummy rule
    if data.age >= 50:
        risk_level = "High"
        risk_score = 0.8
    else:
        risk_level = "Low"
        risk_score = 0.3

    record = models.Assessment(
        full_name=data.full_name.strip(),
        age=data.age,
        risk_level=risk_level,
        risk_score=risk_score,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return AssessmentOut(
        risk_level=record.risk_level,
        risk_score=record.risk_score,
        saved_id=record.id,
    )