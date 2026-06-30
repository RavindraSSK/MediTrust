from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from .db import get_db
from .models import User
from .otp_service import otp_store
from .email_service import EMAIL_LOGGED, EmailDeliveryError, send_reset_code_email
from .password_utils import validate_password_for_bcrypt
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

    if not user:
        return {
            "ok": False,
            "message": "No MediTrust account was found for this email."
        }

    code = otp_store.generate_code(email)
    try:
        delivery_mode = send_reset_code_email(email, code)
    except EmailDeliveryError:
        otp_store.clear(email)
        return {
            "ok": False,
            "message": "Unable to send the reset code email. Please try again later.",
        }

    return {
        "ok": True,
        "message": (
            "Email delivery is not configured yet. The reset code is available in the server log."
            if delivery_mode == EMAIL_LOGGED
            else "A 6-digit reset code has been sent to your email."
        )
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

    password, password_error = validate_password_for_bcrypt(data.new_password)
    if password_error:
        return {"ok": False, "message": password_error}

    user.password_hash = pwd_context.hash(password)
    db.commit()
    otp_store.clear(email)

    return {"ok": True, "message": "Password reset successfully."}


@router.post("/change-password", response_model=GenericMessageOut)
def change_password(data: ChangePasswordIn, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    if not user:
        return {"ok": False, "message": "User not found."}

    current_password, _ = validate_password_for_bcrypt(data.current_password)
    if not pwd_context.verify(current_password, user.password_hash):
        return {"ok": False, "message": "Current password is incorrect."}

    new_password, password_error = validate_password_for_bcrypt(data.new_password)
    if password_error:
        return {"ok": False, "message": password_error}

    user.password_hash = pwd_context.hash(new_password)
    db.commit()

    return {"ok": True, "message": "Password changed successfully."}
