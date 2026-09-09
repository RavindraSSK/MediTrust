"""Liveness, readiness and Prometheus metrics."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import settings
from ..db import engine, get_db
from ..ml_service import model_service
from ..observability import metrics_payload
from ..rag import get_clinical_context_service

router = APIRouter(tags=["Health"])
logger = logging.getLogger("meditrust")


@router.get("/")
def root():
    return {
        "message": "MediTrust API running",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
        "ready": "/health/ready",
        "metrics": "/metrics",
        "model": "/model/info",
    }


@router.get("/health")
@router.get("/health/live")
def health():
    return {"status": "ok", "version": settings.app_version}


@router.get("/health/ready")
def readiness(response: Response, db: Session = Depends(get_db)):
    checks: dict[str, dict] = {}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = {"ok": True, "dialect": engine.dialect.name}
    except Exception:  # noqa: BLE001
        logger.exception("Readiness database check failed")
        checks["database"] = {"ok": False, "error": "Database connectivity check failed."}

    try:
        model_service.ensure_loaded()
        checks["model"] = {
            "ok": True,
            "name": model_service.info().get("model_name"),
            "version": model_service.model_version,
        }
    except Exception:  # noqa: BLE001
        logger.exception("Readiness model check failed")
        checks["model"] = {"ok": False, "error": "Model readiness check failed."}

    if settings.rag_enabled:
        try:
            status = get_clinical_context_service().status()
            checks["rag"] = {"ok": status["passages"] > 0, **status}
        except Exception:  # noqa: BLE001
            logger.exception("Readiness RAG check failed")
            checks["rag"] = {"ok": False, "error": "RAG readiness check failed."}
    else:
        checks["rag"] = {"ok": True, "enabled": False}

    ready = all(item.get("ok") for item in checks.values())
    response.status_code = 200 if ready else 503
    return {"status": "ready" if ready else "degraded", "checks": checks, "version": settings.app_version}


@router.get("/db-health")
def db_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"database": f"{engine.dialect.name} connected"}


@router.get("/metrics", include_in_schema=False)
def metrics():
    if not settings.metrics_enabled:
        return Response(status_code=404)
    payload, content_type = metrics_payload()
    return Response(content=payload, media_type=content_type)
