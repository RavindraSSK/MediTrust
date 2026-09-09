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

## 6. The instance was stopped ("paused") and the site is down

Stopping an EC2 instance to save credits is fine, but three things break when it comes back:

1. **The public IP changes** unless an Elastic IP is attached, so `meditrust.ddns.net` keeps
   pointing at the old address (the No-IP record is not updated automatically).
2. Containers only return if Docker starts at boot (`sudo systemctl enable docker`).
3. Nothing is deployed at all if the instance is still stopped.

### Run the deployment on the instance, not in CloudShell

AWS CloudShell is a browser terminal in the console. It is a throwaway container with no Docker
daemon and an ephemeral filesystem, so cloning the repository there deploys nothing. Use CloudShell
to *inspect* the account and to *connect*; run the bootstrap on the EC2 host itself.
`deploy/ec2-bootstrap.sh` refuses to run in CloudShell for this reason.

### Recovery checklist (about 10 minutes)

1. **From CloudShell**, get the facts (read-only, changes nothing):

   ```bash
   git clone https://github.com/RavindraSSK/MediTrust.git ~/meditrust && cd ~/meditrust
   ./deploy/aws-status.sh
   ```

   It prints every instance with its state and public IP, the inbound security-group rules, any
   Elastic IPs, what `meditrust.ddns.net` currently resolves to, and the exact next command.
   If it finds nothing, the region is probably wrong: `export AWS_REGION=us-east-1`.

2. **Start the instance** if it is stopped:

   ```bash
   aws ec2 start-instances --instance-ids <instance-id>
   aws ec2 wait instance-running --instance-ids <instance-id>
   ```

3. **Attach an Elastic IP** so the address stops changing on every restart. It is free while
   associated with a running instance:

   ```bash
   aws ec2 allocate-address --domain vpc                     # note the AllocationId
   aws ec2 associate-address --instance-id <instance-id> --allocation-id <eipalloc-...>
   ```

4. **Point the DNS name at that IP.** Either edit the record in the No-IP dashboard, or install the
   updater on the host so it syncs itself on every boot:

   ```bash
   sudo mkdir -p /etc/meditrust
   sudo tee /etc/meditrust/ddns.env >/dev/null <<'ENV'
   NOIP_HOSTNAME=meditrust.ddns.net
   NOIP_USERNAME=<no-ip account email or DDNS key id>
   NOIP_PASSWORD=<no-ip password or DDNS key>
   ENV
   sudo chmod 600 /etc/meditrust/ddns.env
   ```

5. **Open the ports**: inbound TCP 80 (443 for TLS, 22 for SSH) in the instance security group.

6. **Connect to the instance and deploy.** Session Manager needs no SSH key, but does need the SSM
   agent plus an instance role with `AmazonSSMManagedInstanceCore`:

   ```bash
   aws ssm start-session --target <instance-id>
   # or:  ssh -i ~/key.pem ec2-user@<public-ip>     (Ubuntu images use the 'ubuntu' user)
   ```

   Then, on the instance:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/RavindraSSK/MediTrust/main/deploy/ec2-bootstrap.sh \
     | BRANCH=main bash
   curl http://127.0.0.1/api/health/ready
   ```

   The bootstrap installs Docker and the compose plugin on Amazon Linux (`dnf`/`yum`) or
   Debian/Ubuntu (`apt`), enables the Docker service so the stack survives a reboot, writes
   `backend/.env` with a generated admin password and JWT secret if none exists, and starts the
   stack (pulling the GHCR images, or building them on the host when they are not published yet).

   **Until PR #79 is merged, `main` cannot start** (`backend/app/password_utils.py` is missing there
   and the API crashes on import). The bootstrap checks for this and stops with a clear message.
   Deploy the branch instead: `BRANCH=claude/clinical-risk-platform-completion-ohnfgm`.

7. **Verify from your laptop** once DNS has propagated (No-IP TTL is 60 s):

   ```bash
   curl -I http://meditrust.ddns.net/api/health/ready
   ```

### Before the credits run out

Stop the instance and release the Elastic IP (an unattached Elastic IP is billed), or take an AMI
snapshot. The repository plus `ec2-bootstrap.sh` recreates the whole environment later; only the
database contents are lost, so run `pg_dump` first if the recorded cases matter.
