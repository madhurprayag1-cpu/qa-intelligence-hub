from fastapi.testclient import TestClient
from tests.conftest import authenticated


def test_get_ancillary_catalog(client: TestClient):
    response = client.get("/bookings/ancillaries/catalog")
    assert response.status_code == 200
    data = response.json()
    assert "baggage" in data
    assert "seats" in data
    assert "meals" in data

    # Verify options present
    baggage_tiers = [b["id"] for b in data["baggage"]]
    assert 0 in baggage_tiers and 1 in baggage_tiers and 2 in baggage_tiers

    seat_ids = [s["id"] for s in data["seats"]]
    assert "STANDARD" in seat_ids and "EXTRA_LEGROOM" in seat_ids

    meal_ids = [m["id"] for m in data["meals"]]
    assert "STANDARD" in meal_ids and "GOURMET" in meal_ids


def test_booking_with_custom_ancillaries_pricing(client: TestClient):
    flights_resp = client.get("/flights")
    assert flights_resp.status_code == 200
    flights = flights_resp.json()
    assert len(flights) > 0

    available_flights = [f for f in flights if f.get("available_seats", 0) > 5]
    flight = available_flights[0] if available_flights else flights[0]

    # Book 2 seats with 1 checked bag ($35), extra legroom ($45), and gourmet meal ($20)
    # Total ancillary per passenger = 35 + 45 + 20 = 100.00
    # For 2 seats = 200.00
    expected_base_fare = round(float(flight["base_price"]) * 2, 2)
    expected_ancillary = 200.00
    expected_total = round(expected_base_fare + expected_ancillary, 2)

    payload = {
        "flight_id": flight["id"],
        "passenger_name": "Dr. Sarah Ancillary",
        "passenger_email": "sarah.ancillary@example.com",
        "seats": 2,
        "payment_method": "CARD",
        "ancillaries": {
            "baggage_tier": 1,
            "seat_preference": "EXTRA_LEGROOM",
            "meal_preference": "GOURMET",
        },
    }

    with authenticated(client):
        create_res = client.post("/bookings", json=payload)
    assert create_res.status_code == 201
    booking = create_res.json()

    assert booking["seats"] == 2
    assert booking["base_fare"] == expected_base_fare
    assert booking["ancillary_amount"] == expected_ancillary
    assert booking["total_amount"] == expected_total

    # Verify itemized breakdown in booking
    breakdown = booking["ancillaries"]
    assert breakdown is not None
    assert breakdown["baggage"]["tier"] == 1
    assert breakdown["seat"]["tier"] == "EXTRA_LEGROOM"
    assert breakdown["meal"]["tier"] == "GOURMET"
    assert breakdown["total_ancillary"] == 200.00


def test_booking_default_ancillaries_is_zero(client: TestClient):
    flights_resp = client.get("/flights")
    available_flights = [f for f in flights_resp.json() if f.get("available_seats", 0) > 3]
    flight = available_flights[0]

    payload = {
        "flight_id": flight["id"],
        "passenger_name": "Standard Passenger",
        "passenger_email": "std.passenger@example.com",
        "seats": 1,
        "payment_method": "CARD",
    }

    with authenticated(client):
        create_res = client.post("/bookings", json=payload)
    assert create_res.status_code == 201
    booking = create_res.json()

    assert booking["ancillary_amount"] == 0.0
    assert booking["total_amount"] == float(flight["base_price"])


def test_invalid_ancillary_selection_rejected(client: TestClient):
    flights_resp = client.get("/flights")
    available_flights = [f for f in flights_resp.json() if f.get("available_seats", 0) > 3]
    flight = available_flights[0]

    # Baggage tier 5 is invalid (only 0, 1, 2 permitted)
    payload = {
        "flight_id": flight["id"],
        "passenger_name": "Invalid Passenger",
        "passenger_email": "invalid@example.com",
        "seats": 1,
        "payment_method": "CARD",
        "ancillaries": {
            "baggage_tier": 5,
            "seat_preference": "STANDARD",
            "meal_preference": "STANDARD",
        },
    }

    with authenticated(client):
        res = client.post("/bookings", json=payload)
    assert res.status_code == 422


def test_cancellation_refunds_full_amount_including_ancillaries(client: TestClient):
    flights_resp = client.get("/flights")
    available_flights = [f for f in flights_resp.json() if f.get("available_seats", 0) > 3]
    flight = available_flights[0]

    payload = {
        "flight_id": flight["id"],
        "passenger_name": "Refundable Passenger",
        "passenger_email": "refundable@example.com",
        "seats": 1,
        "payment_method": "CARD",
        "ancillaries": {
            "baggage_tier": 2,  # $70
            "seat_preference": "EXTRA_LEGROOM",  # $45
            "meal_preference": "GOURMET",  # $20 -> Total ancillaries = 135
        },
    }

    with authenticated(client):
        booking_res = client.post("/bookings", json=payload)
    assert booking_res.status_code == 201
    booking = booking_res.json()
    booking_id = booking["id"]
    total_paid = booking["total_amount"]
    assert booking["ancillary_amount"] == 135.00

    # Pay booking
    with authenticated(client):
        pay_res = client.post(
        "/payments",
        json={
            "booking_id": booking_id,
            "method": "CREDIT_CARD",
        },
    )
    assert pay_res.status_code == 201

    # Cancel booking
    with authenticated(client):
        cancel_res = client.post(f"/bookings/{booking_id}/cancel")
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()

    assert cancel_data["current_status"] == "CANCELLED"
    assert cancel_data["refund_status"] == "REFUNDED"
    assert cancel_data["refund_amount"] == total_paid
