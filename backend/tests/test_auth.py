from conftest import auth_header, login


def test_admin_is_seeded_and_gets_a_jwt(client):
    data = login(client, "admin@example.com", "TestAdmin@2026")
    assert data["ok"] and data["role"] == "Admin"
    assert data["access_token"] and data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@example.com"


def test_wrong_password_is_rejected(client):
    data = login(client, "admin@example.com", "nope-nope")
    assert data["ok"] is False and "access_token" not in data or data.get("access_token") is None


def test_me_requires_bearer_token(client, admin_token):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer not-a-token"}).status_code == 401
    me = client.get("/auth/me", headers=auth_header(admin_token)).json()
    assert me["email"] == "admin@example.com" and me["role"] == "Admin"


def test_new_signups_are_pending_until_admin_approves(client, admin_token):
    response = client.post(
        "/auth/register",
        json={
            "first_name": "Pending",
            "last_name": "Person",
            "email": "pending@example.com",
            "password": "Pending@2026",
            "role": "Nurse",
        },
    )
    assert response.json()["ok"] is True
    assert "approve" in response.json()["message"].lower()

    data = login(client, "pending@example.com", "Pending@2026")
    assert data["ok"] is False and "pending" in data["message"].lower()

    # Duplicate email is refused
    dup = client.post(
        "/auth/register",
        json={"first_name": "P", "last_name": "P", "email": "pending@example.com", "password": "Pending@2026"},
    ).json()
    assert dup["ok"] is False

    users = client.get("/admin/users", headers=auth_header(admin_token)).json()
    uid = next(u["id"] for u in users if u["email"] == "pending@example.com")
    rejected = client.patch(
        f"/admin/users/{uid}/role-status", json={"role_status": "rejected"}, headers=auth_header(admin_token)
    )
    assert rejected.status_code == 200
    assert "rejected" in login(client, "pending@example.com", "Pending@2026")["message"].lower()


def test_weak_password_is_rejected_at_registration(client):
    response = client.post(
        "/auth/register",
        json={"first_name": "A", "last_name": "B", "email": "weak@example.com", "password": "short", "role": "Doctor"},
    ).json()
    assert response["ok"] is False and "8" in response["message"]


def test_rbac_blocks_non_admins_from_admin_routes(client, doctor_token, nurse_token):
    assert client.get("/admin/users", headers=auth_header(doctor_token)).status_code == 403
    assert client.get("/admin/users", headers=auth_header(nurse_token)).status_code == 403
    assert client.get("/admin/users").status_code == 401


def test_universal_admin_cannot_be_demoted_or_deleted(client, admin_token):
    users = client.get("/admin/users", headers=auth_header(admin_token)).json()
    admin_id = next(u["id"] for u in users if u["email"] == "admin@example.com")
    assert client.delete(f"/admin/users/{admin_id}", headers=auth_header(admin_token)).status_code == 400
    assert (
        client.patch(
            f"/admin/users/{admin_id}/role", json={"role": "Nurse"}, headers=auth_header(admin_token)
        ).status_code
        == 400
    )


def test_change_password_uses_token_identity(client, doctor_token):
    wrong = client.post(
        "/auth/change-password",
        json={"current_password": "wrong", "new_password": "Doctor@2027"},
        headers=auth_header(doctor_token),
    ).json()
    assert wrong["ok"] is False

    other = client.post(
        "/auth/change-password",
        json={"email": "admin@example.com", "current_password": "Doctor@2026", "new_password": "Doctor@2027"},
        headers=auth_header(doctor_token),
    ).json()
    assert other["ok"] is False and "signed-in" in other["message"]

    ok = client.post(
        "/auth/change-password",
        json={"current_password": "Doctor@2026", "new_password": "Doctor@2027"},
        headers=auth_header(doctor_token),
    ).json()
    assert ok["ok"] is True
    assert login(client, "doctor@example.com", "Doctor@2027")["ok"] is True
    # restore for the other tests
    client.post(
        "/auth/change-password",
        json={"current_password": "Doctor@2027", "new_password": "Doctor@2026"},
        headers=auth_header(doctor_token),
    )


def test_login_rate_limit_returns_429_after_repeated_failures(client):
    client.post(
        "/auth/register",
        json={"first_name": "R", "last_name": "L", "email": "ratelimit@example.com", "password": "Limit@2026"},
    )
    statuses = []
    for _ in range(7):
        response = client.post("/auth/login", json={"email": "ratelimit@example.com", "password": "bad-password"})
        statuses.append(response.status_code)
    assert statuses[:5] == [200] * 5
    assert statuses[5] == 429
    assert "Retry-After" in response.headers


def test_password_reset_flow_with_logged_code(client, monkeypatch):
    from app import otp_service

    client.post(
        "/auth/register",
        json={"first_name": "Re", "last_name": "Set", "email": "reset@example.com", "password": "Reset@2026"},
    )
    captured = {}
    original = otp_service.otp_store.generate_code

    def capture(email, ttl_minutes=10):
        code = original(email, ttl_minutes)
        captured["code"] = code
        return code

    monkeypatch.setattr(otp_service.otp_store, "generate_code", capture)
    assert client.post("/auth/request-reset", json={"email": "reset@example.com"}).json()["ok"] is True
    assert (
        client.post("/auth/verify-reset-code", json={"email": "reset@example.com", "code": "000000"}).json()["ok"]
        is False
    )
    assert client.post("/auth/verify-reset-code", json={"email": "reset@example.com", "code": captured["code"]}).json()[
        "ok"
    ]
    assert client.post(
        "/auth/reset-password", json={"email": "reset@example.com", "new_password": "Reset@2027"}
    ).json()["ok"]
