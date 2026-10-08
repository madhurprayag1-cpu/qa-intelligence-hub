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



def test_flight_search_is_scoped_to_requested_calendar_day(client):
    response = client.get("/search/flights?origin=ATH&destination=SKG&travel_date=2026-10-15")
    assert response.status_code == 200
    flights = response.json()
    assert flights
    assert all(item["departure_time"].startswith("2026-10-15") for item in flights)


def test_flight_search_has_next_day_and_long_range_future_coverage(client):
    from datetime import date, timedelta

    today = date.today()
    for offset_days in (1, 365, 730, 1095):
        travel_date = today + timedelta(days=offset_days)
        response = client.get(
            f"/search/flights?origin=ATH&destination=SKG&travel_date={travel_date.isoformat()}"
        )
        assert response.status_code == 200
        flights = response.json()
        assert len(flights) >= 2, f"No schedule coverage for {travel_date}"
        assert all(item["departure_time"].startswith(travel_date.isoformat()) for item in flights)


def test_flight_search_has_historical_coverage(client):
    from datetime import date, timedelta

    today = date.today()
    for offset_days in (365, 730):
        travel_date = today - timedelta(days=offset_days)
        response = client.get(
            f"/search/flights?origin=ATH&destination=SKG&travel_date={travel_date.isoformat()}"
        )
        assert response.status_code == 200
        flights = response.json()
        assert len(flights) >= 2, f"No historical schedule coverage for {travel_date}"
        assert all(item["departure_time"].startswith(travel_date.isoformat()) for item in flights)


def test_flight_search_outside_seeded_future_window_is_empty(client):
    from datetime import date, timedelta

    travel_date = date.today() + timedelta(days=1096)
    response = client.get(
        f"/search/flights?origin=ATH&destination=SKG&travel_date={travel_date.isoformat()}"
    )
    assert response.status_code == 200
    assert response.json() == []
