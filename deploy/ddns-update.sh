#!/usr/bin/env bash
# Keep a No-IP (ddns.net) hostname pointing at this EC2 instance's current public IP.
#
# Config file /etc/meditrust/ddns.env (chmod 600):
#   NOIP_HOSTNAME=meditrust.ddns.net
#   NOIP_USERNAME=<no-ip account email or DDNS key id>
#   NOIP_PASSWORD=<no-ip password or DDNS key>
#
# Run manually:  sudo meditrust-ddns-update
# Installed by deploy/ec2-bootstrap.sh as a systemd timer (on boot + every 15 minutes).
set -euo pipefail

CONFIG="${DDNS_CONFIG:-/etc/meditrust/ddns.env}"
if [[ -f "$CONFIG" ]]; then
  # shellcheck disable=SC1090
  source "$CONFIG"
fi
: "${NOIP_HOSTNAME:?NOIP_HOSTNAME is required}"
: "${NOIP_USERNAME:?NOIP_USERNAME is required}"
: "${NOIP_PASSWORD:?NOIP_PASSWORD is required}"

public_ip() {
  # EC2 instance metadata (IMDSv2) first, public echo service as fallback.
  local token ip
  token="$(curl -sS -m 3 -X PUT "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 60" 2>/dev/null || true)"
  if [[ -n "$token" ]]; then
    ip="$(curl -sS -m 3 -H "X-aws-ec2-metadata-token: $token" \
      http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)"
  fi
  if [[ -z "${ip:-}" ]]; then
    ip="$(curl -sS -m 5 https://api.ipify.org 2>/dev/null || true)"
  fi
  printf '%s' "$ip"
}

IP="$(public_ip)"
if [[ -z "$IP" ]]; then
  echo "ddns-update: could not determine the public IP" >&2
  exit 1
fi

CURRENT="$(getent hosts "$NOIP_HOSTNAME" | awk '{print $1}' | head -n1 || true)"
if [[ "$CURRENT" == "$IP" ]]; then
  echo "ddns-update: $NOIP_HOSTNAME already resolves to $IP"
  exit 0
fi

RESPONSE="$(curl -sS -m 15 -u "${NOIP_USERNAME}:${NOIP_PASSWORD}" \
  -A "MediTrust-DDNS/1.0 ${NOIP_USERNAME}" \
  "https://dynupdate.no-ip.com/nic/update?hostname=${NOIP_HOSTNAME}&myip=${IP}")"
echo "ddns-update: $NOIP_HOSTNAME -> $IP : $RESPONSE"
case "$RESPONSE" in
  good*|nochg*) exit 0 ;;
  *) exit 1 ;;
esac
