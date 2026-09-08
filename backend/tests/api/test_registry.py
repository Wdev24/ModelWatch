def _signup_and_get_key(client, email):
    resp = client.post("/signup", json={"email": email, "password": "supersecret"})
    return resp.json()["api_key"]["api_key"]


def test_create_and_list_models(client):
    key = _signup_and_get_key(client, "modelowner@example.com")
    headers = {"X-API-Key": key}

    create_resp = client.post("/models", json={"name": "fraud-detector"}, headers=headers)
    assert create_resp.status_code == 201
    assert create_resp.json()["name"] == "fraud-detector"

    list_resp = client.get("/models", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


def test_duplicate_model_name_for_same_user_returns_409(client):
    key = _signup_and_get_key(client, "dupmodel@example.com")
    headers = {"X-API-Key": key}
    client.post("/models", json={"name": "dup"}, headers=headers)
    resp = client.post("/models", json={"name": "dup"}, headers=headers)
    assert resp.status_code == 409


def test_user_cannot_see_another_users_models(client):
    key_a = _signup_and_get_key(client, "isoA@example.com")
    key_b = _signup_and_get_key(client, "isoB@example.com")

    client.post("/models", json={"name": "private-model"}, headers={"X-API-Key": key_a})

    resp = client.get("/models", headers={"X-API-Key": key_b})
    assert resp.status_code == 200
    assert resp.json() == []


def test_full_registry_workflow_model_version_feature(client):
    key = _signup_and_get_key(client, "workflow@example.com")
    headers = {"X-API-Key": key}

    model_id = client.post("/models", json={"name": "wf-model"}, headers=headers).json()["id"]
    version_resp = client.post(
        f"/models/{model_id}/versions", json={"version_label": "v1"}, headers=headers
    )
    assert version_resp.status_code == 201
    version_id = version_resp.json()["id"]

    feature_resp = client.post(
        f"/versions/{version_id}/features",
        json={"name": "transaction_amount", "data_type": "numeric"},
        headers=headers,
    )
    assert feature_resp.status_code == 201
    assert feature_resp.json()["data_type"] == "numeric"

    features = client.get(f"/versions/{version_id}/features", headers=headers)
    assert len(features.json()) == 1


def test_cannot_create_version_on_another_users_model(client):
    key_a = _signup_and_get_key(client, "ownerA@example.com")
    key_b = _signup_and_get_key(client, "ownerB@example.com")

    model_id = client.post("/models", json={"name": "a-model"}, headers={"X-API-Key": key_a}).json()["id"]

    resp = client.post(
        f"/models/{model_id}/versions", json={"version_label": "v1"}, headers={"X-API-Key": key_b}
    )
    assert resp.status_code == 404


def test_invalid_feature_data_type_rejected(client):
    key = _signup_and_get_key(client, "badtype@example.com")
    headers = {"X-API-Key": key}
    model_id = client.post("/models", json={"name": "bt-model"}, headers=headers).json()["id"]
    version_id = client.post(
        f"/models/{model_id}/versions", json={"version_label": "v1"}, headers=headers
    ).json()["id"]

    resp = client.post(
        f"/versions/{version_id}/features",
        json={"name": "x", "data_type": "not_a_real_type"},
        headers=headers,
    )
    assert resp.status_code == 422
