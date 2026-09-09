# MediTrust – Explainable AI Healthcare Risk Prediction Platform

## Sprint 1 (Completed)
- Developed website prototype (Login + Signup + Assessment UI)
- Configured FastAPI backend
- Integrated PostgreSQL using Docker
- Implemented database models
- Established GitHub project management workflow

## Sprint 2 (completed)
- Integrate Machine Learning model for cardiovascular risk prediction
- Develop /predict API endpoint
- Store predictions in database
- Connect frontend with backend prediction API

## Sprint 3 – Explainability & Enhancement (completed)
- Integrate SHAP for model explainability
- Add feature importance visualization
- Improve UI/UX (modern healthcare dashboard)
- Enhance authentication 
## Sprint 4 – Finalization & Clinical Workflow
- Enhanced prediction output with clear clinical interpretation
- Integrated Gemini for AI-based summaries
- Completed nurse and doctor dashboard workflows
- Implemented case status flow and performed final testing
- Deployed (AWS-EC2)
- Website: https://meditrust.ddns.net/

### EC2 deployment health check

After changing an instance, Elastic IP, security group, or DNS setting, verify the
deployment from the EC2 host in this order:

```bash
# The DDNS record must resolve to the instance's current public/Elastic IP.
dig +short meditrust.ddns.net A

# The application process and reverse proxy must both be running.
sudo systemctl status meditrust --no-pager
sudo systemctl status nginx --no-pager
curl --fail http://127.0.0.1:8000/health
sudo nginx -t

# AWS security-group inbound rules must allow TCP 80 and 443.
# After correcting configuration, restart both services.
sudo systemctl restart meditrust nginx
curl --fail https://meditrust.ddns.net/api/health
```

If the first command returns no address or an old address, update the DDNS
record before changing the application. If the local health check fails, inspect
`sudo journalctl -u meditrust -n 100 --no-pager`; if only the public check fails,
check the EC2 security group, network ACL, Nginx configuration, and TLS
certificate.


Team:
- Ravi 
- Uday 
