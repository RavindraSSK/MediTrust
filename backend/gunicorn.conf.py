"""Gunicorn configuration for the MediTrust API (production)."""

import os

# PaaS hosts that inject a $PORT (Render, Heroku-style buildpacks, etc.) expect the
# process to bind to it; the platform's own port-forwarding does not read our Docker
# EXPOSE directive. Fall back to 8000 for docker-compose / EC2, where PORT is unset.
_port = os.getenv("PORT")
_default_bind = f"0.0.0.0:{_port}" if _port else "0.0.0.0:8000"
bind = os.getenv("GUNICORN_BIND", _default_bind)
workers = int(os.getenv("GUNICORN_WORKERS", "2"))
worker_class = "uvicorn.workers.UvicornWorker"
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = 30
keepalive = 5
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = 100

# Request logging is handled by the app middleware (with request ids), so the
# gunicorn access log would only duplicate it.
accesslog = None
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
capture_output = True
