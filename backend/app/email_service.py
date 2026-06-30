import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr


logger = logging.getLogger(__name__)

EMAIL_SENT = "email"
EMAIL_LOGGED = "log"


class EmailDeliveryError(RuntimeError):
    pass


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _log_reset_code(email: str, code: str) -> None:
    logger.warning(
        "MediTrust password reset fallback for %s: reset code %s (expires in 10 minutes).",
        email,
        code,
    )
    print("\n" + "=" * 60)
    print("MediTrust Password Reset")
    print(f"To: {email}")
    print(f"Reset code: {code}")
    print("This code expires in 10 minutes.")
    print("=" * 60 + "\n")


def _build_message(recipient_email: str, sender_email: str, code: str) -> EmailMessage:
    sender_name = os.getenv("SMTP_FROM_NAME", "MediTrust").strip() or "MediTrust"

    message = EmailMessage()
    message["Subject"] = "MediTrust password reset code"
    message["From"] = formataddr((sender_name, sender_email))
    message["To"] = recipient_email
    message.set_content(
        "\n".join(
            [
                "Your MediTrust password reset code is below.",
                "",
                f"Reset code: {code}",
                "",
                "This code expires in 10 minutes.",
                "If you did not request a password reset, you can ignore this email.",
            ]
        )
    )
    return message


def send_reset_code_email(email: str, code: str) -> str:
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = _env_int("SMTP_PORT", 587)
    smtp_user = _first_env("SMTP_USER", "SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from_email = _first_env("SMTP_FROM_EMAIL", "SMTP_USER", "SMTP_USERNAME")
    smtp_use_tls = _env_flag("SMTP_USE_TLS", True)
    smtp_use_ssl = _env_flag("SMTP_USE_SSL", False)
    smtp_timeout = _env_int("SMTP_TIMEOUT_SECONDS", 20)
    fallback_to_log = _env_flag("SMTP_FALLBACK_TO_LOG", True)

    if not smtp_host or not smtp_from_email:
        if fallback_to_log:
            _log_reset_code(email, code)
            return EMAIL_LOGGED
        raise EmailDeliveryError("SMTP is not configured.")

    if bool(smtp_user) != bool(smtp_password):
        logger.error("SMTP_USER and SMTP_PASSWORD must both be set when SMTP authentication is required.")
        raise EmailDeliveryError("Incomplete SMTP credentials.")

    message = _build_message(email, smtp_from_email, code)

    try:
        if smtp_use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=smtp_timeout, context=context) as server:
                if smtp_user:
                    server.login(smtp_user, smtp_password)
                server.send_message(message)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=smtp_timeout) as server:
                server.ehlo()
                if smtp_use_tls:
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                if smtp_user:
                    server.login(smtp_user, smtp_password)
                server.send_message(message)
    except Exception as exc:
        logger.exception("Failed to send password reset email to %s", email)
        raise EmailDeliveryError("Unable to send reset code email.") from exc

    logger.info("Password reset email sent to %s", email)
    return EMAIL_SENT
