def _setup_model_version_with_features(client, headers):
    model_id = client.post("/models", json={"name": "m"}, headers=headers).json()["id"]
    version_id = client.post(
        f"/models/{model_id}/versions", json={"version_label": "v1"}, headers=headers
    ).json()["id"]
    amount_id = client.post(
        f"/versions/{version_id}/features",
        json={"name": "amount", "data_type": "numeric"},
        headers=headers,
    ).json()["id"]
    country_id = client.post(
        f"/versions/{version_id}/features",
        json={"name": "country", "data_type": "categorical"},
        headers=headers,
    ).json()["id"]
    return version_id, amount_id, country_id


def test_create_reference_snapshot(client):
    signup = client.post("/signup", json={"email": "snapapi@example.com", "password": "supersecret"})
    headers = {"X-API-Key": signup.json()["api_key"]["api_key"]}
    version_id, amount_id, country_id = _setup_model_version_with_features(client, headers)

    resp = client.post(
        f"/versions/{version_id}/reference-snapshots",
        json={
            "label": "baseline-1",
            "feature_uploads": [
                {"feature_id": amount_id, "numeric_values": [1.0, 2.0, 3.0]},
                {"feature_id": country_id, "categorical_values": ["US", "UK", "US"]},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["stats"]) == 2


def test_mismatched_data_type_rejected(client):
    signup = client.post("/signup", json={"email": "snapbad@example.com", "password": "supersecret"})
    headers = {"X-API-Key": signup.json()["api_key"]["api_key"]}
    version_id, amount_id, country_id = _setup_model_version_with_features(client, headers)

    resp = client.post(
        f"/versions/{version_id}/reference-snapshots",
        json={
            "label": "bad-upload",
            "feature_uploads": [{"feature_id": amount_id, "categorical_values": ["US"]}],
        },
        headers=headers,
    )
    assert resp.status_code == 422


def test_copy_forward_across_snapshots_via_api(client):
    signup = client.post("/signup", json={"email": "snapcf@example.com", "password": "supersecret"})
    headers = {"X-API-Key": signup.json()["api_key"]["api_key"]}
    version_id, amount_id, country_id = _setup_model_version_with_features(client, headers)

    client.post(
        f"/versions/{version_id}/reference-snapshots",
        json={
            "label": "snap1",
            "feature_uploads": [
                {"feature_id": amount_id, "numeric_values": [1.0, 2.0]},
                {"feature_id": country_id, "categorical_values": ["US"]},
            ],
        },
        headers=headers,
    )

    snap2 = client.post(
        f"/versions/{version_id}/reference-snapshots",
        json={
            "label": "snap2",
            "feature_uploads": [{"feature_id": amount_id, "numeric_values": [5.0]}],
        },
        headers=headers,
    )
    assert snap2.status_code == 201
    stats = {s["feature_id"]: s for s in snap2.json()["stats"]}
    assert country_id in stats  # copied forward
    assert stats[country_id]["statistics"]["category_counts"] == {"US": 1}


def test_cannot_create_snapshot_for_another_users_version(client):
    signup_a = client.post("/signup", json={"email": "snapA@example.com", "password": "supersecret"})
    headers_a = {"X-API-Key": signup_a.json()["api_key"]["api_key"]}
    version_id, amount_id, _ = _setup_model_version_with_features(client, headers_a)

    signup_b = client.post("/signup", json={"email": "snapB@example.com", "password": "supersecret"})
    headers_b = {"X-API-Key": signup_b.json()["api_key"]["api_key"]}

    resp = client.post(
        f"/versions/{version_id}/reference-snapshots",
        json={"label": "hijack", "feature_uploads": [{"feature_id": amount_id, "numeric_values": [1.0]}]},
        headers=headers_b,
    )
    assert resp.status_code == 404
