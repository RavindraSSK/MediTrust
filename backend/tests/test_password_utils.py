import pytest

from app.password_utils import (
    BCRYPT_MAX_BYTES,
    MAX_PASSWORD_LENGTH,
    hash_password,
    validate_password_for_bcrypt,
    verify_password,
)


@pytest.mark.parametrize("password", [None, "", "   "])
def test_validator_rejects_missing_passwords(password):
    safe_password, error = validate_password_for_bcrypt(password)

    assert safe_password == ""
    assert error == "Password is required."


def test_validator_rejects_passwords_shorter_than_eight_characters():
    safe_password, error = validate_password_for_bcrypt("short")

    assert safe_password == "short"
    assert error == "Password must be at least 8 characters long."


def test_validator_accepts_password_within_character_and_byte_limits():
    password = "StrongPass@2026"

    assert validate_password_for_bcrypt(password) == (password, None)


@pytest.mark.parametrize(
    "password",
    [
        "a" * (MAX_PASSWORD_LENGTH + 1),
        "é" * (BCRYPT_MAX_BYTES // 2 + 1),
    ],
)
def test_validator_returns_bcrypt_safe_value_for_oversized_passwords(password):
    safe_password, error = validate_password_for_bcrypt(password)

    assert len(safe_password.encode("utf-8")) <= BCRYPT_MAX_BYTES
    assert error == f"Password must be at most {MAX_PASSWORD_LENGTH} characters long."


def test_hash_and_verify_round_trip():
    password = "StrongPass@2026"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("WrongPass@2026", password_hash)


@pytest.mark.parametrize("password_hash", [None, "", "not-a-valid-hash"])
def test_verify_rejects_missing_or_malformed_hash(password_hash):
    assert not verify_password("StrongPass@2026", password_hash)
