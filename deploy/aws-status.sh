#!/usr/bin/env bash
# Read-only status report for the MediTrust AWS deployment.
#
# Run it wherever the AWS CLI is configured (AWS CloudShell is ideal). It only calls
# describe/list APIs: it never starts, stops or changes anything.
#
#   ./deploy/aws-status.sh
#   PUBLIC_HOST=meditrust.ddns.net ./deploy/aws-status.sh
set -euo pipefail

PUBLIC_HOST="${PUBLIC_HOST:-meditrust.ddns.net}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"

# AWS CLI v2 pipes output through a pager (less) by default. On exit the pager restores the
# terminal screen, which erases everything this script printed. Disable it globally and per call.
export AWS_PAGER=""

command -v aws >/dev/null 2>&1 || { echo "aws CLI not found"; exit 1; }

AWS_REGION_IN_USE="$(aws configure get region 2>/dev/null || true)"
AWS_REGION_IN_USE="${AWS_REGION_IN_USE:-${AWS_REGION:-${AWS_DEFAULT_REGION:-}}}"
if [[ -z "$AWS_REGION_IN_USE" ]]; then
  echo "No AWS region configured. Set one and re-run:  export AWS_REGION=us-east-1"
  exit 1
fi

if ! aws sts get-caller-identity --no-cli-pager >/dev/null 2>&1; then
  echo "The AWS CLI has no working credentials in this shell."
  exit 1
fi

echo "== DNS =="
DNS_IP="$(getent hosts "$PUBLIC_HOST" 2>/dev/null | awk '{print $1}' | head -n1 || true)"
echo "${PUBLIC_HOST} -> ${DNS_IP:-<unresolved>}"
if [[ -z "$DNS_IP" ]]; then
  cat <<EOF
  DNS is not publishing an address for ${PUBLIC_HOST}. Browsers cannot reach the
  instance until the hostname is restored/reconfirmed in No-IP and updated to the
  instance's public (preferably Elastic) IP.
EOF
fi

echo
echo "== EC2 instances in ${AWS_REGION_IN_USE} =="
INSTANCE_TABLE="$(aws --no-cli-pager ec2 describe-instances \
  --query 'Reservations[].Instances[].{Name:Tags[?Key==`Name`]|[0].Value,Id:InstanceId,State:State.Name,Type:InstanceType,PublicIP:PublicIpAddress,PrivateIP:PrivateIpAddress,Launched:LaunchTime}' \
  --output table 2>/dev/null || true)"
if [[ -n "$INSTANCE_TABLE" ]]; then
  printf '%s\n' "$INSTANCE_TABLE"
else
  echo "(no EC2 instances in this region)"
fi

INSTANCE_ID="${INSTANCE_ID:-$(aws --no-cli-pager ec2 describe-instances \
  --filters 'Name=instance-state-name,Values=running,stopped,stopping,pending' \
  --query 'Reservations[0].Instances[0].InstanceId' --output text 2>/dev/null || true)}"

if [[ -z "$INSTANCE_ID" || "$INSTANCE_ID" == "None" ]]; then
  echo
  echo "No instance found. If the region is wrong, set it first:  export AWS_REGION=us-east-1"
  exit 0
fi

STATE="$(aws --no-cli-pager ec2 describe-instances --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].State.Name' --output text)"
PUBLIC_IP="$(aws --no-cli-pager ec2 describe-instances --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)"

echo
echo "== Inbound rules for $INSTANCE_ID =="
for SG in $(aws --no-cli-pager ec2 describe-instances --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].SecurityGroups[].GroupId' --output text); do
  echo "security group $SG:"
  aws --no-cli-pager ec2 describe-security-groups --group-ids "$SG" \
    --query 'SecurityGroups[0].IpPermissions[].{Proto:IpProtocol,From:FromPort,To:ToPort,Cidr:IpRanges[0].CidrIp}' \
    --output table
done

echo "== Elastic IPs =="
aws --no-cli-pager ec2 describe-addresses \
  --query 'Addresses[].{IP:PublicIp,AllocationId:AllocationId,AttachedTo:InstanceId}' --output table
AVAILABLE_EIP_ALLOCATION="$(aws --no-cli-pager ec2 describe-addresses \
  --query 'Addresses[?AssociationId==null].AllocationId | [0]' --output text 2>/dev/null || true)"
AVAILABLE_EIP="$(aws --no-cli-pager ec2 describe-addresses \
  --query 'Addresses[?AssociationId==null].PublicIp | [0]' --output text 2>/dev/null || true)"
[[ "$AVAILABLE_EIP_ALLOCATION" == "None" ]] && AVAILABLE_EIP_ALLOCATION=""
[[ "$AVAILABLE_EIP" == "None" ]] && AVAILABLE_EIP=""

if [[ "$PUBLIC_IP" != "None" && -n "$PUBLIC_IP" ]]; then
  echo
  echo "== Is the application answering on ${PUBLIC_IP}? =="
  APP_UP=0
  SITE_RESPONDING=0
  probe() {  # never let a curl failure abort the script; %{http_code} is 000 when it fails
    curl -s -o /dev/null -m 8 -w '%{http_code}' "$@" 2>/dev/null || true
  }
  for URL in "http://${PUBLIC_IP}/api/health/ready" "http://${PUBLIC_IP}:8000/health/ready" "http://${PUBLIC_IP}/"; do
    CODE="$(probe "$URL")"
    case "$CODE" in
      000) echo "  $URL -> no response (nothing listening on that port, or blocked)" ;;
      200) echo "  $URL -> $CODE OK"; APP_UP=1; SITE_RESPONDING=1 ;;
      30*) echo "  $URL -> $CODE redirect (usually nginx sending HTTP to HTTPS)"; SITE_RESPONDING=1 ;;
      *)   echo "  $URL -> $CODE"; SITE_RESPONDING=1 ;;
    esac
  done

  # Decisive test: pretend DNS already points at this IP, and use the real hostname so TLS
  # and the certificate are exercised exactly as a browser would. -k tolerates a self-signed
  # or expired certificate so we still learn whether the application itself answers.
  echo "  --- as ${PUBLIC_HOST} would see it (DNS forced to ${PUBLIC_IP}) ---"
  for SCHEME in http https; do
    PORT=80; [[ "$SCHEME" == "https" ]] && PORT=443
    CODE="$(probe -k -L --resolve "${PUBLIC_HOST}:${PORT}:${PUBLIC_IP}" "${SCHEME}://${PUBLIC_HOST}/api/health/ready")"
    if [[ "$CODE" == "200" ]]; then
      echo "  ${SCHEME}://${PUBLIC_HOST}/api/health/ready -> 200 OK   <-- the site works once DNS is updated"
      APP_UP=1; SITE_RESPONDING=1
    else
      echo "  ${SCHEME}://${PUBLIC_HOST}/api/health/ready -> ${CODE:-000}"
      [[ "$CODE" != "000" ]] && SITE_RESPONDING=1
    fi
  done
fi

echo
echo "== Assessment =="
[[ "$STATE" == "running" ]] \
  && echo "  instance $INSTANCE_ID is running at ${PUBLIC_IP}" \
  || echo "  instance $INSTANCE_ID is '$STATE' -> start it:  aws ec2 start-instances --instance-ids $INSTANCE_ID"

if [[ -z "$DNS_IP" && "$PUBLIC_IP" != "None" && -n "$PUBLIC_IP" ]]; then
  echo "  DNS FAILURE: ${PUBLIC_HOST} does not currently resolve."
  echo "  Restore/reconfirm the hostname in No-IP, then set its A record to ${PUBLIC_IP}."
  echo "  To keep it synchronized, configure /etc/meditrust/ddns.env and re-run:"
  echo "    sudo systemctl enable --now meditrust-ddns.timer"
  echo "    sudo systemctl start meditrust-ddns.service"
  echo "    sudo journalctl -u meditrust-ddns.service -n 20 --no-pager"
elif [[ "$PUBLIC_IP" != "None" && "$DNS_IP" != "$PUBLIC_IP" ]]; then
  echo "  DNS MISMATCH: ${PUBLIC_HOST} points at ${DNS_IP} but the instance is at ${PUBLIC_IP}."
  if [[ -n "$AVAILABLE_EIP_ALLOCATION" && -n "$AVAILABLE_EIP" ]]; then
    echo "  An unattached Elastic IP already exists; use it instead of allocating another one:"
    echo "    aws ec2 associate-address --instance-id $INSTANCE_ID --allocation-id $AVAILABLE_EIP_ALLOCATION"
    echo "  After association completes, set the No-IP A record for ${PUBLIC_HOST} to ${AVAILABLE_EIP}."
  else
    echo "  Allocate and associate an Elastic IP so the address stops changing:"
    echo "    ALLOCATION_ID=\$(aws ec2 allocate-address --domain vpc --query AllocationId --output text)"
    echo "    aws ec2 associate-address --instance-id $INSTANCE_ID --allocation-id \"\$ALLOCATION_ID\""
    echo "  Then set the No-IP A record to the Elastic IP printed by aws ec2 describe-addresses."
  fi
fi

if [[ "${APP_UP:-0}" == "1" ]]; then
  echo "  The readiness endpoint is healthy on the instance IP."
elif [[ "${SITE_RESPONDING:-0}" == "1" ]]; then
  echo "  A web server responds, but /api/health/ready is not returning 200; inspect its proxy/TLS configuration."
else
  echo "  Nothing is answering on the instance, so the stack also needs to be (re)started."
fi

echo
echo "  Connect to the instance:"
echo "    aws ssm start-session --target $INSTANCE_ID     # no SSH key needed (requires SSM agent + role)"
echo "  Then deploy on the instance:"
echo "    curl -fsSL https://raw.githubusercontent.com/RavindraSSK/MediTrust/${DEPLOY_BRANCH}/deploy/ec2-bootstrap.sh \\"
echo "      | BRANCH=${DEPLOY_BRANCH} bash"
