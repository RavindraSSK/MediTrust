# AGENTS.md

## Cursor Cloud specific instructions

MediTrust is an explainable-AI cardiovascular risk platform with three parts:

- **backend/** — FastAPI app (`backend/app/main.py`), served by uvicorn. Talks to a SQL database and the ML model.
- **frontend/** — static HTML/CSS/JS (ES modules), no build step. Served as static files.
- **ml/** — scikit-learn training pipeline (`ml/src/preprocess.py`, `ml/src/train_models.py`) producing `ml/models/*.joblib`.

### Environment already prepared by the update script

The update script installs `backend/requirements.txt` into the system Python (`pip install --break-system-packages`) and creates `backend/.env` (pointing at a local SQLite DB) if it is missing. Use the system interpreter `python3` for all backend/ML commands. (A virtualenv is intentionally not used: the base image lacks `python3-venv`, so `python3 -m venv` is not reliable here.)

### Database

- Local dev uses **SQLite** via `DATABASE_URL` in `backend/.env` (e.g. `sqlite:////workspace/backend/meditrust_dev.db`). The app code supports both SQLite and PostgreSQL; tables are auto-created and migrated on startup (no manual migration step). The local `.db` file is gitignored.
- The repo also ships `docker-compose.yml` for a PostgreSQL 16 container (port 5433), which is the production-like option. Docker is NOT installed in this environment; prefer SQLite here. To use Postgres instead, start the container and set `DATABASE_URL=postgresql+psycopg2://meditrust:meditrust_pw@127.0.0.1:5433/meditrust_db`.
- On startup the backend seeds a permanent admin account. The email defaults to `meditrust@gmail.com` (override with `ADMIN_EMAIL`) and the password comes from the `ADMIN_PASSWORD` env var. The update script seeds `ADMIN_PASSWORD=DevAdmin@2026` into a freshly created `backend/.env`, so the local dev admin is `meditrust@gmail.com` / `DevAdmin@2026`. If `ADMIN_PASSWORD` is unset when the admin is first created, a random one-time password is generated and printed to the backend log. The first-ever registered user is auto-approved; any later signup is created with `role_status="pending"` and an admin must approve it before that account can log in.
- `/auth/login` is rate-limited per email+IP (5 failed attempts per 15-minute window → HTTP 429 with a `Retry-After` header). A successful login clears the counter. The limiter is in-memory/per-process, so multi-worker (gunicorn `-w N`) deployments track it per worker.

### Deployment (AWS EC2)

- Production runs gunicorn (see `backend/startup.txt`): `gunicorn -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 app.main:app`.
- **Set a strong `ADMIN_PASSWORD` in the production `backend/.env`.** Because the admin row already exists in prod, the password is only rotated when `ADMIN_PASSWORD` is explicitly set; if it is unset the existing (old) password is left unchanged.
- No DB migration step is required; `create_all` + `migrate_name_columns()` run on startup and are Postgres-safe.

### ML model artifacts

- `ml/models/model.joblib`, `ml/models/preprocessor.joblib`, and the dataset `ml/data/processed/heart_disease_clean.csv` are committed (force-added past `.gitignore`) so `/predict` works out of the box.
- If the model fails to load (e.g. a scikit-learn version mismatch), retrain from the committed dataset (run from repo root):
  ```
  python3 ml/src/preprocess.py
  python3 ml/src/train_models.py
  ```
- The committed dataset uses the Kaggle "cleaned" encoding (cp/thal/ca/slope as 0-based codes). The frontend demo prefill (`frontend/js/meditrust/init.js`) uses original Cleveland codes (e.g. `thal=7`, `cp=4`); the preprocessor's OneHotEncoder uses `handle_unknown="ignore"`, so unknown codes are silently zeroed rather than erroring. Predictions still return valid output.

### Running services (do not put these in the update script)

- Backend (port 8001, matches the frontend's hardcoded `API_BASE` in `frontend/js/services/api.js`):
  ```
  python3 -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001 --reload
  ```
- Frontend (any static server; CORS allows ports 5500/5501/5173):
  ```
  cd frontend && python3 -m http.server 5500
  ```
  Then open `http://127.0.0.1:5500/index.html`.

### Lint / test

- There is no configured linter or pytest suite. The only test is a script: `cd ml/src && python3 test_risk_stratification.py` (prints triage levels; no assertions).

### Gotchas

- `GEMINI_API_KEY` is optional. Without it, `/predict` still works and just returns `gemini_summary: null` (Gemini-based clinical summaries are skipped gracefully).
- The frontend `API_BASE` is hardcoded to `http://127.0.0.1:8001`, so run the backend on port 8001.
