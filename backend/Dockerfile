# syntax=docker/dockerfile:1
# Build from the repository root:  docker build -f backend/Dockerfile .
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libgomp1: OpenMP runtime for xgboost / shap; curl: container health checks.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Application code plus the ML artifacts and the canonical dataset used for SHAP background.
COPY backend /app/backend
COPY ml/src /app/ml/src
COPY ml/models /app/ml/models
COPY ml/data/processed/heart_disease_clean.csv /app/ml/data/processed/heart_disease_clean.csv

RUN useradd --create-home --uid 10001 meditrust && chown -R meditrust:meditrust /app
USER meditrust
WORKDIR /app/backend

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health/ready || exit 1

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app.main:app"]
