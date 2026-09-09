from conftest import DEMO_PATIENT, HEALTHY_PATIENT, auth_header


def test_predict_requires_authentication(client):
    assert client.post("/predict", json=DEMO_PATIENT).status_code == 401


def test_predict_returns_disease_probability_in_the_right_direction(client, doctor_token):
    high = client.post("/predict", json=DEMO_PATIENT, headers=auth_header(doctor_token))
    low = client.post("/predict", json=HEALTHY_PATIENT, headers=auth_header(doctor_token))
    assert high.status_code == 200, high.text
    assert low.status_code == 200, low.text
    high, low = high.json(), low.json()

    # The old model was label-inverted; this guards against a regression.
    assert high["risk_probability"] > 0.6
    assert low["risk_probability"] < 0.2
    assert high["risk_level"] == "High" and low["risk_level"] == "Low"
    assert high["case_id"] and high["model_version"]
    assert high["thresholds"]["rule_out"] < high["thresholds"]["rule_in"]

    # SHAP output is additive in probability space and labelled
    assert len(high["all_features"]) == 13
    assert abs(high["base_value"] + sum(f["impact"] for f in high["all_features"]) - high["risk_probability"]) < 0.05
    assert all(f["label"] for f in high["top_features"])
    increasing = {f["feature"] for f in high["top_features"] if f["direction"] == "increases risk"}
    assert {"ca", "thal", "cp"} & increasing


def test_predict_rejects_codes_outside_the_clinical_encoding(client, doctor_token):
    bad = dict(DEMO_PATIENT, cp=0, thal=2, trestbps=999)
    response = client.post("/predict", json=bad, headers=auth_header(doctor_token))
    assert response.status_code == 422, response.text
    errors = " ".join(response.json()["errors"])
    assert "cp" in errors and "thal" in errors and "trestbps" in errors


def test_predict_response_includes_grounded_clinical_context(client, nurse_token):
    data = client.post("/predict", json=DEMO_PATIENT, headers=auth_header(nurse_token)).json()
    ctx = data["clinical_context"]
    assert ctx["mode"] == "template"  # no Gemini key in tests -> deterministic fallback
    assert ctx["model_output"]["risk_probability"] == data["risk_probability"]
    assert ctx["model_output"]["risk_level"] == data["risk_level"]
    assert len(ctx["citations"]) >= 4
    assert all(c["url"] and c["source"] for c in ctx["citations"])
    cited_ids = {c["id"] for c in ctx["citations"]}
    for item in ctx["evidence"]:
        assert set(item["citation_ids"]) <= cited_ids
        assert item["feature"] in {f["feature"] for f in data["top_features"]}
    assert "[S1]" in ctx["narrative"]
    assert "does not modify" in ctx["narrative"]
    assert "not a diagnosis" in ctx["disclaimer"]


def test_workflow_escalation_and_doctor_decision(client, nurse_token, doctor_token, admin_token):
    case_id = client.post("/predict", json=DEMO_PATIENT, headers=auth_header(nurse_token)).json()["case_id"]

    queue = client.get("/cases/triage-queue", headers=auth_header(nurse_token)).json()
    assert any(item["id"] == case_id and item["priority"] == "Urgent" for item in queue)

    # Doctors cannot escalate; nurses can, and only once.
    assert client.post(f"/cases/{case_id}/escalate", headers=auth_header(doctor_token)).status_code == 403
    first = client.post(f"/cases/{case_id}/escalate", headers=auth_header(nurse_token)).json()
    assert first["ok"] is True and first["case"]["escalation_id"]
    again = client.post(f"/cases/{case_id}/escalate", headers=auth_header(nurse_token)).json()
    assert again["ok"] is False

    # Nurses cannot record decisions; doctors can.
    escalation_id = first["case"]["escalation_id"]
    body = {"decision": "Immediate physician review", "note": "Troponin pathway started"}
    assert (
        client.post(
            f"/doctor/escalations/{escalation_id}/decision", json=body, headers=auth_header(nurse_token)
        ).status_code
        == 403
    )
    bad = client.post(
        f"/doctor/escalations/{escalation_id}/decision",
        json={"decision": "Discharge"},
        headers=auth_header(doctor_token),
    )
    assert bad.status_code == 400
    decided = client.post(
        f"/doctor/escalations/{escalation_id}/decision", json=body, headers=auth_header(doctor_token)
    ).json()
    assert decided["case"]["status"] == "Reviewed" and decided["case"]["doctor_decision"] == body["decision"]

    escalations = client.get("/doctor/escalations", headers=auth_header(doctor_token)).json()
    assert any(e["escalation_id"] == escalation_id and e["doctor_id"] for e in escalations)

    audit = client.get("/admin/audit-log", headers=auth_header(admin_token)).json()
    assert any(e["type"] == "Escalation" for e in audit)


def test_low_risk_case_cannot_be_escalated(client, nurse_token):
    case_id = client.post("/predict", json=HEALTHY_PATIENT, headers=auth_header(nurse_token)).json()["case_id"]
    response = client.post(f"/cases/{case_id}/escalate", headers=auth_header(nurse_token))
    assert response.status_code == 400


def test_case_explainability_reuses_stored_context(client, doctor_token):
    created = client.post("/predict", json=DEMO_PATIENT, headers=auth_header(doctor_token)).json()
    data = client.get(f"/cases/{created['case_id']}/explainability", headers=auth_header(doctor_token)).json()
    assert data["risk_level"] == created["risk_level"]
    assert data["legacy_model"] is False
    assert data["clinical_context"]["generated_at"] == created["clinical_context"]["generated_at"]
    assert data["risk_increasing_factors"]
    assert client.get("/cases/999999/explainability", headers=auth_header(doctor_token)).status_code == 404


def test_patient_records_and_dashboard(client, doctor_token):
    client.post(
        "/predict", json=dict(DEMO_PATIENT, first_name="Zara", last_name="Quinn"), headers=auth_header(doctor_token)
    )
    recent = client.get("/patients/recent?limit=5", headers=auth_header(doctor_token)).json()
    assert any(p["full_name"] == "Zara Quinn" for p in recent)
    found = client.get("/patients/search?q=zara", headers=auth_header(doctor_token)).json()
    assert found and found[0]["first_name"] == "Zara"
    records = client.get("/patients/records?first_name=Zara&last_name=Quinn", headers=auth_header(doctor_token)).json()
    assert records and records[0]["model_version"]

    summary = client.get("/dashboard/summary", headers=auth_header(doctor_token)).json()
    assert summary["total_predictions"] >= 1 and summary["urgent_cases"] >= 1
    assert summary["model_version"]
