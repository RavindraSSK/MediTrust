# EC2 deployment troubleshooting

Use this checklist when `https://meditrust.ddns.net/` stops responding after an
AWS networking or instance change. Run the first section from any machine with
normal Internet access, then run the remaining sections over SSH on the EC2
instance.

## 1. Verify DNS and the EC2 public address

```bash
dig +short meditrust.ddns.net A
curl --fail --silent http://169.254.169.254/latest/meta-data/public-ipv4
```

The addresses must match. The metadata command only works from EC2 instances
where IMDSv1 is enabled; otherwise compare the DNS result with the public or
Elastic IP displayed in the EC2 console. If the instance was stopped and does
not use an Elastic IP, AWS may have assigned a new public IP. Update the No-IP
DDNS record to that address, or associate an Elastic IP to prevent recurrence.

## 2. Verify AWS networking

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

## 3. Verify the application and reverse proxy

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

## 4. Verify TLS

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
