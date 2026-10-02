def test_flight_search_contract(client):
    response = client.get("/search/flights?origin=ATH&destination=SKG")
    assert response.status_code == 200
    flights = response.json()
    assert isinstance(flights, list)
    assert len(flights) >= 1

    first_flight = flights[0]
    expected_keys = {
        "flight_id",
        "flight_number",
        "airline",
        "origin",
        "destination",
        "departure_time",
        "arrival_time",
        "duration_minutes",
        "available_seats",
        "base_price",
    }
    assert expected_keys.issubset(set(first_flight.keys()))
    assert first_flight["origin"] == "ATH"
    assert first_flight["destination"] == "SKG"


def test_flight_search_no_results(client):
    response = client.get("/search/flights?origin=BOM&destination=SKG")
    assert response.status_code == 200
    assert response.json() == []


def test_flight_search_validation_errors(client):
    # Missing required query params
    resp_missing = client.get("/search/flights")
    assert resp_missing.status_code == 422

    # Invalid airport code length
    resp_invalid = client.get("/search/flights?origin=AT&destination=SKG")
    assert resp_invalid.status_code == 422


def test_list_all_flights(client):
    response = client.get("/flights")
    assert response.status_code == 200
    flights = response.json()
    assert isinstance(flights, list)
    assert len(flights) >= 12

