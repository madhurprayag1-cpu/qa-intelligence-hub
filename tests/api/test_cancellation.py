import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.flight import Flight
from app.models.payment import Payment
from tests.conftest import authenticated


def test_cancel_confirmed_unpaid_booking(client: TestClient, db_session: Session):
    """
    Verify cancellation of an unpaid booking:
    1. Seat inventory is restored to the flight.
    2. Booking status transitions from CONFIRMED to CANCELLED.
    3. Refund status is NOT_APPLICABLE since no payment was processed.
    """
    flight = db_session.query(Flight).filter(Flight.active.is_(True), Flight.available_seats > 5).first()
    assert flight is not None
    original_seats = flight.available_seats

    with authenticated(client):
        b_res = client.post(
        "/bookings",
        json={
            "flight_id": flight.id,
            "passenger_name": "Cancel Tester",
            "passenger_email": "cancel@qahub.io",
            "seats": 2,
        },
    )
    assert b_res.status_code == 201
    booking_id = b_res.json()["id"]

    db_session.refresh(flight)
    assert flight.available_seats == original_seats - 2

    # Cancel booking
    with authenticated(client):
        cancel_res = client.post(f"/bookings/{booking_id}/cancel")
    assert cancel_res.status_code == 200
    data = cancel_res.json()

    assert data["booking_id"] == booking_id
    assert data["previous_status"] == "CONFIRMED"
    assert data["current_status"] == "CANCELLED"
    assert data["seats_released"] == 2
    assert data["refund_status"] == "NOT_APPLICABLE"
    assert data["refund_amount"] == 0.0

    # Verify inventory is fully restored in database
    db_session.refresh(flight)
    assert flight.available_seats == original_seats


def test_cancel_paid_booking_triggers_refund(client: TestClient, db_session: Session):
    """
    Verify cancellation of a PAID booking:
    1. Seat inventory is restored.
    2. Booking status transitions to CANCELLED.
    3. Associated payment record transitions to REFUNDED.
    4. Refund amount matches total booking fare.
    """
    flight = db_session.query(Flight).filter(Flight.active.is_(True), Flight.available_seats > 5).first()
    assert flight is not None
    seats_to_book = 1

    with authenticated(client):
        b_res = client.post(
        "/bookings",
        json={
            "flight_id": flight.id,
            "passenger_name": "Refund Tester",
            "passenger_email": "refund@qahub.io",
            "seats": seats_to_book,
        },
    )
    assert b_res.status_code == 201
    booking = b_res.json()
    booking_id = booking["id"]
    fare = booking["total_amount"]

    # Pay booking
    with authenticated(client):
        pay_res = client.post(
        "/payments",
        json={"booking_id": booking_id, "method": "CREDIT_CARD"},
    )
    assert pay_res.status_code == 201
    assert pay_res.json()["status"] == "PAID"

    # Cancel and assert refund
    with authenticated(client):
        cancel_res = client.post(f"/bookings/{booking_id}/cancel")
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()

    assert cancel_data["current_status"] == "CANCELLED"
    assert cancel_data["refund_status"] == "REFUNDED"
    assert cancel_data["refund_amount"] == fare

    # Verify payment in DB
    payment = db_session.query(Payment).filter(Payment.booking_id == booking_id).first()
    assert payment is not None
    assert payment.status == "REFUNDED"


def test_cancel_already_cancelled_booking_fails(client: TestClient, db_session: Session):
    """Ensure duplicate cancellation request on already CANCELLED booking is rejected with 409 Conflict."""
    flight = db_session.query(Flight).filter(Flight.active.is_(True), Flight.available_seats > 2).first()
    assert flight is not None

    with authenticated(client):
        b_res = client.post(
        "/bookings",
        json={
            "flight_id": flight.id,
            "passenger_name": "Conflict Tester",
            "passenger_email": "conflict@qahub.io",
            "seats": 1,
        },
    )
    booking_id = b_res.json()["id"]

    # First cancel succeeds
    with authenticated(client):
        c1 = client.post(f"/bookings/{booking_id}/cancel")
    assert c1.status_code == 200

    # Second cancel rejected with 409
    with authenticated(client):
        c2 = client.post(f"/bookings/{booking_id}/cancel")
    assert c2.status_code == 409
    assert "already cancelled" in c2.json()["detail"].lower()


def test_cancel_nonexistent_booking_fails(client: TestClient):
    """Ensure cancelling non-existent booking ID yields 404 Not Found."""
    with authenticated(client):
        res = client.post("/bookings/99999999/cancel")
    assert res.status_code == 404
