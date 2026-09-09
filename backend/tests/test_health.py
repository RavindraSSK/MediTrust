def test_root_and_liveness(client):
    assert client.get("/").status_code == 200
    body = client.get("/health").json()
    assert body["status"] == "ok"


def test_readiness_reports_all_subsystems(client):
    response = client.get("/health/ready")
    assert response.status_code == 200, response.text
    checks = response.json()["checks"]
    assert checks["database"]["ok"]
    assert checks["model"]["ok"]
    assert checks["rag"]["ok"] and checks["rag"]["passages"] > 0


def test_metrics_exposed_in_prometheus_format(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "meditrust_model_loaded 1.0" in response.text
    assert "meditrust_http_requests_total" in response.text


def test_request_id_header_is_returned(client):
    response = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert response.headers["X-Request-ID"] == "abc123"


def test_model_info_is_public_and_describes_model_card(client):
    info = client.get("/model/info").json()
    assert info["status"] == "ready"
    assert info["model_name"] in {"LogisticRegression", "RandomForest", "XGBoost"}
    assert 0 < info["active_thresholds"]["rule_out"] < info["active_thresholds"]["rule_in"] < 1
    assert info["cross_validation"]["roc_auc_mean"] > 0.8
    assert len(info["global_feature_importance"]["features"]) == 13
    assert info["label_definition"].startswith("1 = angiographic coronary artery disease")


def test_model_encoding_matches_frontend_codes(client):
    enc = client.get("/model/encoding").json()
    assert enc["category_codes"]["cp"] == [1, 2, 3, 4]
    assert enc["category_codes"]["thal"] == [3, 6, 7]
    assert enc["category_codes"]["slope"] == [1, 2, 3]
