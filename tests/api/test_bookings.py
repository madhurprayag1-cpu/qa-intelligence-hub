from tests.conftest import authenticated

def test_booking_validation_contract(client):
    with authenticated(client):
        response = client.post(
            "/bookings",
            json={
                "flight_id": 999999,
                "passenger_name": "Test Passenger",
                "passenger_email": "qa@example.com",
                "seats": 1,
                "payment_method": "CARD",
            },
        )
    assert response.status_code == 404
    assert response.json()["detail"] == "Flight not found"


def test_create_and_retrieve_booking(client):
    # Find an active flight
    flights_resp = client.get("/flights")
    assert flights_resp.status_code == 200
    flights = flights_resp.json()
    assert len(flights) > 0

    available_flights = [f for f in flights if f.get("available_seats", 0) > 5]
    target_flight = available_flights[0] if available_flights else flights[0]
    flight_id = target_flight["id"]
    seats_to_book = 2

    # Create booking
    booking_payload = {
        "flight_id": flight_id,
        "passenger_name": "Senior SDET",
        "passenger_email": "sdet@qahub.io",
        "seats": seats_to_book,
        "payment_method": "CREDIT_CARD",
    }
    with authenticated(client):
        create_resp = client.post("/bookings", json=booking_payload)
    assert create_resp.status_code == 201

    booking = create_resp.json()
    assert "id" in booking
    assert booking["id"] > 0
    assert booking["reference"].startswith("QAH-")
    assert booking["flight_id"] == flight_id
    assert booking["passenger_name"] == "Senior SDET"
    assert booking["passenger_email"] == "sdet@qahub.io"
    assert booking["seats"] == seats_to_book
    assert booking["total_amount"] == target_flight["base_price"] * seats_to_book
    assert booking["status"] == "CONFIRMED"

    # Retrieve by ID
    with authenticated(client):
        get_by_id_resp = client.get(f"/bookings/{booking['id']}")
    assert get_by_id_resp.status_code == 200
    assert get_by_id_resp.json()["reference"] == booking["reference"]

    # Retrieve by Reference
    with authenticated(client):
        get_by_ref_resp = client.get(f"/bookings/reference/{booking['reference']}")
    assert get_by_ref_resp.status_code == 200
    assert get_by_ref_resp.json()["id"] == booking["id"]


def test_booking_not_found(client):
    with authenticated(client):
        resp_id = client.get("/bookings/999999")
    assert resp_id.status_code == 404

    with authenticated(client):
        resp_ref = client.get("/bookings/reference/QAH-UNKNOWN")
    assert resp_ref.status_code == 404


def test_booking_insufficient_seats(client):
    flights_resp = client.get("/flights")
    assert flights_resp.status_code == 200
    target_flight = flights_resp.json()[0]

    # Attempt to book more seats than available if possible, or validation limit
    # Schema limits seats to max 9. If available seats was less than 9, test that:
    with authenticated(client):
        response = client.post(
            "/bookings",
            json={
                "flight_id": target_flight["id"],
                "passenger_name": "Overbooking Test",
                "passenger_email": "qa@example.com",
                "seats": 10,  # exceeds schema limit (le=9)
                "payment_method": "CARD",
            },
        )
    assert response.status_code == 422

