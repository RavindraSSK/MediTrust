"""
MediTrust API application factory.

Startup: create tables, run idempotent migrations, seed the universal admin,
warm the ML model and the RAG index (failures are logged and surfaced through
/health/ready instead of crashing the process).
"""

from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .config import settings
from .db import Base, SessionLocal, engine
from .migrations import run_migrations
from .ml_service import InvalidClinicalInputError, ModelNotLoadedError, model_service
from .models import User
from .observability import APP_INFO, RequestContextMiddleware, configure_logging
from .password_utils import hash_password, verify_password
from .routers import admin, auth, health, model, predictions, rag

configure_logging(settings.log_level, settings.log_json)
logger = logging.getLogger("meditrust")

UNIVERSAL_ADMIN_ROLE = "Admin"
UNIVERSAL_ADMIN_STATUS = "approved"


def ensure_universal_admin(db: Session) -> None:
    """
    Seed (or repair) the universal admin account. The password is only ever
    (re)set from ADMIN_PASSWORD; when it is unset and the account does not
    exist, a one-time password is generated.
    """
    admin_email = settings.admin_email
    env_password = settings.admin_password or None
    admin = db.query(User).filter(User.email == admin_email).first()

    if not admin:
        password = env_password or secrets.token_urlsafe(16)
        if not env_password:
            logger.warning(
                "ADMIN_PASSWORD is not set. Generated a one-time admin password for %s "
                "(set ADMIN_PASSWORD and restart to control this credential)",
                admin_email,
            )
        admin = User(
            full_name="MediTrust Admin",
            first_name="MediTrust",
            last_name="Admin",
            email=admin_email,
            password_hash=hash_password(password),
            role=UNIVERSAL_ADMIN_ROLE,
            role_status=UNIVERSAL_ADMIN_STATUS,
            hospital_name="MediTrust",
        )
        db.add(admin)
        db.commit()
        logger.info("Seeded universal admin account %s", admin_email)
        return

    changed = False
    if admin.role != UNIVERSAL_ADMIN_ROLE:
        admin.role = UNIVERSAL_ADMIN_ROLE
        changed = True
    if (admin.role_status or "").lower() != UNIVERSAL_ADMIN_STATUS:
        admin.role_status = UNIVERSAL_ADMIN_STATUS
        changed = True
    if env_password and not verify_password(env_password, admin.password_hash):
        admin.password_hash = hash_password(env_password)
        changed = True
        logger.info("Rotated universal admin password from ADMIN_PASSWORD")
    if changed:
        db.commit()


def warm_up() -> None:
    try:
        model_service.load()
    except Exception as exc:  # noqa: BLE001
        logger.error("Model not available at startup: %s", exc)

    if settings.rag_enabled:
        try:
            from .rag import get_clinical_context_service

            get_clinical_context_service()
        except Exception as exc:  # noqa: BLE001
            logger.error("RAG index not available at startup: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s %s (%s)", settings.app_name, settings.app_version, settings.environment)
    Base.metadata.create_all(bind=engine)
    run_migrations(engine)
    db = SessionLocal()
    try:
        ensure_universal_admin(db)
    finally:
        db.close()
    warm_up()
    APP_INFO.labels(settings.app_version, settings.environment).set(1)
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Explainable cardiovascular risk prediction with SHAP attributions and a "
            "retrieval-augmented clinical context layer. Decision support only."
        ),
        lifespan=lifespan,
    )

    # Request context (logging/metrics) sits inside CORS so error responses keep CORS headers.
    app.add_middleware(RequestContextMiddleware, metrics_enabled=settings.metrics_enabled)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(predictions.router)
    app.include_router(admin.router)
    app.include_router(rag.router)
    app.include_router(model.router)

    @app.exception_handler(InvalidClinicalInputError)
    async def invalid_input_handler(request: Request, exc: InvalidClinicalInputError):
        return JSONResponse(status_code=422, content={"detail": "Invalid clinical input.", "errors": exc.errors})

    @app.exception_handler(ModelNotLoadedError)
    async def model_missing_handler(request: Request, exc: ModelNotLoadedError):
        return JSONResponse(status_code=503, content={"detail": f"Risk model unavailable: {exc}"})

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        errors = [
            f"{'.'.join(str(loc) for loc in err.get('loc', []) if loc != 'body')}: {err.get('msg')}"
            for err in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": "Validation failed.", "errors": errors})

    return app


app = create_app()
