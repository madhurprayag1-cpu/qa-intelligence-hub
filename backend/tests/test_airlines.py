from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_airlines():
    response = client.get("/airlines")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 5

    codes = {airline["code"] for airline in data}

    assert "A3" in codes
    assert "LH" in codes
    assert "AM" in codes
    assert "EY" in codes
    assert "BA" in codes


def test_airline_response_schema():
    response = client.get("/airlines")

    assert response.status_code == 200

    airline = response.json()[0]

    assert "id" in airline
    assert "code" in airline
    assert "name" in airline
    assert "country" in airline
    assert "active" in airline