from fastapi import FastAPI, Depends, Header, HTTPException
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
    AdminRoleUpdateIn,
    AdminRoleStatusUpdateIn,
    DoctorNurseAssignmentIn,
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


VALID_ROLES = {"Doctor", "Nurse", "Admin", "Patient"}
VALID_ROLE_STATUSES = {"pending", "approved", "rejected"}


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

    is_first_user = db.query(User).count() == 0
    user = User(
        full_name=compose_full_name(data.first_name, data.last_name),
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        email=email,
        password_hash=pwd_context.hash(data.password),
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
