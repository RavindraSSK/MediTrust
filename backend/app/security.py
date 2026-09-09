"""
JWT authentication and role-based access control.

Tokens are signed HS256 bearer tokens carrying the user id, email and role.
Routes declare the roles they accept with ``require_roles`` and the current
user is always re-read from the database so role or approval changes made by
an admin take effect immediately.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Iterable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

ROLE_DOCTOR = "Doctor"
ROLE_NURSE = "Nurse"
ROLE_ADMIN = "Admin"
ROLE_PATIENT = "Patient"

CLINICAL_ROLES: tuple[str, ...] = (ROLE_DOCTOR, ROLE_NURSE, ROLE_ADMIN)
VALID_ROLES: set[str] = {ROLE_DOCTOR, ROLE_NURSE, ROLE_ADMIN, ROLE_PATIENT}
APPROVED = "approved"


def create_access_token(user: User, expires_minutes: int | None = None) -> tuple[str, int]:
    """Return ``(token, expires_in_seconds)`` for the given user."""
    minutes = expires_minutes or settings.jwt_expire_minutes
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=minutes)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "name": user.full_name,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "type": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    if isinstance(token, bytes):  # PyJWT < 2 compatibility
        token = token.decode("utf-8")
    return token, int(minutes * 60)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.get("type") != "access" or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token.") from exc

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account no longer exists.")

    role_status = (getattr(user, "role_status", APPROVED) or APPROVED).lower()
    if role_status != APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not approved for access.",
        )
    return user


def require_roles(*roles: str):
    """Dependency factory: the current user must hold one of ``roles``."""
    allowed: set[str] = set(roles)

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            logger.info("RBAC denied user=%s role=%s required=%s", user.email, user.role, sorted(allowed))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of the roles: {', '.join(sorted(allowed))}.",
            )
        return user

    return dependency


def require_any_role(roles: Iterable[str]):
    return require_roles(*roles)


require_clinical_user = require_roles(*CLINICAL_ROLES)
require_admin = require_roles(ROLE_ADMIN)
require_doctor = require_roles(ROLE_DOCTOR, ROLE_ADMIN)
require_nurse = require_roles(ROLE_NURSE, ROLE_ADMIN)
