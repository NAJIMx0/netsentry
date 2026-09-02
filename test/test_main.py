from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_system():
    response = client.get("/system")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)


def test_network():
    response = client.get("/network")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)


def test_alerts():
    response = client.get("/alerts")
    assert response.status_code == 200
    assert "alerts" in response.json()