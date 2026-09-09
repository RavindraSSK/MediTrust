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

echo
echo "== Assessment =="
[[ "$STATE" == "running" ]] \
  && echo "  instance $INSTANCE_ID is running at ${PUBLIC_IP}" \
  || echo "  instance $INSTANCE_ID is '$STATE' -> start it:  aws ec2 start-instances --instance-ids $INSTANCE_ID"

if [[ -n "$DNS_IP" && "$PUBLIC_IP" != "None" && "$DNS_IP" != "$PUBLIC_IP" ]]; then
  echo "  DNS MISMATCH: ${PUBLIC_HOST} points at ${DNS_IP} but the instance is at ${PUBLIC_IP}."
  echo "  Update the No-IP record, and allocate an Elastic IP so the address stops changing:"
  echo "    aws ec2 allocate-address --domain vpc"
  echo "    aws ec2 associate-address --instance-id $INSTANCE_ID --allocation-id <eipalloc-...>"
fi

echo
echo "  Connect and deploy:"
echo "    aws ssm start-session --target $INSTANCE_ID     # no SSH key needed (requires SSM agent + role)"
echo "    curl -fsSL https://raw.githubusercontent.com/RavindraSSK/MediTrust/main/deploy/ec2-bootstrap.sh | bash"
