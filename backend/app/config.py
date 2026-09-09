"""
Application settings.

Values are read from environment variables. A ``backend/.env`` file is loaded
first (without overriding variables that are already exported) so local
development, Docker and EC2 deployments all use the same knobs.
"""

from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]  # repository root
BACKEND_DIR = BASE_DIR / "backend"
ML_DIR = BASE_DIR / "ml"
ENV_PATH = BACKEND_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)
load_dotenv()

logger = logging.getLogger(__name__)


def env_str(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def env_int(name: str, default: int) -> int:
    raw = env_str(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid integer for %s=%r; using %s", name, raw, default)
        return default


def env_float(name: str, default: float) -> float:
    raw = env_str(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("Invalid float for %s=%r; using %s", name, raw, default)
        return default


def env_bool(name: str, default: bool) -> bool:
    raw = env_str(name)
    if not raw:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    raw = env_str(name)
    if not raw:
        return list(default or [])
    return [item.strip() for item in raw.split(",") if item.strip()]


DEFAULT_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:5501",
    "http://localhost:5501",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:4173",
    "http://localhost:4173",
    "http://127.0.0.1:8080",
    "http://localhost:8080",
]


def _resolve_jwt_secret() -> str:
    """
    Use JWT_SECRET when provided. Otherwise persist a random secret next to
    the backend so every gunicorn worker (and restart) shares the same key.
    """
    configured = env_str("JWT_SECRET")
    if configured:
        return configured

    secret_file = Path(env_str("JWT_SECRET_FILE", str(BACKEND_DIR / ".jwt_secret")))
    try:
        if secret_file.exists():
            existing = secret_file.read_text().strip()
            if existing:
                return existing
        generated = secrets.token_urlsafe(48)
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        secret_file.write_text(generated)
        try:
            os.chmod(secret_file, 0o600)
        except OSError:
            pass
        logger.warning(
            "JWT_SECRET is not set; generated a secret at %s. Set JWT_SECRET in production.",
            secret_file,
        )
        return generated
    except OSError:
        logger.warning("JWT_SECRET is not set and the secret file is not writable; using an in-memory secret.")
        return secrets.token_urlsafe(48)


@dataclass
class Settings:
    app_name: str = "MediTrust API"
    app_version: str = env_str("APP_VERSION", "1.0.0")
    environment: str = env_str("APP_ENV", "development")

    database_url: str = env_str("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'meditrust_dev.db'}")

    jwt_secret: str = field(default_factory=_resolve_jwt_secret)
    jwt_algorithm: str = env_str("JWT_ALGORITHM", "HS256")
    jwt_expire_minutes: int = env_int("JWT_EXPIRE_MINUTES", 12 * 60)

    admin_email: str = env_str("ADMIN_EMAIL", "meditrust@gmail.com").lower()
    admin_password: str = env_str("ADMIN_PASSWORD")

    allowed_origins: list[str] = field(
        default_factory=lambda: list(dict.fromkeys(DEFAULT_ALLOWED_ORIGINS + env_list("ALLOWED_ORIGINS")))
    )

    login_max_attempts: int = env_int("LOGIN_MAX_ATTEMPTS", 5)
    login_window_seconds: int = env_int("LOGIN_WINDOW_SECONDS", 900)

    gemini_api_key: str = env_str("GEMINI_API_KEY")
    gemini_model: str = env_str("GEMINI_MODEL", "gemini-2.5-flash")
    gemini_timeout_ms: int = env_int("GEMINI_TIMEOUT_MS", 15000)

    rag_enabled: bool = env_bool("RAG_ENABLED", True)
    rag_top_k: int = env_int("RAG_TOP_K", 6)
    rag_use_llm: bool = env_bool("RAG_USE_LLM", True)
    rag_embedding_model: str = env_str("RAG_EMBEDDING_MODEL")  # optional sentence-transformers model
    rag_corpus_dir: Path = Path(env_str("RAG_CORPUS_DIR", str(BACKEND_DIR / "app" / "rag" / "corpus")))

    model_dir: Path = Path(env_str("MODEL_DIR", str(ML_DIR / "models")))
    background_data_path: Path = Path(
        env_str("BACKGROUND_DATA_PATH", str(ML_DIR / "data" / "processed" / "heart_disease_clean.csv"))
    )
    model_s3_uri: str = env_str("MODEL_S3_URI")  # e.g. s3://meditrust-artifacts/models/latest
    aws_region: str = env_str("AWS_REGION", env_str("AWS_DEFAULT_REGION"))

    log_level: str = env_str("LOG_LEVEL", "INFO").upper()
    log_json: bool = env_bool("LOG_JSON", False)
    metrics_enabled: bool = env_bool("METRICS_ENABLED", True)

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"prod", "production"}

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


settings = Settings()
