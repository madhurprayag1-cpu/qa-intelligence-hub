from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_airports():
    response = client.get("/airports")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 12

    codes = {airport["code"] for airport in data}

    assert "ATH" in codes
    assert "SKG" in codes
    assert "LHR" in codes
    assert "FRA" in codes
    assert "AUH" in codes
    assert "DXB" in codes
    assert "BOM" in codes
    assert "DEL" in codes


def test_airport_response_schema():
    response = client.get("/airports")

    assert response.status_code == 200

    airport = response.json()[0]

    assert "id" in airport
    assert "code" in airport
    assert "name" in airport
    assert "city" in airport
    assert "country" in airport
    assert "timezone" in airport
    assert "active" in airport


def test_airports_are_sorted_by_code():
    response = client.get("/airports")

    assert response.status_code == 200

    codes = [airport["code"] for airport in response.json()]

    assert codes == sorted(codes)