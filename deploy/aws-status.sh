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
command -v aws >/dev/null 2>&1 || { echo "aws CLI not found"; exit 1; }

echo "== DNS =="
DNS_IP="$(getent hosts "$PUBLIC_HOST" 2>/dev/null | awk '{print $1}' | head -n1 || true)"
echo "${PUBLIC_HOST} -> ${DNS_IP:-<unresolved>}"

echo
echo "== EC2 instances in $(aws configure get region 2>/dev/null || echo "${AWS_REGION:-${AWS_DEFAULT_REGION:-unknown}}") =="
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].{Name:Tags[?Key==`Name`]|[0].Value,Id:InstanceId,State:State.Name,Type:InstanceType,PublicIP:PublicIpAddress,PrivateIP:PrivateIpAddress,Launched:LaunchTime}' \
  --output table

INSTANCE_ID="${INSTANCE_ID:-$(aws ec2 describe-instances \
  --filters 'Name=instance-state-name,Values=running,stopped,stopping,pending' \
  --query 'Reservations[0].Instances[0].InstanceId' --output text 2>/dev/null || true)}"

if [[ -z "$INSTANCE_ID" || "$INSTANCE_ID" == "None" ]]; then
  echo
  echo "No instance found. If the region is wrong, set it first:  export AWS_REGION=us-east-1"
  exit 0
fi

STATE="$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].State.Name' --output text)"
PUBLIC_IP="$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)"

echo
echo "== Inbound rules for $INSTANCE_ID =="
for SG in $(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].SecurityGroups[].GroupId' --output text); do
  echo "security group $SG:"
  aws ec2 describe-security-groups --group-ids "$SG" \
    --query 'SecurityGroups[0].IpPermissions[].{Proto:IpProtocol,From:FromPort,To:ToPort,Cidr:IpRanges[0].CidrIp}' \
    --output table
done

echo "== Elastic IPs =="
aws ec2 describe-addresses \
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
