"""
Password helpers shared by the auth routes.

Two concerns are deliberately kept apart:

* **Policy** (``validate_password_for_bcrypt``) decides whether a *new* password is
  acceptable. It mirrors ``frontend/src/lib/passwordRules.js`` so the UI and the API agree,
  and it is only applied when a password is being set: registration, reset and change.
* **bcrypt safety** (``hash_password`` / ``verify_password``) only guarantees the value can
  be handed to bcrypt. bcrypt hashes at most 72 bytes and newer builds raise ``ValueError``
  for longer input instead of truncating silently.

Verification never applies policy. Tightening the rules must never lock out an account whose
password was created under the old rules, so ``verify_password`` coerces and truncates but
does not judge.
"""

from __future__ import annotations

import re

from passlib.context import CryptContext

BCRYPT_MAX_BYTES = 72
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 64

# Character classes required of a new password, in the order they are reported.
COMPLEXITY_RULES: tuple[tuple[str, str], ...] = (
    (r"[A-Z]", "Password must include at least one uppercase letter."),
    (r"[a-z]", "Password must include at least one lowercase letter."),
    (r"\d", "Password must include at least one number."),
    (r"[^A-Za-z0-9]", "Password must include at least one special character."),
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _coerce_to_text(password: object) -> str:
    if password is None:
        return ""
    return password if isinstance(password, str) else str(password)


def truncate_for_bcrypt(password: object) -> str:
    """Return a value that bcrypt can always hash (at most 72 bytes)."""
    text = _coerce_to_text(password)
    encoded = text.encode("utf-8")
    if len(encoded) <= BCRYPT_MAX_BYTES:
        return text
    # errors="ignore" drops a multi-byte character split by the byte boundary.
    return encoded[:BCRYPT_MAX_BYTES].decode("utf-8", errors="ignore")


def validate_password_for_bcrypt(password: object) -> tuple[str, str | None]:
    """
    Check a password that is about to be *set* and return ``(safe_password, error)``.

    ``error`` is ``None`` when the password satisfies the policy. The returned password is
    always safe to pass to bcrypt, so a caller that only needs a usable value can ignore the
    error.
    """
    text = _coerce_to_text(password)

    if not text.strip():
        return "", "Password is required."

    if len(text) < MIN_PASSWORD_LENGTH:
        return text, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."

    if len(text) > MAX_PASSWORD_LENGTH or len(text.encode("utf-8")) > BCRYPT_MAX_BYTES:
        return truncate_for_bcrypt(text), f"Password must be at most {MAX_PASSWORD_LENGTH} characters long."

    for pattern, message in COMPLEXITY_RULES:
        if not re.search(pattern, text):
            return text, message

    return text, None


def hash_password(password: object) -> str:
    """Hash a password. Callers enforce policy first; this only guarantees bcrypt safety."""
    return pwd_context.hash(truncate_for_bcrypt(password))


def verify_password(password: object, password_hash: str | None) -> bool:
    """Verify a password against a stored hash. Never applies the policy rules."""
    if not password_hash:
        return False
    try:
        return bool(pwd_context.verify(truncate_for_bcrypt(password), password_hash))
    except (ValueError, TypeError):
        return False
