from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from passlib.context import CryptContext
from dotenv import load_dotenv
import os

load_dotenv()
from .db import Base, engine, get_db
from . import models
from .models import User
from .schemas import (
    AssessmentIn,
    AssessmentOut,
    RegisterIn,
    LoginIn,
    AuthOut,
    AdminRoleUpdateIn,
    AdminRoleStatusUpdateIn,
    DoctorNurseAssignmentIn,
    PredictRequest,
    PredictResponse,
)
from .ml_service import predict_probability, explain_prediction, generate_gemini_summary
from .password_utils import validate_password_for_bcrypt
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

azure_allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
ALLOWED_ORIGINS = list(dict.fromkeys(ALLOWED_ORIGINS + azure_allowed_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_extra_router)


VALID_ROLES = {"Doctor", "Nurse", "Admin", "Patient"}
VALID_ROLE_STATUSES = {"pending", "approved", "rejected"}


def compose_full_name(first_name: str, last_name: str) -> str:
    return f"{first_name.strip()} {last_name.strip()}".strip()


def migrate_name_columns():
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            for statement in [
                "ALTER TABLE users ADD COLUMN first_name VARCHAR",
                "ALTER TABLE users ADD COLUMN last_name VARCHAR",
                "ALTER TABLE assessments ADD COLUMN first_name VARCHAR",
                "ALTER TABLE assessments ADD COLUMN last_name VARCHAR",
                "ALTER TABLE prediction_logs ADD COLUMN first_name VARCHAR",
                "ALTER TABLE prediction_logs ADD COLUMN last_name VARCHAR",
                "ALTER TABLE prediction_logs ADD COLUMN full_name VARCHAR",
                "ALTER TABLE users ADD COLUMN role_status VARCHAR DEFAULT 'approved' NOT NULL",
            ]:
                try:
                    conn.execute(text(statement))
                except Exception:
                    pass

            conn.execute(
                text("UPDATE users SET role_status = 'approved' WHERE role_status IS NULL OR trim(role_status) = ''")
            )

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

            return

        if engine.dialect.name == "postgresql":
            for statement in [
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS role_status VARCHAR DEFAULT 'approved'",
                "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS first_name VARCHAR",
                "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS last_name VARCHAR",
                "ALTER TABLE prediction_logs ADD COLUMN IF NOT EXISTS full_name VARCHAR",
                "ALTER TABLE prediction_logs ADD COLUMN IF NOT EXISTS first_name VARCHAR",
                "ALTER TABLE prediction_logs ADD COLUMN IF NOT EXISTS last_name VARCHAR",
            ]:
                conn.execute(text(statement))

            conn.execute(
                text("UPDATE users SET role_status = 'approved' WHERE role_status IS NULL OR btrim(role_status) = ''")
            )

            for table_name in ["users", "assessments", "prediction_logs"]:
                conn.execute(
                    text(
                        f"""
                        UPDATE {table_name}
                        SET
                            first_name = CASE
                                WHEN strpos(btrim(coalesce(full_name, '')), ' ') > 0 THEN split_part(btrim(full_name), ' ', 1)
                                ELSE btrim(coalesce(full_name, ''))
                            END,
                            last_name = CASE
                                WHEN strpos(btrim(coalesce(full_name, '')), ' ') > 0
                                    THEN btrim(substr(btrim(full_name), strpos(btrim(full_name), ' ') + 1))
                                ELSE ''
                            END
                        WHERE
                            full_name IS NOT NULL
                            AND (
                                first_name IS NULL OR btrim(first_name) = ''
                                OR last_name IS NULL
                            )
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

FEATURE_LABELS = {
    "age": "Age",
    "sex": "Sex",
    "cp": "Chest pain type",
    "trestbps": "Resting blood pressure",
    "chol": "Total cholesterol",
    "fbs": "Fasting blood sugar",
    "restecg": "Resting ECG result",
    "thalach": "Maximum heart rate",
    "exang": "Exercise-induced angina",
    "oldpeak": "ST depression during exercise",
    "slope": "ST-segment slope",
    "ca": "Major vessel involvement",
    "thal": "Thallium stress test result",
}


def normalize_risk_level(value: str | None) -> str:
    cleaned = (value or "").strip().lower()
    if cleaned == "high":
        return "High"
    if cleaned == "medium":
        return "Medium"
    if cleaned == "low":
        return "Low"
    return "Unknown"


def priority_for_risk(risk_level: str | None) -> str:
    level = normalize_risk_level(risk_level)
    if level == "High":
        return "Urgent"
    if level == "Medium":
        return "Monitor"
    return "Routine"


def patient_display_name(row) -> str:
    name = compose_full_name(row.first_name or "", row.last_name or "")
    return name or row.full_name or f"Patient #{row.id}"


def get_case_or_404(case_id: int, db: Session):
    case = db.query(models.PredictionLog).filter(models.PredictionLog.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case


def serialize_triage_case(row, escalation=None):
    escalated = escalation is not None
    return {
        **serialize_prediction_log(row),
        "patient_id": row.id,
        "patient_name": patient_display_name(row),
        "status": "Escalated" if escalated else "Pending",
        "priority": priority_for_risk(row.risk_level),
        "escalated": escalated,
        "escalation_id": escalation.id if escalation else None,
        "escalated_at": escalation.created_at if escalation else None,
        "nurse_id": escalation.nurse_id if escalation else None,
    }


def feature_to_clinical_text(item):
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
        "direction": item.get("direction") or "influences risk",
        "explanation": f"{meaning} {effect}",
    }


def build_fallback_explanation(top_features: list[dict], risk_level: str) -> str:
    increasing = [feature_to_clinical_text(item)["label"] for item in top_features if item.get("direction") == "increases risk"]
    reducing = [feature_to_clinical_text(item)["label"] for item in top_features if item.get("direction") == "decreases risk"]
    drivers = ", ".join(increasing[:3]) if increasing else "the available clinical features"
    offsets = ", ".join(reducing[:2]) if reducing else "no strong risk-reducing factor"
    return (
        f"{drivers} contributed most to this {risk_level.lower()} risk prediction. "
        f"{offsets} offset the prediction to some extent. The AI model suggests this risk pattern, "
        "but the final decision must be made by the clinician."
    )


def normalize_role(role: str) -> str:
    cleaned = (role or "").strip().lower()
    role_map = {
        "doctor": "Doctor",
        "nurse": "Nurse",
        "admin": "Admin",
        "patient": "Patient",
    }
    return role_map.get(cleaned, role.strip() if role else "")


def serialize_user(user: User):
    return {
        "id": user.id,
        "full_name": user.full_name,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "role": user.role,
        "role_status": getattr(user, "role_status", "approved") or "approved",
        "hospital_name": user.hospital_name,
    }


def get_admin_user(
    x_admin_email: str = Header(default=""),
    db: Session = Depends(get_db),
):
    email = (x_admin_email or "").lower().strip()
    if not email:
        raise HTTPException(status_code=401, detail="Admin email header is required.")

    admin = db.query(User).filter(User.email == email).first()
    if (
        not admin
        or admin.role != "Admin"
        or (getattr(admin, "role_status", "approved") or "approved") != "approved"
    ):
        raise HTTPException(status_code=403, detail="Admin access required.")

    return admin


def get_user_or_404(user_id: int, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


def serialize_assignment(assignment, doctor: User, nurse: User):
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

    requested_role = normalize_role(data.role or "Doctor")
    if requested_role not in VALID_ROLES:
        return {"ok": False, "message": "Unsupported role selected."}

    password, password_error = validate_password_for_bcrypt(data.password)
    if password_error:
        return {"ok": False, "message": password_error}

    is_first_user = db.query(User).count() == 0
    user = User(
        full_name=compose_full_name(data.first_name, data.last_name),
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        email=email,
        password_hash=pwd_context.hash(password),
        role=requested_role,
        role_status="approved" if is_first_user else "pending",
        hospital_name=data.hospital_name,
    )
    db.add(user)
    db.commit()

    if user.role_status == "approved":
        return {"ok": True, "message": "Account created successfully."}

    return {"ok": True, "message": "Account created. An admin must approve this role before login."}


@app.post("/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    email = data.email.lower().strip()

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"ok": False, "message": "Invalid email or password."}

    if not pwd_context.verify(data.password, user.password_hash):
        return {"ok": False, "message": "Invalid email or password."}

    role_status = getattr(user, "role_status", "approved") or "approved"
    if role_status != "approved":
        return {
            "ok": False,
            "message": "Your role request is pending admin approval." if role_status == "pending" else "Your role request was rejected.",
        }

    return {
        "ok": True,
        "message": "Login successful.",
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": compose_full_name(user.first_name, user.last_name),
        "role": user.role,
        "role_status": role_status,
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
    gemini_summary = generate_gemini_summary(
        top_features=top_features,
        risk_level=level,
        risk_probability=prob,
        triage_recommendation=msg,
        explanation_summary=explanation_summary,
    )

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

    print("Returning gemini_summary:", gemini_summary)

    return PredictResponse(
        risk_probability=prob,
        risk_level=level,
        triage_recommendation=msg,
        explanation_summary=explanation_summary,
        gemini_summary=gemini_summary,
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


@app.get("/cases/triage-queue", tags=["Cases"])
def triage_queue(db: Session = Depends(get_db)):
    rows = (
        db.query(models.PredictionLog)
        .order_by(models.PredictionLog.created_at.desc(), models.PredictionLog.id.desc())
        .limit(100)
        .all()
    )
    escalations = {
        item.case_id: item
        for item in db.query(models.CaseEscalation).all()
    }
    return [serialize_triage_case(row, escalations.get(row.id)) for row in rows]


@app.post("/cases/{case_id}/escalate", tags=["Cases"])
def escalate_case(
    case_id: int,
    x_nurse_id: str = Header(default=""),
    db: Session = Depends(get_db),
):
    case = get_case_or_404(case_id, db)
    risk_level = normalize_risk_level(case.risk_level)

    if risk_level not in {"High", "Medium"}:
        raise HTTPException(
            status_code=400,
            detail="Only high-risk or selected medium-risk cases can be escalated.",
        )

    existing = (
        db.query(models.CaseEscalation)
        .filter(models.CaseEscalation.case_id == case.id)
        .first()
    )
    if existing:
        return {
            "ok": False,
            "message": "This case is already escalated.",
            "case": serialize_triage_case(case, existing),
        }

    nurse_id = None
    try:
        nurse_id = int(x_nurse_id) if str(x_nurse_id).strip() else None
    except ValueError:
        nurse_id = None

    escalation = models.CaseEscalation(case_id=case.id, nurse_id=nurse_id)
    db.add(escalation)
    db.commit()
    db.refresh(escalation)

    return {
        "ok": True,
        "message": "Case escalated to doctor for review.",
        "case": serialize_triage_case(case, escalation),
    }


@app.get("/doctor/escalations", tags=["Doctor"])
def doctor_escalations(db: Session = Depends(get_db)):
    rows = (
        db.query(models.CaseEscalation, models.PredictionLog)
        .join(models.PredictionLog, models.CaseEscalation.case_id == models.PredictionLog.id)
        .order_by(models.CaseEscalation.created_at.desc(), models.CaseEscalation.id.desc())
        .all()
    )
    return [serialize_triage_case(case, escalation) for escalation, case in rows]


@app.get("/cases/{case_id}/explainability", tags=["Cases"])
def case_explainability(case_id: int, db: Session = Depends(get_db)):
    case = get_case_or_404(case_id, db)
    payload = {
        "age": case.age,
        "sex": case.sex,
        "cp": case.cp,
        "trestbps": case.trestbps,
        "chol": case.chol,
        "fbs": case.fbs,
        "restecg": case.restecg,
        "thalach": case.thalach,
        "exang": case.exang,
        "oldpeak": case.oldpeak,
        "slope": case.slope,
        "ca": case.ca,
        "thal": case.thal,
    }
    missing = [key for key, value in payload.items() if value is None]
    if missing:
        raise HTTPException(status_code=400, detail="This case is missing model inputs needed for explainability.")

    risk_level = normalize_risk_level(case.risk_level)
    triage_recommendation = risk_level_from_probability(float(case.risk_probability or 0))[1]
    top_features, all_features, base_value, explanation_summary = explain_prediction(payload, risk_level)
    gemini_summary = generate_gemini_summary(
        top_features=top_features,
        risk_level=risk_level,
        risk_probability=case.risk_probability,
        triage_recommendation=triage_recommendation,
        explanation_summary=explanation_summary,
    )
    increasing = [
        feature_to_clinical_text(item)
        for item in top_features
        if item.get("direction") == "increases risk"
    ]
    reducing = [
        feature_to_clinical_text(item)
        for item in top_features
        if item.get("direction") == "decreases risk"
    ]
    clinical_summary = gemini_summary or build_fallback_explanation(top_features, risk_level)

    return {
        "case": serialize_prediction_log(case),
        "patient": {
            "id": case.id,
            "name": patient_display_name(case),
            "age": case.age,
        },
        "risk_probability": case.risk_probability,
        "risk_level": risk_level,
        "triage_recommendation": triage_recommendation,
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
        "top_features": [feature_to_clinical_text(item) for item in top_features],
        "all_features": all_features,
        "base_value": base_value,
    }


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


@app.get("/admin/users", tags=["Admin"])
def admin_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    users = db.query(User).order_by(User.id.asc()).all()
    return [serialize_user(user) for user in users]


@app.patch("/admin/users/{user_id}/role", tags=["Admin"])
def admin_update_user_role(
    user_id: int,
    data: AdminRoleUpdateIn,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    user = get_user_or_404(user_id, db)
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Admins cannot change their own role from this screen.")

    role = normalize_role(data.role)
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Unsupported role.")

    user.role = role
    db.commit()
    db.refresh(user)
    return {"ok": True, "message": "User role updated.", "user": serialize_user(user)}


@app.patch("/admin/users/{user_id}/role-status", tags=["Admin"])
def admin_update_user_role_status(
    user_id: int,
    data: AdminRoleStatusUpdateIn,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    user = get_user_or_404(user_id, db)
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Admins cannot change their own approval status from this screen.")

    role_status = (data.role_status or "").strip().lower()
    if role_status not in VALID_ROLE_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported approval status.")

    user.role_status = role_status
    db.commit()
    db.refresh(user)
    return {"ok": True, "message": "User approval status updated.", "user": serialize_user(user)}


@app.delete("/admin/users/{user_id}", tags=["Admin"])
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    user = get_user_or_404(user_id, db)
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Admins cannot delete their own account.")

    db.query(models.DoctorNurseAssignment).filter(
        (models.DoctorNurseAssignment.doctor_id == user.id)
        | (models.DoctorNurseAssignment.nurse_id == user.id)
    ).delete(synchronize_session=False)
    db.delete(user)
    db.commit()
    return {"ok": True, "message": "User account deleted."}


@app.get("/admin/doctor-nurse-assignments", tags=["Admin"])
def admin_doctor_nurse_assignments(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    rows = db.query(models.DoctorNurseAssignment).order_by(models.DoctorNurseAssignment.id.asc()).all()
    result = []
    for row in rows:
        doctor = db.query(User).filter(User.id == row.doctor_id).first()
        nurse = db.query(User).filter(User.id == row.nurse_id).first()
        if doctor and nurse:
            result.append(serialize_assignment(row, doctor, nurse))
    return result


@app.post("/admin/doctor-nurse-assignments", tags=["Admin"])
def admin_create_doctor_nurse_assignment(
    data: DoctorNurseAssignmentIn,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    doctor = get_user_or_404(data.doctor_id, db)
    nurse = get_user_or_404(data.nurse_id, db)

    if doctor.role != "Doctor" or (getattr(doctor, "role_status", "approved") or "approved") != "approved":
        raise HTTPException(status_code=400, detail="Select an approved doctor.")
    if nurse.role != "Nurse" or (getattr(nurse, "role_status", "approved") or "approved") != "approved":
        raise HTTPException(status_code=400, detail="Select an approved nurse.")

    existing = db.query(models.DoctorNurseAssignment).filter(
        models.DoctorNurseAssignment.doctor_id == doctor.id,
        models.DoctorNurseAssignment.nurse_id == nurse.id,
    ).first()
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


@app.delete("/admin/doctor-nurse-assignments/{assignment_id}", tags=["Admin"])
def admin_delete_doctor_nurse_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    assignment = db.query(models.DoctorNurseAssignment).filter(
        models.DoctorNurseAssignment.id == assignment_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    db.delete(assignment)
    db.commit()
    return {"ok": True, "message": "Nurse unassigned from doctor."}


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
