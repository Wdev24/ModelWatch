def _setup_with_reference_and_obs(client, headers, n_ref=40, n_obs=35):
    model_id = client.post("/models", json={"name": "m"}, headers=headers).json()["id"]
    version_id = client.post(
        f"/models/{model_id}/versions", json={"version_label": "v1"}, headers=headers
    ).json()["id"]
    feature_id = client.post(
        f"/versions/{version_id}/features",
        json={"name": "amount", "data_type": "numeric"},
        headers=headers,
    ).json()["id"]

    ref_values = [float(i) for i in range(n_ref)]
    client.post(
        f"/versions/{version_id}/reference-snapshots",
        json={"label": "baseline", "feature_uploads": [{"feature_id": feature_id, "numeric_values": ref_values}]},
        headers=headers,
    )

    obs = [{"feature_id": feature_id, "raw_value": str(float(i))} for i in range(n_obs)]
    client.post(f"/versions/{version_id}/observations", json={"observations": obs}, headers=headers)

    return version_id, feature_id


def test_trigger_drift_run_and_get_detail(client):
    signup = client.post("/signup", json={"email": "driftapi@example.com", "password": "supersecret"})
    headers = {"X-API-Key": signup.json()["api_key"]["api_key"]}
    version_id, feature_id = _setup_with_reference_and_obs(client, headers)

    resp = client.post(f"/versions/{version_id}/drift-runs", json={}, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "completed"
    assert body["overall_status"] in ("ok", "moderate", "drifted")
    assert len(body["feature_results"]) == 1
    assert body["feature_results"][0]["rows_received"] == 35

    detail = client.get(f"/drift-runs/{body['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == body["id"]


def test_drift_run_without_reference_snapshot_returns_422(client):
    signup = client.post("/signup", json={"email": "driftnoRef@example.com", "password": "supersecret"})
    headers = {"X-API-Key": signup.json()["api_key"]["api_key"]}
    model_id = client.post("/models", json={"name": "m"}, headers=headers).json()["id"]
    version_id = client.post(
        f"/models/{model_id}/versions", json={"version_label": "v1"}, headers=headers
    ).json()["id"]

    resp = client.post(f"/versions/{version_id}/drift-runs", json={}, headers=headers)
    assert resp.status_code == 422


def test_list_drift_run_history(client):
    signup = client.post("/signup", json={"email": "drifthistory@example.com", "password": "supersecret"})
    headers = {"X-API-Key": signup.json()["api_key"]["api_key"]}
    version_id, feature_id = _setup_with_reference_and_obs(client, headers)

    client.post(f"/versions/{version_id}/drift-runs", json={}, headers=headers)
    client.post(f"/versions/{version_id}/drift-runs", json={}, headers=headers)

    resp = client.get(f"/versions/{version_id}/drift-runs", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_cannot_view_another_users_drift_run(client):
    signup_a = client.post("/signup", json={"email": "driftA@example.com", "password": "supersecret"})
    headers_a = {"X-API-Key": signup_a.json()["api_key"]["api_key"]}
    version_id, _ = _setup_with_reference_and_obs(client, headers_a)
    run = client.post(f"/versions/{version_id}/drift-runs", json={}, headers=headers_a).json()

    signup_b = client.post("/signup", json={"email": "driftB@example.com", "password": "supersecret"})
    headers_b = {"X-API-Key": signup_b.json()["api_key"]["api_key"]}

    resp = client.get(f"/drift-runs/{run['id']}", headers=headers_b)
    assert resp.status_code == 404


def test_second_drift_run_only_covers_new_observations(client):
    signup = client.post("/signup", json={"email": "driftwin@example.com", "password": "supersecret"})
    headers = {"X-API-Key": signup.json()["api_key"]["api_key"]}
    version_id, feature_id = _setup_with_reference_and_obs(client, headers, n_obs=20)

    first = client.post(f"/versions/{version_id}/drift-runs", json={}, headers=headers).json()
    assert first["feature_results"][0]["rows_received"] == 20

    # No new observations ingested -> second run should be empty.
    second = client.post(f"/versions/{version_id}/drift-runs", json={}, headers=headers).json()
    assert second["status"] == "empty"
    assert second["feature_results"] == []
