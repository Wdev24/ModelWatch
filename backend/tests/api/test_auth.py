def test_signup_creates_user_and_returns_api_key(client):
    resp = client.post("/signup", json={"email": "new@example.com", "password": "supersecret"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["email"] == "new@example.com"
    assert body["api_key"]["api_key"].startswith("mw_")


def test_signup_duplicate_email_returns_409(client):
    client.post("/signup", json={"email": "dup@example.com", "password": "supersecret"})
    resp = client.post("/signup", json={"email": "dup@example.com", "password": "anotherpass"})
    assert resp.status_code == 409


def test_protected_route_requires_api_key(client):
    resp = client.post("/api-keys")
    assert resp.status_code == 401


def test_protected_route_rejects_invalid_key(client):
    resp = client.post("/api-keys", headers={"X-API-Key": "mw_not_a_real_key"})
    assert resp.status_code == 401


def test_create_and_revoke_api_key(client):
    signup = client.post("/signup", json={"email": "keyowner@example.com", "password": "supersecret"})
    key = signup.json()["api_key"]["api_key"]

    create_resp = client.post("/api-keys", headers={"X-API-Key": key})
    assert create_resp.status_code == 201
    new_key_id = create_resp.json()["id"]

    revoke_resp = client.delete(f"/api-keys/{new_key_id}", headers={"X-API-Key": key})
    assert revoke_resp.status_code == 204


def test_revoked_key_can_no_longer_authenticate(client):
    signup = client.post("/signup", json={"email": "revokeme@example.com", "password": "supersecret"})
    first_key_id = signup.json()["api_key"]["id"]
    first_key = signup.json()["api_key"]["api_key"]

    # issue a second key so we still have a valid credential to revoke the first with
    second = client.post("/api-keys", headers={"X-API-Key": first_key})
    second_key = second.json()["api_key"]

    client.delete(f"/api-keys/{first_key_id}", headers={"X-API-Key": second_key})

    resp = client.post("/api-keys", headers={"X-API-Key": first_key})
    assert resp.status_code == 401


def test_cannot_revoke_another_users_api_key(client):
    signup_a = client.post("/signup", json={"email": "usera@example.com", "password": "supersecret"})
    key_a = signup_a.json()["api_key"]["api_key"]

    signup_b = client.post("/signup", json={"email": "userb@example.com", "password": "supersecret"})
    key_b_id = signup_b.json()["api_key"]["id"]

    # user A tries to revoke user B's key
    resp = client.delete(f"/api-keys/{key_b_id}", headers={"X-API-Key": key_a})
    assert resp.status_code == 404
