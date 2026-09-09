#!/usr/bin/env bash
# One-shot bootstrap for a fresh (or freshly restarted) Ubuntu EC2 host running MediTrust in Docker.
#
#   curl -fsSL https://raw.githubusercontent.com/RavindraSSK/MediTrust/main/deploy/ec2-bootstrap.sh | bash
#   # or, after cloning:  ./deploy/ec2-bootstrap.sh
#
# What it does (idempotent, safe to re-run):
#   1. installs Docker + compose plugin and git if missing
#   2. clones/updates the repository into $APP_DIR (default /opt/meditrust)
#   3. creates backend/.env with a random JWT_SECRET and ADMIN_PASSWORD if none exists
#   4. installs the DDNS updater (keeps meditrust.ddns.net pointing at this instance) when
#      /etc/meditrust/ddns.env exists
#   5. starts the stack with deploy/deploy.sh (pulls GHCR images, builds locally if unavailable)
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/meditrust}"
REPO_URL="${REPO_URL:-https://github.com/RavindraSSK/MediTrust.git}"
BRANCH="${BRANCH:-main}"
PUBLIC_HOST="${PUBLIC_HOST:-meditrust.ddns.net}"

log() { printf '[bootstrap] %s\n' "$*"; }

if ! command -v docker >/dev/null 2>&1; then
  log "installing Docker"
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER" || true
fi
if ! docker compose version >/dev/null 2>&1; then
  sudo apt-get update -qq && sudo apt-get install -y -qq docker-compose-plugin
fi
command -v git >/dev/null 2>&1 || (sudo apt-get update -qq && sudo apt-get install -y -qq git)

if [[ ! -d "$APP_DIR/.git" ]]; then
  log "cloning $REPO_URL into $APP_DIR"
  sudo mkdir -p "$APP_DIR" && sudo chown "$USER":"$USER" "$APP_DIR"
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"
git fetch --quiet origin "$BRANCH" && git checkout --quiet "$BRANCH" && git reset --quiet --hard "origin/$BRANCH"

ENV_FILE="$APP_DIR/backend/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  log "creating $ENV_FILE (edit it afterwards to add GEMINI_API_KEY, SMTP, RDS, S3 settings)"
  ADMIN_PASSWORD_VALUE="${ADMIN_PASSWORD:-$(openssl rand -base64 12 | tr -d '/+=' | cut -c1-12)A1!}"
  cat > "$ENV_FILE" <<ENV
APP_ENV=production
ADMIN_EMAIL=${ADMIN_EMAIL:-meditrust@gmail.com}
ADMIN_PASSWORD=${ADMIN_PASSWORD_VALUE}
JWT_SECRET=$(openssl rand -base64 48 | tr -d '\n')
ALLOWED_ORIGINS=http://${PUBLIC_HOST},https://${PUBLIC_HOST}
LOG_JSON=true
GEMINI_API_KEY=${GEMINI_API_KEY:-}
ENV
  chmod 600 "$ENV_FILE"
  log "admin login: ${ADMIN_EMAIL:-meditrust@gmail.com} / ${ADMIN_PASSWORD_VALUE}   (stored in $ENV_FILE)"
fi

if [[ -f /etc/meditrust/ddns.env ]]; then
  log "installing DDNS updater (systemd timer)"
  sudo install -m 0755 deploy/ddns-update.sh /usr/local/bin/meditrust-ddns-update
  sudo cp deploy/systemd/meditrust-ddns.service deploy/systemd/meditrust-ddns.timer /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable --now meditrust-ddns.timer
  sudo systemctl start meditrust-ddns.service || true
else
  log "no /etc/meditrust/ddns.env found; skipping DDNS updater (see deploy/README.md)"
fi

log "starting the stack"
DEPLOY_MODE=docker APP_DIR="$APP_DIR" IMAGE_TAG="${IMAGE_TAG:-latest}" ./deploy/deploy.sh

PUBLIC_IP="$(curl -fsS -m 5 https://api.ipify.org || true)"
log "done. Local check: curl http://127.0.0.1/api/health/ready"
log "Public IP of this instance: ${PUBLIC_IP:-unknown}. Make sure ${PUBLIC_HOST} resolves to it (dig +short ${PUBLIC_HOST})."
