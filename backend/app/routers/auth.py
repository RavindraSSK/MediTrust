"""Registration, login (JWT), profile and password flows."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..email_service import EMAIL_LOGGED, EmailDeliveryError, send_reset_code_email
from ..models import User
from ..otp_service import otp_store
from ..password_utils import hash_password, validate_password_for_bcrypt, verify_password
from ..rate_limit import LoginRateLimiter
from ..schemas import (
    AuthOut,
    ChangePasswordIn,
    ForgotPasswordIn,
    GenericMessageOut,
    LoginIn,
    LoginOut,
    RegisterIn,
    ResetPasswordIn,
    UserOut,
    VerifyResetCodeIn,
)
from ..security import VALID_ROLES, create_access_token, get_current_user
from ..serializers import compose_full_name, serialize_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])

login_rate_limiter = LoginRateLimiter(
    max_attempts=settings.login_max_attempts, window_seconds=settings.login_window_seconds
)


def normalize_role(role: str | None) -> str:
    cleaned = (role or "").strip().lower()
    return {"doctor": "Doctor", "nurse": "Nurse", "admin": "Admin", "patient": "Patient"}.get(
        cleaned, (role or "").strip()
    )


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=AuthOut)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
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
        password_hash=hash_password(password),
        role=requested_role,
        role_status="approved" if is_first_user else "pending",
        hospital_name=(data.hospital_name or "").strip() or None,
    )
    db.add(user)
    db.commit()
    logger.info("Registered %s as %s (%s)", email, requested_role, user.role_status, extra={"event": "register"})

    if user.role_status == "approved":
        return {"ok": True, "message": "Account created successfully."}
    return {"ok": True, "message": "Account created. An admin must approve this role before login."}


@router.post("/login", response_model=LoginOut)
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    rate_limit_key = f"{email}|{get_client_ip(request)}"

    retry_after = login_rate_limiter.seconds_until_unblocked(rate_limit_key)
    if retry_after:
        return JSONResponse(
            status_code=429,
            content={
                "ok": False,
                "message": f"Too many failed login attempts. Please try again in {retry_after} seconds.",
            },
            headers={"Retry-After": str(retry_after)},
        )

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(data.password, user.password_hash):
        login_rate_limiter.register_failure(rate_limit_key)
        logger.info("Failed login for %s", email, extra={"event": "login_failed"})
        return {"ok": False, "message": "Invalid email or password."}

    login_rate_limiter.reset(rate_limit_key)

    role_status = (getattr(user, "role_status", "approved") or "approved").lower()
    if role_status != "approved":
        return {
            "ok": False,
            "message": (
                "Your role request is pending admin approval."
                if role_status == "pending"
                else "Your role request was rejected."
            ),
        }

    user.last_login_at = datetime.now(UTC)
    db.commit()

    token, expires_in = create_access_token(user)
    profile = serialize_user(user)
    logger.info("Login for %s (%s)", user.email, user.role, extra={"event": "login", "user": user.email})
    return {
        "ok": True,
        "message": "Login successful.",
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": profile,
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": compose_full_name(user.first_name, user.last_name),
        "role": user.role,
        "role_status": role_status,
    }


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return serialize_user(user)


@router.post("/request-reset", response_model=GenericMessageOut)
def request_reset(data: ForgotPasswordIn, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"ok": False, "message": "No MediTrust account was found for this email."}

    code = otp_store.generate_code(email)
    try:
        delivery_mode = send_reset_code_email(email, code)
    except EmailDeliveryError:
        otp_store.clear(email)
        return {"ok": False, "message": "Unable to send the reset code email. Please try again later."}

    return {
        "ok": True,
        "message": (
            "Email delivery is not configured yet. The reset code is available in the server log."
            if delivery_mode == EMAIL_LOGGED
            else "A 6-digit reset code has been sent to your email."
        ),
    }


@router.post("/verify-reset-code", response_model=GenericMessageOut)
def verify_reset_code(data: VerifyResetCodeIn):
    if not otp_store.verify_code(data.email, data.code):
        return {"ok": False, "message": "Invalid or expired reset code."}
    return {"ok": True, "message": "Reset code verified successfully."}


@router.post("/reset-password", response_model=GenericMessageOut)
def reset_password(data: ResetPasswordIn, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    if not otp_store.is_verified(email):
        return {"ok": False, "message": "Reset code verification required."}

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"ok": False, "message": "User not found."}

    password, password_error = validate_password_for_bcrypt(data.new_password)
    if password_error:
        return {"ok": False, "message": password_error}

    user.password_hash = hash_password(password)
    db.commit()
    otp_store.clear(email)
    return {"ok": True, "message": "Password reset successfully."}


@router.post("/change-password", response_model=GenericMessageOut)
def change_password(
    data: ChangePasswordIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.email and data.email.lower().strip() != user.email:
        return {"ok": False, "message": "You can only change the password of the signed-in account."}

    if not verify_password(data.current_password, user.password_hash):
        return {"ok": False, "message": "Current password is incorrect."}

    new_password, password_error = validate_password_for_bcrypt(data.new_password)
    if password_error:
        return {"ok": False, "message": password_error}

    user.password_hash = hash_password(new_password)
    db.commit()
    return {"ok": True, "message": "Password changed successfully."}
