def test_alerts_generated_and_listed_via_api(client):
    signup = client.post("/signup", json={"email": "alertapi@example.com", "password": "supersecret"})
    headers = {"X-API-Key": signup.json()["api_key"]["api_key"]}
    model_id = client.post("/models", json={"name": "m"}, headers=headers).json()["id"]
    version_id = client.post(
        f"/models/{model_id}/versions", json={"version_label": "v1"}, headers=headers
    ).json()["id"]
    feature_id = client.post(
        f"/versions/{version_id}/features",
        json={"name": "amount", "data_type": "numeric"},
        headers=headers,
    ).json()["id"]

    ref_values = [float(i) for i in range(50)]
    client.post(
        f"/versions/{version_id}/reference-snapshots",
        json={"label": "baseline", "feature_uploads": [{"feature_id": feature_id, "numeric_values": ref_values}]},
        headers=headers,
    )

    obs = [{"feature_id": feature_id, "raw_value": str(1000.0 + i)} for i in range(40)]
    client.post(f"/versions/{version_id}/observations", json={"observations": obs}, headers=headers)

    run_resp = client.post(f"/versions/{version_id}/drift-runs", json={}, headers=headers)
    assert run_resp.json()["overall_status"] == "drifted"

    alerts_resp = client.get(f"/versions/{version_id}/alerts", headers=headers)
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "high"

    detail_resp = client.get(f"/alerts/{alerts[0]['id']}", headers=headers)
    assert detail_resp.status_code == 200


def test_cannot_view_another_users_alerts(client):
    signup_a = client.post("/signup", json={"email": "alertA@example.com", "password": "supersecret"})
    headers_a = {"X-API-Key": signup_a.json()["api_key"]["api_key"]}
    model_id = client.post("/models", json={"name": "m"}, headers=headers_a).json()["id"]
    version_id = client.post(
        f"/models/{model_id}/versions", json={"version_label": "v1"}, headers=headers_a
    ).json()["id"]

    signup_b = client.post("/signup", json={"email": "alertB@example.com", "password": "supersecret"})
    headers_b = {"X-API-Key": signup_b.json()["api_key"]["api_key"]}

    resp = client.get(f"/versions/{version_id}/alerts", headers=headers_b)
    assert resp.status_code == 404
