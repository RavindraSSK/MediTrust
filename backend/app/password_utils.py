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
