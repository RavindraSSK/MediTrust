#!/usr/bin/env bash
# One-shot deployment script executed on the EC2 host by GitHub Actions (or by hand).
#
#   DEPLOY_MODE=docker  (default when docker is installed)
#       Pulls the images published to GHCR by the deploy workflow and restarts the
#       stack with docker compose (db + backend + frontend).
#   DEPLOY_MODE=native
#       git pull, install Python deps into /opt/meditrust/.venv, build the React app
#       into /var/www/meditrust, restart the gunicorn systemd service and reload nginx.
#
# Usage: APP_DIR=/opt/meditrust IMAGE_TAG=main ./deploy/deploy.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/meditrust}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_REPO="${IMAGE_REPO:-ghcr.io/ravindrassk/meditrust}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/health/ready}"
BRANCH="${BRANCH:-main}"

if [[ -z "${DEPLOY_MODE:-}" ]]; then
  if command -v docker >/dev/null 2>&1; then DEPLOY_MODE=docker; else DEPLOY_MODE=native; fi
fi

log() { printf '[deploy] %s\n' "$*"; }

wait_for_health() {
  local url="$1" attempts="${2:-30}"
  for i in $(seq 1 "$attempts"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "healthy: $url"
      return 0
    fi
    sleep 4
  done
  log "ERROR: $url did not become healthy"
  return 1
}

cd "$APP_DIR"
log "mode=$DEPLOY_MODE app_dir=$APP_DIR tag=$IMAGE_TAG"

if [[ "$DEPLOY_MODE" == "docker" ]]; then
  export IMAGE_REPO IMAGE_TAG
  git fetch --quiet origin "$BRANCH" && git checkout --quiet "$BRANCH" && git reset --quiet --hard "origin/$BRANCH"
  docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml pull backend frontend
  docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d --remove-orphans
  wait_for_health "$HEALTH_URL"
  docker image prune -f >/dev/null 2>&1 || true
else
  git fetch --quiet origin "$BRANCH" && git checkout --quiet "$BRANCH" && git reset --quiet --hard "origin/$BRANCH"
  if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
    python3 -m venv "$APP_DIR/.venv"
  fi
  "$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip
  "$APP_DIR/.venv/bin/pip" install --quiet -r backend/requirements.txt

  if command -v npm >/dev/null 2>&1; then
    (cd frontend && npm ci --silent && VITE_API_BASE=/api npm run build --silent)
    sudo mkdir -p /var/www/meditrust
    sudo rsync -a --delete frontend/dist/ /var/www/meditrust/
  else
    log "WARNING: npm not found; frontend build skipped"
  fi

  sudo systemctl restart meditrust-backend
  sudo nginx -t && sudo systemctl reload nginx
  wait_for_health "$HEALTH_URL"
fi

log "deployment complete"
