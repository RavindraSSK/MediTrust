"""
Logging, request tracing and Prometheus metrics.

* ``configure_logging`` sets up plain or JSON logs (LOG_JSON=1) for stdout so
  CloudWatch / docker logs capture everything.
* ``RequestContextMiddleware`` assigns an ``X-Request-ID`` to every request,
  logs method/path/status/latency and records Prometheus metrics with the
  route template (``/cases/{case_id}``) rather than the raw path to keep label
  cardinality bounded.
* Domain metrics (predictions, model load state, RAG generations, LLM
  failures) are defined here and updated by the services.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
import uuid
from contextvars import ContextVar

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

REQUEST_COUNT = Counter(
    "meditrust_http_requests_total",
    "HTTP requests processed",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "meditrust_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
REQUESTS_IN_PROGRESS = Gauge("meditrust_http_requests_in_progress", "In-flight HTTP requests")
PREDICTIONS_TOTAL = Counter("meditrust_predictions_total", "Risk predictions served", ["risk_level"])
PREDICTION_LATENCY = Histogram(
    "meditrust_prediction_duration_seconds",
    "End-to-end /predict latency (model + SHAP + RAG)",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0),
)
MODEL_LOADED = Gauge("meditrust_model_loaded", "1 when the ML model is loaded")
MODEL_INFO = Gauge("meditrust_model_info", "Static model metadata", ["model_name", "model_version"])
RAG_INDEX_PASSAGES = Gauge("meditrust_rag_index_passages", "Passages in the RAG index")
RAG_GENERATIONS = Counter("meditrust_rag_generations_total", "Clinical context generations", ["mode"])
LLM_FAILURES = Counter("meditrust_llm_failures_total", "LLM calls that failed or were rejected", ["reason"])
APP_INFO = Gauge("meditrust_app_info", "Application build information", ["version", "environment"])

_ID_SEGMENT = re.compile(r"/\d+(?=/|$)")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key in ("method", "path", "status", "duration_ms", "user", "event"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload)


def configure_logging(level: str = "INFO", json_logs: bool = False) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    if json_logs:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"))
    root.addHandler(handler)

    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    for name in ("uvicorn", "uvicorn.error", "gunicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True


def path_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if path:
        return path
    return _ID_SEGMENT.sub("/{id}", request.url.path)


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, metrics_enabled: bool = True):
        super().__init__(app)
        self.metrics_enabled = metrics_enabled
        self.logger = logging.getLogger("meditrust.request")

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        status_code = 500
        REQUESTS_IN_PROGRESS.inc()
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration = time.perf_counter() - started
            REQUESTS_IN_PROGRESS.dec()
            template = path_template(request)
            if self.metrics_enabled and template not in {"/metrics", "/health", "/health/live"}:
                REQUEST_COUNT.labels(request.method, template, str(status_code)).inc()
                REQUEST_LATENCY.labels(request.method, template).observe(duration)
            if template not in {"/metrics", "/health", "/health/live", "/health/ready"}:
                self.logger.info(
                    "%s %s -> %s in %.1f ms",
                    request.method,
                    request.url.path,
                    status_code,
                    duration * 1000,
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status": status_code,
                        "duration_ms": round(duration * 1000, 1),
                    },
                )
            request_id_ctx.reset(token)


def metrics_payload() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
