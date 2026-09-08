def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_payload_shape(client):
    response = client.get("/health")
    body = response.json()
    assert body["status"] == "ok"
    assert "app" in body
    assert "environment" in body
