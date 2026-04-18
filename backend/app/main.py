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
    PredictRequest,
    PredictResponse,
)
from .ml_service import predict_probability, explain_prediction
from .risk import risk_level_from_probability
from .auth import router as auth_extra_router


app = FastAPI(title="MediTrust API", version="0.1")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_extra_router)


def compose_full_name(first_name: str, last_name: str) -> str:
    return f"{first_name.strip()} {last_name.strip()}".strip()


def migrate_name_columns():
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as conn:
        for statement in [
            "ALTER TABLE users ADD COLUMN first_name VARCHAR",
            "ALTER TABLE users ADD COLUMN last_name VARCHAR",
            "ALTER TABLE assessments ADD COLUMN first_name VARCHAR",
            "ALTER TABLE assessments ADD COLUMN last_name VARCHAR",
            "ALTER TABLE prediction_logs ADD COLUMN first_name VARCHAR",
            "ALTER TABLE prediction_logs ADD COLUMN last_name VARCHAR",
            "ALTER TABLE prediction_logs ADD COLUMN full_name VARCHAR",
        ]:
            try:
                conn.execute(text(statement))
            except Exception:
                pass

        for table_name in ["users", "assessments"]:
            rows = conn.execute(text(f"PRAGMA table_info({table_name})")).mappings().all()
            column_names = {row["name"] for row in rows}
            if "full_name" not in column_names or "first_name" not in column_names or "last_name" not in column_names:
                continue

            conn.execute(
                text(
                    f"""
                    UPDATE {table_name}
                    SET
                        first_name = CASE
                            WHEN instr(trim(full_name), ' ') > 0 THEN substr(trim(full_name), 1, instr(trim(full_name), ' ') - 1)
                            ELSE trim(full_name)
                        END,
                        last_name = CASE
                            WHEN instr(trim(full_name), ' ') > 0 THEN substr(trim(full_name), instr(trim(full_name), ' ') + 1)
                            ELSE ''
                        END
                    WHERE first_name IS NULL OR trim(first_name) = ''
                    """
                )
            )
            conn.execute(
                text(f"UPDATE {table_name} SET last_name = '' WHERE last_name IS NULL")
            )


def serialize_prediction_log(row):
    return {
        "id": row.id,
        "full_name": row.full_name,
        "first_name": row.first_name,
        "last_name": row.last_name,
        "risk_probability": row.risk_probability,
        "risk_level": row.risk_level,
        "age": row.age,
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
        "cp": row.cp,
        "sex": row.sex,
        "created_at": row.created_at,
        "triage_message": risk_level_from_probability(float(row.risk_probability or 0))[1],
    }


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    migrate_name_columns()


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
    return {"database": "PostgreSQL connected"}


@app.post("/auth/register", response_model=AuthOut)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return {"ok": False, "message": "Email already registered."}

    user = User(
        full_name=compose_full_name(data.first_name, data.last_name),
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        email=email,
        password_hash=pwd_context.hash(data.password),
        role=data.role or "Doctor",
        hospital_name=data.hospital_name,
    )
    db.add(user)
    db.commit()

    return {"ok": True, "message": "Account created successfully."}


@app.post("/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    email = data.email.lower().strip()

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"ok": False, "message": "Invalid email or password."}

    if not pwd_context.verify(data.password, user.password_hash):
        return {"ok": False, "message": "Invalid email or password."}

    return {
        "ok": True,
        "message": "Login successful.",
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": compose_full_name(user.first_name, user.last_name),
        "role": user.role,
    }


@app.post("/assess", response_model=AssessmentOut)
def assess(data: AssessmentIn, db: Session = Depends(get_db)):
    if data.age >= 50:
        risk_level = "High"
        risk_score = 0.8
    else:
        risk_level = "Low"
        risk_score = 0.3

    record = models.Assessment(
        full_name=compose_full_name(data.first_name, data.last_name),
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
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


@app.post("/predict", response_model=PredictResponse, tags=["Prediction"])
def predict(req: PredictRequest, db: Session = Depends(get_db)):
    raw_payload = req.model_dump()
    first_name = raw_payload.pop("first_name").strip()
    last_name = raw_payload.pop("last_name").strip()
    full_name = compose_full_name(first_name, last_name)
    payload = raw_payload

    prob = float(predict_probability(payload))
    level, msg = risk_level_from_probability(prob)

    top_features, all_features, base_value, explanation_summary = explain_prediction(payload, level)

    log = models.PredictionLog(
        full_name=full_name,
        first_name=first_name,
        last_name=last_name,
        **payload,
        risk_probability=prob,
        risk_level=level
    )

    db.add(log)
    db.commit()

    return PredictResponse(
        risk_probability=prob,
        risk_level=level,
        triage_recommendation=msg,
        explanation_summary=explanation_summary,
        top_features=top_features,
        all_features=all_features,
        base_value=base_value
    )


@app.get("/predictions/recent", tags=["Prediction"])
def recent_predictions(db: Session = Depends(get_db)):
    rows = (
        db.query(models.PredictionLog)
        .order_by(models.PredictionLog.id.desc())
        .limit(10)
        .all()
    )

    return [
        serialize_prediction_log(r)
        for r in rows
    ]


@app.get("/predictions/urgent", tags=["Prediction"])
def urgent_predictions(db: Session = Depends(get_db)):
    rows = (
        db.query(models.PredictionLog)
        .filter(models.PredictionLog.risk_level == "High")
        .order_by(models.PredictionLog.id.desc())
        .limit(10)
        .all()
    )

    return [
        serialize_prediction_log(r)
        for r in rows
    ]


@app.get("/patients/recent", tags=["Patients"])
def recent_patients(limit: int = 5, db: Session = Depends(get_db)):
    rows = (
        db.query(models.PredictionLog)
        .filter(models.PredictionLog.full_name.isnot(None))
        .filter(models.PredictionLog.full_name != "")
        .order_by(models.PredictionLog.created_at.desc(), models.PredictionLog.id.desc())
        .all()
    )

    seen = set()
    patients = []
    for row in rows:
        key = (row.first_name or "", row.last_name or "", row.full_name or "")
        if key in seen:
            continue
        seen.add(key)
        patients.append(serialize_prediction_log(row))
        if len(patients) >= max(1, min(limit, 20)):
            break

    return patients


@app.get("/patients/search", tags=["Patients"])
def search_patients(q: str = "", db: Session = Depends(get_db)):
    query = q.strip()
    if not query:
        return []

    like_query = f"%{query}%"
    rows = (
        db.query(models.PredictionLog)
        .filter(models.PredictionLog.full_name.isnot(None))
        .filter(models.PredictionLog.full_name.ilike(like_query))
        .order_by(models.PredictionLog.created_at.desc(), models.PredictionLog.id.desc())
        .all()
    )

    seen = set()
    patients = []
    for row in rows:
        key = (row.first_name or "", row.last_name or "", row.full_name or "")
        if key in seen:
            continue
        seen.add(key)
        patients.append(serialize_prediction_log(row))
        if len(patients) >= 20:
            break

    return patients


@app.get("/patients/records", tags=["Patients"])
def patient_records(first_name: str, last_name: str, db: Session = Depends(get_db)):
    rows = (
        db.query(models.PredictionLog)
        .filter(models.PredictionLog.first_name == first_name.strip())
        .filter(models.PredictionLog.last_name == last_name.strip())
        .order_by(models.PredictionLog.created_at.desc(), models.PredictionLog.id.desc())
        .all()
    )

    return [serialize_prediction_log(row) for row in rows]


@app.get("/dashboard/summary", tags=["Dashboard"])
def dashboard_summary(db: Session = Depends(get_db)):
    total_predictions = db.query(models.PredictionLog).count()
    urgent_cases = (
        db.query(models.PredictionLog)
        .filter(models.PredictionLog.risk_level == "High")
        .count()
    )
    medium_cases = (
        db.query(models.PredictionLog)
        .filter(models.PredictionLog.risk_level == "Medium")
        .count()
    )
    low_cases = (
        db.query(models.PredictionLog)
        .filter(models.PredictionLog.risk_level == "Low")
        .count()
    )
    total_users = db.query(User).count()

    return {
        "total_predictions": total_predictions,
        "urgent_cases": urgent_cases,
        "medium_cases": medium_cases,
        "low_cases": low_cases,
        "total_users": total_users,
    }
