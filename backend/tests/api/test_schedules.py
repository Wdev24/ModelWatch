def test_create_and_list_schedule(client):
    signup = client.post("/signup", json={"email": "schedapi@example.com", "password": "supersecret"})
    headers = {"X-API-Key": signup.json()["api_key"]["api_key"]}
    model_id = client.post("/models", json={"name": "m"}, headers=headers).json()["id"]
    version_id = client.post(
        f"/models/{model_id}/versions", json={"version_label": "v1"}, headers=headers
    ).json()["id"]

    resp = client.post(f"/versions/{version_id}/schedules", json={"interval": "daily"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["interval"] == "daily"
    assert resp.json()["is_active"] is True

    listed = client.get(f"/versions/{version_id}/schedules", headers=headers)
    assert len(listed.json()) == 1


def test_deactivate_schedule(client):
    signup = client.post("/signup", json={"email": "schedapi2@example.com", "password": "supersecret"})
    headers = {"X-API-Key": signup.json()["api_key"]["api_key"]}
    model_id = client.post("/models", json={"name": "m"}, headers=headers).json()["id"]
    version_id = client.post(
        f"/models/{model_id}/versions", json={"version_label": "v1"}, headers=headers
    ).json()["id"]
    schedule_id = client.post(
        f"/versions/{version_id}/schedules", json={"interval": "hourly"}, headers=headers
    ).json()["id"]

    resp = client.delete(f"/schedules/{schedule_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_cannot_create_schedule_for_another_users_version(client):
    signup_a = client.post("/signup", json={"email": "schedA@example.com", "password": "supersecret"})
    headers_a = {"X-API-Key": signup_a.json()["api_key"]["api_key"]}
    model_id = client.post("/models", json={"name": "m"}, headers=headers_a).json()["id"]
    version_id = client.post(
        f"/models/{model_id}/versions", json={"version_label": "v1"}, headers=headers_a
    ).json()["id"]

    signup_b = client.post("/signup", json={"email": "schedB@example.com", "password": "supersecret"})
    headers_b = {"X-API-Key": signup_b.json()["api_key"]["api_key"]}

    resp = client.post(f"/versions/{version_id}/schedules", json={"interval": "daily"}, headers=headers_b)
    assert resp.status_code == 404
