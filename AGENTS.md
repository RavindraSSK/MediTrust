# AGENTS.md

Guidance for automated agents (and humans) working in this repository.

## Layout

- **backend/** – FastAPI app (`backend/app/main.py` builds the app; routers live in
  `backend/app/routers/`). JWT auth in `security.py`, model serving in `ml_service.py`, the RAG
  layer in `backend/app/rag/`, settings in `config.py`, Prometheus/logging in `observability.py`.
- **frontend/** – React 19 + Vite single-page app (`frontend/src`). The old static HTML/JS site was
  removed; legacy `.html` URLs redirect inside the router. Build output goes to `frontend/dist`.
- **ml/** – training pipeline. `ml/src/data_dictionary.py` is the single source of truth for feature
  codes/labels (the backend imports it); `preprocess.py` → `train_models.py` produce
  `ml/models/*` (committed) and `ml/reports/*.png`.
- **deploy/** – nginx, systemd, `deploy.sh`, production compose override and the deployment guide.

## Environment

- Use the system interpreter `python3` (no venv in the cloud sandbox):
  `pip install --break-system-packages -r backend/requirements-dev.txt -r ml/requirements.txt`.
  If `import jwt` panics with a missing `_cffi_backend`, run `pip install --break-system-packages cffi`.
- Node 22 for the frontend: `cd frontend && npm install`.
- `backend/.env` is optional. Without it the API uses SQLite at `backend/meditrust_dev.db`, generates
  a JWT secret into `backend/.jwt_secret` (git-ignored) and seeds the admin `meditrust@gmail.com`
  with `ADMIN_PASSWORD` (a one-time password is logged when unset). Docker is not available in the
  sandbox; `docker compose config` still validates the compose files.

## Running

```bash
python3 -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001 --reload   # API
cd frontend && npm run dev                                                                # http://127.0.0.1:5173
cd frontend && npm run build && npx vite preview --port 4173                              # production build
```

The frontend resolves the API base automatically: local dev origins (5173/4173/5500) talk to
`http://127.0.0.1:8001`; a production build served behind nginx uses `/api` (`VITE_API_BASE`).

## Tests, lint, training

```bash
python3 -m pytest backend/tests ml/tests -p no:cacheprovider    # 56 tests, ~1 min (SHAP warm-up)
python3 -m ruff check backend ml && python3 -m ruff format --check backend ml
cd frontend && npm run lint && npm run build
python3 ml/src/preprocess.py && python3 ml/src/train_models.py   # ~1-2 min, rewrites ml/models + ml/reports
```

## Domain rules that must not regress

- The label is `1 = angiographic coronary artery disease`. The Kaggle CSV in `ml/data/raw` has the
  label inverted and re-coded categories; always go through `decode_kaggle_frame`.
- Clinical codes are the original UCI ones: `cp` 1-4, `restecg` 0-2, `slope` 1-3, `thal` 3/6/7,
  `ca` 0-3. `/predict` rejects anything else with HTTP 422.
- Risk bands come from `ml/models/model_metadata.json` (`thresholds.rule_out` / `rule_in`), not
  hard-coded numbers. `backend/tests/test_predict.py` asserts the demo patient is High and the
  healthy patient is Low.
- The RAG layer never changes the model output; it receives probability/band read-only and echoes
  them in `clinical_context.model_output`. Guardrails live in `backend/app/rag/service.py`.
- Admin/nurse identity comes from the JWT (`require_roles`), never from request headers.

## Deployment notes

- Production: see `deploy/README.md`. `deploy.yml` builds images to GHCR, optionally syncs
  `ml/models` to S3 (`MODEL_S3_BUCKET`), then runs `deploy/deploy.sh` on the EC2 host over SSH.
- `startup.txt` was replaced by `backend/gunicorn.conf.py`
  (`gunicorn -c gunicorn.conf.py app.main:app`).
- Set `JWT_SECRET`, `ADMIN_PASSWORD`, `ALLOWED_ORIGINS` and `DATABASE_URL` (RDS) in the production
  `backend/.env`. `GEMINI_API_KEY` is optional (template narratives otherwise).
