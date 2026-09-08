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


def test_ingest_mixed_batch_returns_summary(client):
    signup = client.post("/signup", json={"email": "ingestapi@example.com", "password": "supersecret"})
    headers = {"X-API-Key": signup.json()["api_key"]["api_key"]}
    version_id, amount_id, country_id = _setup_model_version_with_features(client, headers)

    resp = client.post(
        f"/versions/{version_id}/observations",
        json={
            "observations": [
                {"feature_id": amount_id, "raw_value": "10.5"},
                {"feature_id": amount_id, "raw_value": "not-a-number"},
                {"feature_id": amount_id, "raw_value": None},
                {"feature_id": country_id, "raw_value": "US"},
            ]
        },
        headers=headers,
    )
    assert resp.status_code == 201
    summary = resp.json()["summary"]
    assert summary["total"] == 4
    assert summary["valid"] == 2
    assert summary["invalid"] == 1
    assert summary["missing"] == 1


def test_ingest_unknown_feature_returns_422(client):
    signup = client.post("/signup", json={"email": "ingestbad@example.com", "password": "supersecret"})
    headers = {"X-API-Key": signup.json()["api_key"]["api_key"]}
    version_id, amount_id, country_id = _setup_model_version_with_features(client, headers)

    resp = client.post(
        f"/versions/{version_id}/observations",
        json={"observations": [{"feature_id": "00000000-0000-0000-0000-000000000000", "raw_value": "1"}]},
        headers=headers,
    )
    assert resp.status_code == 422


def test_cannot_ingest_into_another_users_version(client):
    signup_a = client.post("/signup", json={"email": "ingestA@example.com", "password": "supersecret"})
    headers_a = {"X-API-Key": signup_a.json()["api_key"]["api_key"]}
    version_id, amount_id, _ = _setup_model_version_with_features(client, headers_a)

    signup_b = client.post("/signup", json={"email": "ingestB@example.com", "password": "supersecret"})
    headers_b = {"X-API-Key": signup_b.json()["api_key"]["api_key"]}

    resp = client.post(
        f"/versions/{version_id}/observations",
        json={"observations": [{"feature_id": amount_id, "raw_value": "1"}]},
        headers=headers_b,
    )
    assert resp.status_code == 404


def test_unseen_category_flagged_via_api(client):
    signup = client.post("/signup", json={"email": "ingestunseen@example.com", "password": "supersecret"})
    headers = {"X-API-Key": signup.json()["api_key"]["api_key"]}
    version_id, amount_id, country_id = _setup_model_version_with_features(client, headers)

    client.post(
        f"/versions/{version_id}/reference-snapshots",
        json={
            "label": "baseline",
            "feature_uploads": [{"feature_id": country_id, "categorical_values": ["US", "UK"]}],
        },
        headers=headers,
    )

    resp = client.post(
        f"/versions/{version_id}/observations",
        json={"observations": [{"feature_id": country_id, "raw_value": "FR"}]},
        headers=headers,
    )
    assert resp.json()["summary"]["unseen_category"] == 1
