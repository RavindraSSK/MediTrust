MAX_BCRYPT_PASSWORD_BYTES = 72
PASSWORD_LENGTH_ERROR = "Password is too long. Use 72 bytes or fewer."


def normalize_password(value) -> str:
    return str(value or "")


def validate_password_for_bcrypt(value) -> tuple[str, str | None]:
    password = normalize_password(value)
    if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        return password, PASSWORD_LENGTH_ERROR
    return password, None
