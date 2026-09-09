"""Shared password validation for endpoints backed by bcrypt."""

import re


def validate_password_for_bcrypt(password: str) -> tuple[str, str | None]:
    """Return the password and a user-facing validation error, if any.

    The rules intentionally mirror ``frontend/js/auth/password-rules.js``.
    Checking the encoded length also prevents bcrypt from raising an exception
    for inputs larger than its 72-byte limit (non-ASCII characters may use
    more than one byte).
    """
    if len(password.encode("utf-8")) > 72:
        return "", "Password is too long for secure storage."
    if not 8 <= len(password) <= 12:
        return password, "Password must be 8 to 12 characters long."
    if not re.search(r"[A-Z]", password):
        return password, "Password must include at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return password, "Password must include at least one lowercase letter."
    if not re.search(r"\d", password):
        return password, "Password must include at least one number."
    if not re.search(r"[^A-Za-z0-9]", password):
        return password, "Password must include at least one special character."

    return password, None
"""
Password helpers shared by the auth routes.

bcrypt only hashes the first 72 bytes of a password and newer bcrypt builds
raise ``ValueError`` for longer inputs instead of silently truncating. Every
password that reaches ``passlib`` therefore goes through
``validate_password_for_bcrypt`` first so callers get a clear error message
instead of a 500.
"""

from __future__ import annotations

from passlib.context import CryptContext

BCRYPT_MAX_BYTES = 72
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 64

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def validate_password_for_bcrypt(password: object) -> tuple[str, str | None]:
    """
    Normalise a submitted password and return ``(password, error_message)``.

    ``error_message`` is ``None`` when the password is acceptable. The returned
    password is always safe to pass to bcrypt (it never exceeds 72 bytes), so
    callers that only need to *verify* an existing hash can ignore the error.
    """
    if password is None:
        return "", "Password is required."

    if not isinstance(password, str):
        password = str(password)

    if not password.strip():
        return "", "Password is required."

    if len(password) < MIN_PASSWORD_LENGTH:
        return password, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."

    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES or len(password) > MAX_PASSWORD_LENGTH:
        # Truncate so verification of legacy hashes can never crash bcrypt.
        safe = encoded[:BCRYPT_MAX_BYTES].decode("utf-8", errors="ignore")
        return safe, f"Password must be at most {MAX_PASSWORD_LENGTH} characters long."

    return password, None


def hash_password(password: str) -> str:
    safe, _ = validate_password_for_bcrypt(password)
    return pwd_context.hash(safe)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    safe, _ = validate_password_for_bcrypt(password)
    try:
        return bool(pwd_context.verify(safe, password_hash))
    except (ValueError, TypeError):
        return False
