def test_create_monitoring_job_returns_202_pending(client):
    signup = client.post("/signup", json={"email": "jobapi@example.com", "password": "supersecret"})
    headers = {"X-API-Key": signup.json()["api_key"]["api_key"]}
    model_id = client.post("/models", json={"name": "m"}, headers=headers).json()["id"]
    version_id = client.post(
        f"/models/{model_id}/versions", json={"version_label": "v1"}, headers=headers
    ).json()["id"]

    resp = client.post(f"/versions/{version_id}/monitoring-jobs", headers=headers)
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "pending"
    assert body["model_version_id"] == version_id


def test_get_monitoring_job_status(client):
    signup = client.post("/signup", json={"email": "jobapi2@example.com", "password": "supersecret"})
    headers = {"X-API-Key": signup.json()["api_key"]["api_key"]}
    model_id = client.post("/models", json={"name": "m"}, headers=headers).json()["id"]
    version_id = client.post(
        f"/models/{model_id}/versions", json={"version_label": "v1"}, headers=headers
    ).json()["id"]
    job_id = client.post(f"/versions/{version_id}/monitoring-jobs", headers=headers).json()["id"]

    resp = client.get(f"/monitoring-jobs/{job_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id


def test_cannot_view_another_users_monitoring_job(client):
    signup_a = client.post("/signup", json={"email": "jobA@example.com", "password": "supersecret"})
    headers_a = {"X-API-Key": signup_a.json()["api_key"]["api_key"]}
    model_id = client.post("/models", json={"name": "m"}, headers=headers_a).json()["id"]
    version_id = client.post(
        f"/models/{model_id}/versions", json={"version_label": "v1"}, headers=headers_a
    ).json()["id"]
    job_id = client.post(f"/versions/{version_id}/monitoring-jobs", headers=headers_a).json()["id"]

    signup_b = client.post("/signup", json={"email": "jobB@example.com", "password": "supersecret"})
    headers_b = {"X-API-Key": signup_b.json()["api_key"]["api_key"]}

    resp = client.get(f"/monitoring-jobs/{job_id}", headers=headers_b)
    assert resp.status_code == 404
