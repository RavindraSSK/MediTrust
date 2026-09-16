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

> **No budget for AWS?** Skip straight to [section 7](#7-free-tier-alternative-cloudflare-pages--render--neon)
> for a genuinely $0, no-credit-card-required deployment that also auto-deploys on every
> push to `main` — no EC2, no SSM sessions, no manual `deploy.sh`.

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

   Run only commands shown in fenced code blocks. Labels such as `DNS_IP == EC2 PublicIP` and
   values written as `<instance-id>` are explanatory placeholders, not commands to paste. The
   status script prints the real instance ID and, when one exists, an exact command using an
   available Elastic IP allocation.

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

   These `systemctl` commands must be run **inside the EC2 instance after the bootstrap has
   installed the unit files**, not in CloudShell. A `unit meditrust-ddns.timer does not exist`
   error means the command was run on the wrong machine or bootstrap has not installed the units:

   ```bash
   sudo install -m 0755 deploy/ddns-update.sh /usr/local/bin/meditrust-ddns-update
   sudo cp deploy/systemd/meditrust-ddns.service deploy/systemd/meditrust-ddns.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now meditrust-ddns.timer
   sudo systemctl start meditrust-ddns.service
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

   The bootstrap deploys `main` by default and stops with a clear message if a required backend
   module is missing.

7. **Verify from your laptop** once DNS has propagated (No-IP TTL is 60 s):

   ```bash
   curl -I http://meditrust.ddns.net/api/health/ready
   ```

   If `getent hosts meditrust.ddns.net` returns no address, the hostname itself is inactive or
   unpublished—not merely pointed at the wrong IP. Sign in to No-IP, restore/reconfirm the
   hostname if required, set its A record to the instance's public IP, and then run the updater
   service on the instance. No application deploy can repair an inactive DNS record without the
   No-IP credentials.

   The Docker deployment exposes HTTP on port 80. Do not use `https://meditrust.ddns.net` until
   TLS has been configured using an ALB/CloudFront or a host reverse proxy with a certificate;
   opening security-group port 443 alone does not provide HTTPS.

### Before the credits run out

Stop the instance and release the Elastic IP (an unattached Elastic IP is billed), or take an AMI
snapshot. The repository plus `ec2-bootstrap.sh` recreates the whole environment later; only the
database contents are lost, so run `pg_dump` first if the recorded cases matter.

## 7. Free-tier alternative: Cloudflare Pages + Render + Neon

No AWS account, no credit card anywhere in this path, and every piece auto-deploys on
`git push` — the exact thing the EC2 path above never managed to do reliably.

```
   GitHub                    Cloudflare Pages                     Render
   push to main ──┬────► builds frontend/ (Vite) ────► https://<app>.pages.dev
                  └────► builds backend/Dockerfile ──► https://<app>.onrender.com
                                                              │
                                                              ▼
                                                     Neon (serverless Postgres)
```

Why this combination and not another: Fly.io's free allowance is gone for new
accounts as of late 2024 (pay-as-you-go only now); Render's own free Postgres expires
after 30 days, which loses your data, so Neon (or Supabase) stands in for it instead;
Cloudflare Pages has no credit card, no expiry, and effectively unlimited bandwidth
for a static React build. Render's own free web service sleeps after 15 minutes idle
and takes about a minute to wake on the next request — acceptable for a portfolio
project, not for something that needs to answer instantly at 3am.

### 7.1 Database — Neon (5 minutes)

1. [neon.tech](https://neon.tech) → sign up (no card) → New Project.
2. Copy the connection string it shows you (`postgresql://...`). That is your
   `DATABASE_URL` — psycopg2 needs the `postgresql+psycopg2://` scheme, so change the
   prefix, e.g. `postgresql+psycopg2://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`.
   Keep it somewhere; you paste it into Render next.

### 7.2 Backend — Render (10 minutes)

1. [render.com](https://render.com) → sign up (no card) → **New → Blueprint** → connect
   this GitHub repository. Render reads `render.yaml` at the repo root and proposes a
   `meditrust-backend` Docker web service on the free plan.
   - If blueprint parsing rejects a field (Render's schema changes over time), create
     it manually instead: **New → Web Service → Docker**, Dockerfile path
     `backend/Dockerfile`, Docker build context `.` (repository root).
2. Before the first deploy, set these environment variables on the service (Render
   generates `JWT_SECRET` and `ADMIN_PASSWORD` for you if you used the blueprint):
   | Key | Value |
   | --- | --- |
   | `DATABASE_URL` | the Neon connection string from 7.1, with `postgresql+psycopg2://` |
   | `APP_ENV` | `production` |
   | `ALLOWED_ORIGINS` | leave blank for now — comes back in step 7.4 |
   | `GEMINI_API_KEY` | optional; blank uses the deterministic RAG template |
3. Deploy. Watch the build logs, then open `https://<your-service>.onrender.com/health/ready` —
   it should report the database, model and RAG index all `ok: true`. The admin login
   is `meditrust@gmail.com` with the `ADMIN_PASSWORD` Render generated (Environment tab).

### 7.3 Frontend — Cloudflare Pages (5 minutes)

1. [dash.cloudflare.com](https://dash.cloudflare.com) → **Workers & Pages → Create →
   Pages → Connect to Git** → this repository.
2. Build settings:
   | Setting | Value |
   | --- | --- |
   | Root directory | `frontend` |
   | Build command | `npm run build` |
   | Build output directory | `dist` |
   | Environment variable | `VITE_API_BASE` = `https://<your-service>.onrender.com` (no `/api`, no trailing slash — this setup has no nginx proxy step, so the React app calls Render directly) |
3. Deploy. Cloudflare gives you `https://<project>.pages.dev`.

### 7.4 Wire them together

1. Back in Render, set `ALLOWED_ORIGINS` to the `.pages.dev` URL from 7.3 (comma-separated
   if you add more origins later) and save — this restarts the service.
2. Your site's address is now `https://<project>.pages.dev`. Share that link.

`meditrust.ddns.net` cannot be pointed here: it is a domain No-IP itself owns, and
No-IP does not allow a CNAME record on its own domains, only an A record to a fixed
IP address — which is exactly the problem this whole path avoids, since Cloudflare
Pages has no single IP to give you and needs none. If you want a real custom domain
instead of the `.pages.dev` one, buy one (a few dollars a year from any registrar,
Cloudflare included) and add it under **Custom domains** in the Pages project; that
is the only step in this entire section that costs money, and it is optional.
Retire the No-IP hostname once you stop using the EC2 path — it no longer needs to
follow anything.
3. Confirm: open the Pages URL, log in, run a prediction, and check that the
   evidence-grounded RAG panel and its citations appear below the SHAP explanation.

### 7.5 Living with the free tiers

- **Render sleeps after 15 minutes idle.** The first request after a quiet spell takes
  about a minute. A free uptime monitor (e.g. UptimeRobot, pinging `/health` every 10
  minutes) keeps it warm during hours you expect traffic; do not run it 24/7 against a
  free service, since 750 instance-hours/month covers one always-on service but not
  much slack beyond that.
- **Neon scales to zero after 5 minutes idle**, autoscaling back up on the next query
  in well under a second. This is normal, not a fault.
- **Everything here auto-deploys on push to `main`** — Render and Cloudflare Pages both
  watch the GitHub repo directly. `.github/workflows/deploy.yml` (the SSH-to-EC2
  workflow) is unrelated to this path and can be left alone or disabled.
