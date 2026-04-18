from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from .db import get_db
from .models import User
from .otp_service import otp_store
from .email_service import send_reset_code_email
from .schemas import (
    ForgotPasswordIn,
    VerifyResetCodeIn,
    ResetPasswordIn,
    ChangePasswordIn,
    GenericMessageOut,
)

router = APIRouter(prefix="/auth", tags=["Auth Extras"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/request-reset", response_model=GenericMessageOut)
def request_reset(data: ForgotPasswordIn, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    # security-safe response
    if not user:
        return {
            "ok": True,
            "message": "If this email exists, a reset code has been sent."
        }

    code = otp_store.generate_code(email)
    send_reset_code_email(email, code)

    return {
        "ok": True,
        "message": "If this email exists, a reset code has been sent."
    }


@router.post("/verify-reset-code", response_model=GenericMessageOut)
def verify_reset_code(data: VerifyResetCodeIn):
    valid = otp_store.verify_code(data.email, data.code)

    if not valid:
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

    user.password_hash = pwd_context.hash(data.new_password)
    db.commit()
    otp_store.clear(email)

    return {"ok": True, "message": "Password reset successfully."}


@router.post("/change-password", response_model=GenericMessageOut)
def change_password(data: ChangePasswordIn, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    if not user:
        return {"ok": False, "message": "User not found."}

    if not pwd_context.verify(data.current_password, user.password_hash):
        return {"ok": False, "message": "Current password is incorrect."}

    user.password_hash = pwd_context.hash(data.new_password)
    db.commit()

    return {"ok": True, "message": "Password changed successfully."}
