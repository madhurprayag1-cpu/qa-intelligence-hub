import pytest
from tests.conftest import authenticated


def _create_booking(client) -> dict:
    flights = client.get("/flights").json()
    assert len(flights) > 0
    available_flights = [f for f in flights if f.get("available_seats", 0) > 2]
    flight = available_flights[0] if available_flights else flights[0]
    flight_id = flight["id"]

    with authenticated(client):
        resp = client.post(
            "/bookings",
            json={
                "flight_id": flight_id,
                "passenger_name": "Test Passenger",
                "passenger_email": "passenger@example.com",
                "seats": 1,
                "payment_method": "CREDIT_CARD",
            },
        )
    assert resp.status_code == 201
    return resp.json()


def test_payment_cash_success(client):
    booking = _create_booking(client)

    with authenticated(client):
        response = client.post(
            "/payments",
            json={
                "booking_id": booking["id"],
                "method": "CASH",
            },
        )
    assert response.status_code == 201
    payment = response.json()

    assert payment["booking_id"] == booking["id"]
    assert payment["method"] == "CASH"
    assert payment["status"] == "PAID"
    assert payment["three_ds_required"] is False
    assert payment["three_ds_status"] == "NOT_REQUIRED"
    assert payment["authorization_status"] == "AUTHORIZED"
    assert payment["transaction_reference"].startswith("TXN-")
    assert payment["provider_reference"].startswith("PROV-")
    assert float(payment["amount"]) == float(booking["total_amount"])
    assert payment["currency"] == "EUR"

    # Confirm booking status is updated to PAID
    with authenticated(client):
        booking_resp = client.get(f"/bookings/{booking['id']}")
    assert booking_resp.status_code == 200
    assert booking_resp.json()["status"] == "PAID"


@pytest.mark.parametrize(
    "method",
    [
        "CREDIT_CARD",
        "DEBIT_CARD",
        "EASY_PAY",
        "UPI",
        "WALLET",
    ],
)
def test_payment_direct_methods_success(client, method):
    booking = _create_booking(client)

    with authenticated(client):
        response = client.post(
            "/payments",
            json={
                "booking_id": booking["id"],
                "method": method,
            },
        )
    assert response.status_code == 201
    payment = response.json()

    assert payment["booking_id"] == booking["id"]
    assert payment["method"] == method
    assert payment["status"] == "PAID"
    assert payment["authorization_status"] == "AUTHORIZED"
    assert payment["three_ds_required"] is False

    with authenticated(client):
        booking_resp = client.get(f"/bookings/{booking['id']}")
    assert booking_resp.status_code == 200
    assert booking_resp.json()["status"] == "PAID"


def test_payment_3ds_success(client):
    booking = _create_booking(client)

    with authenticated(client):
        response = client.post(
            "/payments",
            json={
                "booking_id": booking["id"],
                "method": "CREDIT_CARD_3DS",
                "three_ds_result": "SUCCESS",
            },
        )
    assert response.status_code == 201
    payment = response.json()

    assert payment["method"] == "CREDIT_CARD_3DS"
    assert payment["status"] == "PAID"
    assert payment["three_ds_required"] is True
    assert payment["three_ds_status"] == "SUCCESS"
    assert payment["authorization_status"] == "AUTHORIZED"

    # Booking must be marked PAID
    with authenticated(client):
        booking_resp = client.get(f"/bookings/{booking['id']}")
    assert booking_resp.json()["status"] == "PAID"


def test_payment_3ds_failed(client):
    booking = _create_booking(client)

    with authenticated(client):
        response = client.post(
            "/payments",
            json={
                "booking_id": booking["id"],
                "method": "CREDIT_CARD_3DS",
                "three_ds_result": "FAILED",
            },
        )
    assert response.status_code == 201
    payment = response.json()

    assert payment["method"] == "CREDIT_CARD_3DS"
    assert payment["status"] == "FAILED"
    assert payment["three_ds_required"] is True
    assert payment["three_ds_status"] == "FAILED"
    assert payment["authorization_status"] == "DECLINED"
    assert payment["failure_code"] == "3DS_AUTH_FAILED"
    assert payment["failure_reason"] == "3DS authentication failed"

    # Booking should remain CONFIRMED, not PAID
    with authenticated(client):
        booking_resp = client.get(f"/bookings/{booking['id']}")
    assert booking_resp.json()["status"] == "CONFIRMED"


def test_payment_3ds_timeout(client):
    booking = _create_booking(client)

    with authenticated(client):
        response = client.post(
            "/payments",
            json={
                "booking_id": booking["id"],
                "method": "CREDIT_CARD_3DS",
                "three_ds_result": "TIMEOUT",
            },
        )
    assert response.status_code == 201
    payment = response.json()

    assert payment["method"] == "CREDIT_CARD_3DS"
    assert payment["status"] == "TIMEOUT"
    assert payment["three_ds_required"] is True
    assert payment["three_ds_status"] == "TIMEOUT"
    assert payment["authorization_status"] == "PENDING"
    assert payment["failure_code"] == "3DS_TIMEOUT"
    assert payment["failure_reason"] == "3DS authentication timed out"

    with authenticated(client):
        booking_resp = client.get(f"/bookings/{booking['id']}")
    assert booking_resp.json()["status"] == "CONFIRMED"


def test_payment_3ds_cancelled(client):
    booking = _create_booking(client)

    with authenticated(client):
        response = client.post(
            "/payments",
            json={
                "booking_id": booking["id"],
                "method": "CREDIT_CARD_3DS",
                "three_ds_result": "CANCELLED",
            },
        )
    assert response.status_code == 201
    payment = response.json()

    assert payment["method"] == "CREDIT_CARD_3DS"
    assert payment["status"] == "CANCELLED"
    assert payment["three_ds_required"] is True
    assert payment["three_ds_status"] == "CANCELLED"
    assert payment["authorization_status"] == "CANCELLED"
    assert payment["failure_code"] == "3DS_CANCELLED"
    assert payment["failure_reason"] == "Customer cancelled 3DS authentication"

    with authenticated(client):
        booking_resp = client.get(f"/bookings/{booking['id']}")
    assert booking_resp.json()["status"] == "CONFIRMED"


def test_payment_duplicate_conflict(client):
    booking = _create_booking(client)

    # First payment
    with authenticated(client):
        resp1 = client.post(
            "/payments",
            json={
                "booking_id": booking["id"],
                "method": "CASH",
            },
        )
    assert resp1.status_code == 201

    # Second payment for same booking
    with authenticated(client):
        resp2 = client.post(
            "/payments",
            json={
                "booking_id": booking["id"],
                "method": "CREDIT_CARD",
            },
        )
    assert resp2.status_code == 409
    assert resp2.json()["detail"] == "Payment already exists for this booking"


def test_payment_booking_not_found(client):
    with authenticated(client):
        response = client.post(
            "/payments",
            json={
                "booking_id": 999999,
                "method": "CASH",
            },
        )
    assert response.status_code == 404
    assert response.json()["detail"] == "Booking not found"


def test_payment_invalid_method(client):
    booking = _create_booking(client)

    with authenticated(client):
        response = client.post(
            "/payments",
            json={
                "booking_id": booking["id"],
                "method": "INVALID_METHOD",
            },
        )
    assert response.status_code == 422


def test_get_payment_by_booking_id(client):
    booking = _create_booking(client)

    with authenticated(client):
        create_resp = client.post(
            "/payments",
            json={
                "booking_id": booking["id"],
                "method": "UPI",
            },
        )
    assert create_resp.status_code == 201

    with authenticated(client):
        get_resp = client.get(f"/payments/{booking['id']}")
    assert get_resp.status_code == 200
    payment = get_resp.json()
    assert payment["booking_id"] == booking["id"]
    assert payment["method"] == "UPI"
    assert payment["status"] == "PAID"


def test_get_payment_not_found(client):
    booking = _create_booking(client)
    with authenticated(client):
        response = client.get(f"/payments/{booking['id']}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Payment not found"
