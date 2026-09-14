#!/usr/bin/env bash
# Read-only discovery for the MediTrust EC2 host. Changes nothing. Run this ON THE
# INSTANCE (via `aws ssm start-session --target <instance-id>`, not CloudShell) so we
# can pick a safe upgrade path before touching a live site.
set -uo pipefail

section() { printf '\n===== %s =====\n' "$1"; }

section "What is listening on 80 / 443 / 8000"
sudo ss -tlnp 2>/dev/null | grep -E ':80 |:443 |:8000 |LISTEN' || echo "(ss not available or nothing found)"

section "systemd services that look related"
systemctl list-units --type=service --all --no-pager 2>/dev/null | grep -iE 'meditrust|gunicorn|uvicorn|nginx|docker' || echo "(none found)"

section "Is Docker installed, and what is it running"
if command -v docker >/dev/null 2>&1; then
  echo "docker: $(docker --version 2>/dev/null || sudo docker --version 2>/dev/null)"
  sudo docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}' 2>/dev/null || echo "(cannot query docker ps)"
else
  echo "docker: not installed"
fi

section "Common app directories"
for d in /opt/meditrust /var/www/meditrust /home/*/meditrust /srv/meditrust; do
  for p in $d; do
    [[ -e "$p" ]] && { echo "$p:"; ls -la "$p" 2>/dev/null | head -15; [[ -d "$p/.git" ]] && (cd "$p" && echo "  git remote: $(git remote get-url origin 2>/dev/null)  branch: $(git branch --show-current 2>/dev/null)  HEAD: $(git rev-parse --short HEAD 2>/dev/null)"); }
  done
done

section "nginx config (server_name, root, proxy_pass, cert paths)"
if command -v nginx >/dev/null 2>&1; then
  sudo nginx -T 2>/dev/null | grep -E 'server_name|root |proxy_pass|ssl_certificate '
else
  echo "nginx binary not found on the host (it may run inside a container instead)"
fi

section "Node / npm availability (needed to build the new React frontend natively)"
command -v node >/dev/null 2>&1 && echo "node: $(node --version)" || echo "node: not installed"
command -v npm  >/dev/null 2>&1 && echo "npm:  $(npm --version)"  || echo "npm: not installed"

section "Python venv / gunicorn (native backend, if any)"
for v in /opt/meditrust/.venv /opt/meditrust/backend/.venv; do
  [[ -x "$v/bin/python" ]] && echo "venv at $v: $($v/bin/python --version 2>&1)"
done

echo
echo "Paste everything above back to Claude — it decides the exact next commands."
