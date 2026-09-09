# Deploying MediTrust

MediTrust ships as two containers (FastAPI backend, nginx-served React frontend) plus
PostgreSQL. It runs the same way on a laptop, on a single EC2 instance, or with the
database on RDS and model artifacts on S3.

```
                 GitHub Actions (ci.yml / deploy.yml)
   push to main ─► tests ─► build images ─► GHCR ─► ssh EC2 ─► deploy.sh ─► /health/ready
                                  └──────► S3 (model artifacts, optional)

   Browser ──► nginx (:80, React build, /api/* proxy) ──► gunicorn+uvicorn (:8000)
                                                            ├─ PostgreSQL (RDS or container)
                                                            ├─ ml/models (local or synced from S3)
                                                            └─ Gemini (optional, RAG narrative)
```

## 1. Local full stack

```bash
cp backend/.env.example backend/.env       # set ADMIN_PASSWORD, JWT_SECRET, GEMINI_API_KEY (optional)
docker compose up -d --build               # db + backend + frontend
open http://localhost:8080                 # API docs: http://localhost:8000/docs
```

Only the database (run the API with uvicorn and the frontend with Vite):

```bash
docker compose up -d db
python3 -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001 --reload
cd frontend && npm run dev                 # http://127.0.0.1:5173 -> API at http://127.0.0.1:8001
```

## 2. AWS EC2 (Docker mode, recommended)

1. Launch an Ubuntu 22.04+ instance, open ports 22 and 80/443, install Docker + the compose plugin.
2. `sudo mkdir -p /opt/meditrust && sudo chown $USER /opt/meditrust && git clone <repo> /opt/meditrust`
3. Create `/opt/meditrust/backend/.env` from `.env.example`:
   * `DATABASE_URL` → RDS PostgreSQL (`postgresql+psycopg2://user:pw@host:5432/meditrust?sslmode=require`)
     or leave unset to use the compose `db` service.
   * `ADMIN_PASSWORD`, `JWT_SECRET` (long random string), `ALLOWED_ORIGINS=http://meditrust.ddns.net`.
   * `MODEL_S3_URI=s3://<bucket>/models/latest` if CI publishes models to S3 (instance role or AWS keys).
   * `GEMINI_API_KEY` for LLM narratives (the deterministic RAG template is used without it).
4. First start: `IMAGE_TAG=latest ./deploy/deploy.sh` (pulls images from GHCR and starts the stack).
5. Point DNS (`meditrust.ddns.net`) at the instance. For TLS terminate at an ALB/CloudFront or run
   certbot on a host nginx in front of port 80.

GitHub Actions secrets for automatic deploys (`.github/workflows/deploy.yml`):

| Secret | Purpose |
| --- | --- |
| `EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY` | SSH access used by `appleboy/ssh-action` |
| `EC2_APP_DIR` | checkout path on the host (default `/opt/meditrust`) |
| `DEPLOY_MODE` | `docker` (default) or `native` |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `MODEL_S3_BUCKET` | optional S3 model publishing |
| `PUBLIC_URL` | e.g. `http://meditrust.ddns.net`, used for the post-deploy readiness check |

Images are published as `ghcr.io/<owner>/meditrust-backend` and `ghcr.io/<owner>/meditrust-frontend`
tagged with the commit SHA and `latest`.

## 3. AWS EC2 (native mode, no containers)

Matches the original deployment (gunicorn behind host nginx):

```bash
sudo apt install -y python3-venv nginx nodejs npm
git clone <repo> /opt/meditrust && cd /opt/meditrust
cp backend/.env.example backend/.env && nano backend/.env
sudo cp deploy/systemd/meditrust-backend.service /etc/systemd/system/
sudo cp deploy/nginx/meditrust.conf /etc/nginx/sites-available/meditrust
sudo ln -sf /etc/nginx/sites-available/meditrust /etc/nginx/sites-enabled/meditrust
sudo rm -f /etc/nginx/sites-enabled/default
DEPLOY_MODE=native ./deploy/deploy.sh    # venv + pip, npm build -> /var/www/meditrust, systemd + nginx reload
```

The React build must be served from `/var/www/meditrust` (or the nginx `root` changed); the old
static `frontend/*.html` files no longer exist.

## 4. Health checks, logging and monitoring

| Endpoint | Purpose |
| --- | --- |
| `GET /health` (`/health/live`) | liveness, used by Docker `HEALTHCHECK` |
| `GET /health/ready` | readiness: database ping, model loaded, RAG index built (503 when degraded) |
| `GET /metrics` | Prometheus exposition: request counts/latency by route, predictions by risk band, model loaded, RAG generations, LLM failures |
| `GET /model/info` | model card: selected model, CV / test metrics, thresholds, global SHAP importance |

* Logs go to stdout with a request id (`X-Request-ID` header, also returned to clients). Set
  `LOG_JSON=true` for JSON lines (CloudWatch Logs / Loki friendly). `docker compose logs -f backend`.
* Scrape `/metrics` with Prometheus (or the CloudWatch agent's Prometheus support) and alert on
  `meditrust_model_loaded == 0`, 5xx rate from `meditrust_http_requests_total`, and p95 of
  `meditrust_prediction_duration_seconds`.
* Every prediction row stores the `model_version` that produced it; rows with `NULL` were produced
  by the pre-fix (label-inverted) model and are flagged as *legacy* in the UI.

## 5. Model lifecycle

```bash
python3 ml/src/preprocess.py      # decode Kaggle file -> canonical encoding, split, preprocessor
python3 ml/src/train_models.py    # LR / RF / XGBoost benchmark, thresholds, model card, reports
pytest backend/tests ml/tests     # API + ML tests (uses the new artifacts)
```

Commit the refreshed `ml/models/*` (model, preprocessor, model card) or let the deploy workflow
publish them to `s3://$MODEL_S3_BUCKET/models/<version>` and `models/latest`; the backend downloads
`MODEL_S3_URI` at startup and exposes the version in `/model/info`, `/health/ready` and every
prediction.
