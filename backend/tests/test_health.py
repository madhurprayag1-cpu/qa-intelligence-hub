from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "qa-intelligence-hub-api"
    assert response.json()["version"] == "0.1.0"
    assert "environment" in response.json()