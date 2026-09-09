#!/usr/bin/env bash
# One-shot bootstrap for the EC2 host that runs MediTrust in Docker.
#
# Run it ON THE INSTANCE (SSH or SSM Session Manager), not in AWS CloudShell:
#   BRANCH=main ./deploy/ec2-bootstrap.sh
#   curl -fsSL https://raw.githubusercontent.com/RavindraSSK/MediTrust/main/deploy/ec2-bootstrap.sh | bash
#
# Idempotent and safe to re-run. It:
#   1. installs Docker + the compose plugin (Amazon Linux dnf/yum or Debian/Ubuntu apt) and git
#   2. enables the Docker service so the stack survives an instance restart
#   3. clones or updates the repository into $APP_DIR (default /opt/meditrust)
#   4. creates backend/.env with a random JWT_SECRET and ADMIN_PASSWORD if none exists
#   5. installs the DDNS updater when /etc/meditrust/ddns.env exists
#   6. starts the stack via deploy/deploy.sh (GHCR images, or a local build as fallback)
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/meditrust}"
REPO_URL="${REPO_URL:-https://github.com/RavindraSSK/MediTrust.git}"
BRANCH="${BRANCH:-main}"
PUBLIC_HOST="${PUBLIC_HOST:-meditrust.ddns.net}"

log() { printf '[bootstrap] %s\n' "$*"; }
die() { printf '[bootstrap] ERROR: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- environment guards
# CloudShell is a browser terminal in the AWS console, unrelated to the EC2 host: its
# filesystem is ephemeral and it has no Docker daemon. Deploying there does nothing.
if [[ "${AWS_EXECUTION_ENV:-}" == "CloudShell" || -d /home/cloudshell-user ]]; then
  cat >&2 <<'MSG'
[bootstrap] ERROR: this looks like AWS CloudShell, not the EC2 instance.

CloudShell cannot host the application (ephemeral disk, no Docker daemon). Connect to the
instance first, then run this script there:

  # find the instance and check it is running
  ./deploy/aws-status.sh

  # connect without an SSH key (needs SSM Agent + an instance role with AmazonSSMManagedInstanceCore)
  aws ssm start-session --target <instance-id>

  # or with your key pair
  ssh -i ~/your-key.pem ec2-user@<public-ip>     # Amazon Linux
  ssh -i ~/your-key.pem ubuntu@<public-ip>       # Ubuntu

Set BOOTSTRAP_ALLOW_CLOUDSHELL=1 to override (not recommended).
MSG
  [[ "${BOOTSTRAP_ALLOW_CLOUDSHELL:-}" == "1" ]] || exit 2
fi

[[ $(id -u) -eq 0 ]] || sudo -n true 2>/dev/null || sudo true || die "this script needs sudo"

# ---------------------------------------------------------------- package manager
if command -v dnf >/dev/null 2>&1; then PKG=dnf
elif command -v yum >/dev/null 2>&1; then PKG=yum
elif command -v apt-get >/dev/null 2>&1; then PKG=apt
else PKG=none; fi
log "package manager: $PKG"

pkg_install() {
  case "$PKG" in
    dnf) sudo dnf install -y -q "$@" ;;
    yum) sudo yum install -y -q "$@" ;;
    apt) sudo apt-get update -qq && sudo apt-get install -y -qq "$@" ;;
    *) return 1 ;;
  esac
}

command -v git >/dev/null 2>&1 || pkg_install git || die "install git manually and re-run"

# ---------------------------------------------------------------- docker engine
if ! command -v docker >/dev/null 2>&1; then
  log "installing Docker"
  case "$PKG" in
    dnf|yum) pkg_install docker || die "could not install Docker with $PKG" ;;
    apt) curl -fsSL https://get.docker.com | sudo sh ;;
    *) die "install Docker manually and re-run" ;;
  esac
fi

sudo systemctl enable --now docker 2>/dev/null || sudo service docker start || true
sudo usermod -aG docker "$USER" 2>/dev/null || true

# The docker group membership only applies to new logins, so pick the command that works now.
if docker info >/dev/null 2>&1; then DOCKER_BIN="docker"
elif sudo docker info >/dev/null 2>&1; then DOCKER_BIN="sudo docker"
else die "the Docker daemon is not reachable (try: sudo systemctl status docker)"; fi
log "docker command: $DOCKER_BIN"

# ---------------------------------------------------------------- compose plugin
COMPOSE_VERSION="${COMPOSE_VERSION:-v2.32.4}"
if ! $DOCKER_BIN compose version >/dev/null 2>&1; then
  log "installing the docker compose plugin"
  pkg_install docker-compose-plugin >/dev/null 2>&1 || true
  if ! $DOCKER_BIN compose version >/dev/null 2>&1; then
    ARCH="$(uname -m)"
    case "$ARCH" in
      x86_64|amd64) ARCH=x86_64 ;;
      aarch64|arm64) ARCH=aarch64 ;;
      *) die "unsupported architecture $ARCH; install docker compose manually" ;;
    esac
    PLUGIN_DIR=/usr/local/lib/docker/cli-plugins
    sudo mkdir -p "$PLUGIN_DIR"
    sudo curl -fsSL -o "$PLUGIN_DIR/docker-compose" \
      "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-${ARCH}"
    sudo chmod +x "$PLUGIN_DIR/docker-compose"
  fi
fi
$DOCKER_BIN compose version >/dev/null 2>&1 || die "docker compose is still unavailable"

# ---------------------------------------------------------------- repository
if [[ ! -d "$APP_DIR/.git" ]]; then
  log "cloning $REPO_URL ($BRANCH) into $APP_DIR"
  sudo mkdir -p "$APP_DIR" && sudo chown "$USER":"$(id -gn)" "$APP_DIR"
  git clone --quiet --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"
git fetch --quiet origin "$BRANCH"
git checkout --quiet "$BRANCH" 2>/dev/null || git checkout --quiet -b "$BRANCH" "origin/$BRANCH"
git reset --quiet --hard "origin/$BRANCH"
log "checked out $BRANCH at $(git rev-parse --short HEAD)"

# The backend cannot start without this module; it was missing on main before PR #79.
if [[ ! -f backend/app/password_utils.py ]]; then
  die "backend/app/password_utils.py is missing on branch '$BRANCH'. Merge PR #79 first, or re-run with
       BRANCH=claude/clinical-risk-platform-completion-ohnfgm"
fi

# ---------------------------------------------------------------- environment file
ENV_FILE="$APP_DIR/backend/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  log "creating $ENV_FILE (add GEMINI_API_KEY, SMTP, RDS and S3 settings afterwards)"
  # Suffix guarantees the generated password satisfies the API policy (upper, lower, digit,
  # special), which a purely random base64 slice does not.
  ADMIN_PASSWORD_VALUE="${ADMIN_PASSWORD:-$(openssl rand -base64 12 | tr -d '/+=' | cut -c1-10)aA1!}"
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
else
  log "keeping the existing $ENV_FILE"
fi

# ---------------------------------------------------------------- optional DDNS updater
if [[ -f /etc/meditrust/ddns.env ]]; then
  log "installing the DDNS updater (systemd timer)"
  sudo install -m 0755 deploy/ddns-update.sh /usr/local/bin/meditrust-ddns-update
  sudo cp deploy/systemd/meditrust-ddns.service deploy/systemd/meditrust-ddns.timer /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable --now meditrust-ddns.timer
  sudo systemctl start meditrust-ddns.service || true
else
  log "no /etc/meditrust/ddns.env; skipping the DDNS updater (see deploy/README.md section 6)"
fi

# ---------------------------------------------------------------- start the stack
log "starting the stack"
DOCKER_BIN="$DOCKER_BIN" DEPLOY_MODE=docker APP_DIR="$APP_DIR" IMAGE_TAG="${IMAGE_TAG:-latest}" \
  BRANCH="$BRANCH" ./deploy/deploy.sh

PUBLIC_IP="$(curl -fsS -m 5 https://api.ipify.org 2>/dev/null || true)"
DNS_IP="$(getent hosts "$PUBLIC_HOST" 2>/dev/null | awk '{print $1}' | head -n1 || true)"
log "local check:  curl http://127.0.0.1/api/health/ready"
log "instance public IP: ${PUBLIC_IP:-unknown}"
log "${PUBLIC_HOST} currently resolves to: ${DNS_IP:-unresolved}"
if [[ -n "$PUBLIC_IP" && -n "$DNS_IP" && "$PUBLIC_IP" != "$DNS_IP" ]]; then
  log "WARNING: DNS points elsewhere. Update the No-IP record to ${PUBLIC_IP} (see deploy/README.md section 6)."
fi
