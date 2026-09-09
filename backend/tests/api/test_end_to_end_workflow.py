"""
The complete V1 workflow in one test, per spec section 17:
signup -> API key -> model -> version/features -> reference snapshot ->
production ingestion -> drift check -> history/detail -> alerts.
"""


def test_full_v1_workflow_end_to_end(client):
    signup = client.post("/signup", json={"email": "e2e@example.com", "password": "supersecret"})
    assert signup.status_code == 201
    api_key = signup.json()["api_key"]["api_key"]
    headers = {"X-API-Key": api_key}

    extra_key_resp = client.post("/api-keys", headers=headers)
    assert extra_key_resp.status_code == 201

    model_resp = client.post("/models", json={"name": "fraud-detector"}, headers=headers)
    assert model_resp.status_code == 201
    model_id = model_resp.json()["id"]

    version_resp = client.post(
        f"/models/{model_id}/versions", json={"version_label": "v1"}, headers=headers
    )
    assert version_resp.status_code == 201
    version_id = version_resp.json()["id"]

    amount_resp = client.post(
        f"/versions/{version_id}/features",
        json={"name": "transaction_amount", "data_type": "numeric"},
        headers=headers,
    )
    assert amount_resp.status_code == 201
    amount_id = amount_resp.json()["id"]

    country_resp = client.post(
        f"/versions/{version_id}/features",
        json={"name": "country", "data_type": "categorical"},
        headers=headers,
    )
    assert country_resp.status_code == 201
    country_id = country_resp.json()["id"]

    reference_amounts = [float(i % 100) for i in range(300)]
    reference_countries = (["US"] * 150) + (["UK"] * 100) + (["FR"] * 50)
    snapshot_resp = client.post(
        f"/versions/{version_id}/reference-snapshots",
        json={
            "label": "initial-baseline",
            "feature_uploads": [
                {"feature_id": amount_id, "numeric_values": reference_amounts},
                {"feature_id": country_id, "categorical_values": reference_countries},
            ],
        },
        headers=headers,
    )
    assert snapshot_resp.status_code == 201
    assert len(snapshot_resp.json()["stats"]) == 2

    observations = []
    for i in range(60):
        observations.append({"feature_id": amount_id, "raw_value": str(5000.0 + i)})  # shifted -> drift
    observations.append({"feature_id": amount_id, "raw_value": None})  # missing
    observations.append({"feature_id": amount_id, "raw_value": "not-a-number"})  # invalid
    for i in range(60):
        observations.append({"feature_id": country_id, "raw_value": "US"})  # stable -> no drift
    observations.append({"feature_id": country_id, "raw_value": "DE"})  # unseen category

    ingest_resp = client.post(
        f"/versions/{version_id}/observations", json={"observations": observations}, headers=headers
    )
    assert ingest_resp.status_code == 201
    summary = ingest_resp.json()["summary"]
    assert summary["total"] == len(observations)
    assert summary["missing"] == 1
    assert summary["invalid"] == 1
    assert summary["unseen_category"] == 1

    drift_resp = client.post(f"/versions/{version_id}/drift-runs", json={}, headers=headers)
    assert drift_resp.status_code == 201
    drift_run = drift_resp.json()
    assert drift_run["status"] == "completed"
    assert drift_run["overall_status"] == "drifted"

    feature_statuses = {fr["feature_id"]: fr["feature_status"] for fr in drift_run["feature_results"]}
    assert feature_statuses[amount_id] == "drifted"
    assert feature_statuses[country_id] in ("ok", "moderate", "drifted", "insufficient_data")

    history_resp = client.get(f"/versions/{version_id}/drift-runs", headers=headers)
    assert history_resp.status_code == 200
    assert len(history_resp.json()) == 1

    detail_resp = client.get(f"/drift-runs/{drift_run['id']}", headers=headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == drift_run["id"]

    alerts_resp = client.get(f"/versions/{version_id}/alerts", headers=headers)
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    assert len(alerts) >= 1
    assert any(a["feature_id"] == amount_id for a in alerts)

    job_resp = client.post(f"/versions/{version_id}/monitoring-jobs", headers=headers)
    assert job_resp.status_code == 202
    assert job_resp.json()["status"] == "pending"

    schedule_resp = client.post(f"/versions/{version_id}/schedules", json={"interval": "daily"}, headers=headers)
    assert schedule_resp.status_code == 201

    other_signup = client.post("/signup", json={"email": "outsider@example.com", "password": "supersecret"})
    other_headers = {"X-API-Key": other_signup.json()["api_key"]["api_key"]}
    assert client.get(f"/models/{model_id}/versions", headers=other_headers).status_code == 404
    assert client.get(f"/versions/{version_id}/drift-runs", headers=other_headers).status_code == 404
    assert client.get(f"/versions/{version_id}/alerts", headers=other_headers).status_code == 404
