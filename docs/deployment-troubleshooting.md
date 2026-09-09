# EC2 deployment troubleshooting

Use this checklist when `https://meditrust.ddns.net/` stops responding after an
AWS networking or instance change. Commands that inspect services must run
**inside the EC2 instance**, not in AWS CloudShell. A CloudShell prompt commonly
looks like `~ $`; `systemctl` there reports that systemd is not PID 1 because
CloudShell is a container.

## 1. Locate and connect to the instance from CloudShell

List running instances and their current addresses:

```bash
aws ec2 describe-instances \
  --filters Name=instance-state-name,Values=running \
  --query 'Reservations[].Instances[].{Name:Tags[?Key==`Name`]|[0].Value,ID:InstanceId,PublicIP:PublicIpAddress,PrivateIP:PrivateIpAddress,SecurityGroups:SecurityGroups[].GroupId}' \
  --output table
```

If the table is empty, select the deployment's AWS Region in CloudShell. Values
written in angle brackets in this guide are placeholders; do not enter text
such as `YOUR_REGION` literally. To discover the active region and reuse it in
commands, run:

```bash
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-$(aws configure get region)}}"
printf 'Using AWS Region: %s\n' "$REGION"
```

Then connect using **EC2 console → Instances → select the instance → Connect**.
Alternatively, if the private key is available locally, use the login name for
the instance image:

```bash
ssh -i /path/to/key.pem ubuntu@<PublicIP>  # Ubuntu
ssh -i /path/to/key.pem ec2-user@<PublicIP>  # Amazon Linux
```

Only continue to the service checks after the shell prompt is on that instance.

CloudShell can also confirm the instance status and display the effective
security-group rules before connecting. Substitute the IDs printed by the first
command:

```bash
aws ec2 describe-instance-status \
  --instance-ids <InstanceID> \
  --include-all-instances \
  --output table

aws ec2 describe-security-groups \
  --group-ids <SecurityGroupID> \
  --query 'SecurityGroups[].IpPermissions' \
  --output json
```

## 2. Verify DNS and the EC2 public address

```bash
getent ahostsv4 meditrust.ddns.net
```

`getent` is normally preinstalled even when `dig` is unavailable. As another
portable fallback, run:

```bash
python3 -c 'import socket; print(socket.gethostbyname("meditrust.ddns.net"))'
```

Compare the resolved address with `PublicIP` from the AWS CLI command above or
with the public/Elastic IP displayed in the EC2 console. If the instance was
stopped and does not use an Elastic IP, AWS may have assigned a new public IP.
Update the No-IP DDNS record to that address, or associate an Elastic IP to
prevent recurrence.

## 3. Verify AWS networking

Confirm that the instance is running and that its security group permits these
inbound rules:

| Type | Protocol | Port | Source |
| --- | --- | --- | --- |
| HTTP | TCP | 80 | `0.0.0.0/0` |
| HTTPS | TCP | 443 | `0.0.0.0/0` |
| SSH | TCP | 22 | Your administrator IP only |

The subnet route table must also have a `0.0.0.0/0` route to an Internet
Gateway. If a custom network ACL is in use, it must permit the web ports and
return traffic on ephemeral ports.

## 4. Verify the application and reverse proxy

The production backend listens on port 8000, while Nginx should expose ports 80
and 443:

```bash
sudo systemctl status meditrust --no-pager
sudo journalctl -u meditrust -n 100 --no-pager
curl --fail http://127.0.0.1:8000/health

sudo nginx -t
sudo systemctl status nginx --no-pager
sudo journalctl -u nginx -n 100 --no-pager
sudo ss -lntp | grep -E ':(80|443|8000)\b'
```

If `systemctl` again says systemd is not PID 1, the shell is still in CloudShell
or another container rather than on the EC2 host. Return to section 1 and
connect to the instance.

Interpret the results as follows:

- If the local port 8000 health check fails, repair or restart the `meditrust`
  service before investigating DNS or TLS.
- If port 8000 works but Nginx is not listening on 80/443, correct the Nginx
  configuration and restart Nginx.
- If all three ports listen locally but the public request times out, revisit
  the security group, route table, network ACL, and DNS address.

After correcting the failing layer, restart the services and test both paths:

```bash
sudo systemctl restart meditrust nginx
curl --fail https://meditrust.ddns.net/
curl --fail https://meditrust.ddns.net/api/health
```

## 5. Verify TLS

If HTTP works but HTTPS fails, inspect the certificate and renewal status:

```bash
sudo certbot certificates
echo | openssl s_client \
  -connect meditrust.ddns.net:443 \
  -servername meditrust.ddns.net 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates
```

Do not request a replacement certificate until DNS resolves to the current EC2
address and ports 80/443 are publicly reachable.
