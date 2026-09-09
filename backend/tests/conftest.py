"""
Test fixtures.

The application is imported once per session against a throw-away SQLite
database with a fixed admin password and no Gemini key, so the suite is
deterministic and never touches the network.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

_TMP = tempfile.mkdtemp(prefix="meditrust-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["ADMIN_EMAIL"] = "admin@example.com"
os.environ["ADMIN_PASSWORD"] = "TestAdmin@2026"
os.environ["JWT_SECRET"] = "test-secret-not-for-production"
os.environ["JWT_EXPIRE_MINUTES"] = "60"
os.environ["GEMINI_API_KEY"] = ""
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["APP_ENV"] = "test"
os.environ.pop("MODEL_S3_URI", None)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

DEMO_PATIENT = {
    "first_name": "Demo",
    "last_name": "Patient",
    "age": 58,
    "sex": 1,
    "cp": 4,
    "trestbps": 156,
    "chol": 286,
    "fbs": 1,
    "restecg": 1,
    "thalach": 118,
    "exang": 1,
    "oldpeak": 2.8,
    "slope": 2,
    "ca": 2,
    "thal": 7,
}

HEALTHY_PATIENT = {
    "first_name": "Healthy",
    "last_name": "Person",
    "age": 35,
    "sex": 0,
    "cp": 2,
    "trestbps": 118,
    "chol": 180,
    "fbs": 0,
    "restecg": 0,
    "thalach": 185,
    "exang": 0,
    "oldpeak": 0.0,
    "slope": 1,
    "ca": 0,
    "thal": 3,
}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, email: str, password: str) -> dict:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def admin_token(client):
    data = login(client, "admin@example.com", "TestAdmin@2026")
    assert data["ok"], data
    return data["access_token"]


def _create_approved_user(client, admin_token, email, password, role):
    response = client.post(
        "/auth/register",
        json={"first_name": role, "last_name": "User", "email": email, "password": password, "role": role},
    )
    assert response.status_code == 200, response.text
    users = client.get("/admin/users", headers=auth_header(admin_token)).json()
    user_id = next(u["id"] for u in users if u["email"] == email)
    response = client.patch(
        f"/admin/users/{user_id}/role-status", json={"role_status": "approved"}, headers=auth_header(admin_token)
    )
    assert response.status_code == 200, response.text
    return login(client, email, password)["access_token"]


@pytest.fixture(scope="session")
def doctor_token(client, admin_token):
    return _create_approved_user(client, admin_token, "doctor@example.com", "Doctor@2026", "Doctor")


@pytest.fixture(scope="session")
def nurse_token(client, admin_token):
    return _create_approved_user(client, admin_token, "nurse@example.com", "Nurse@2026", "Nurse")
