from fastapi.testclient import TestClient

from app.core.auth import User
from tests.conftest import authenticated_as


def _create_booking(client: TestClient, owner_id: int = 801) -> dict:
    flights = client.get("/flights").json()
    flight = next(item for item in flights if item.get("available_seats", 0) > 3)
    owner = User(
        id=owner_id,
        email=f"synthetic-owner-{owner_id}@example.test",
        name="Synthetic Owner",
        role="passenger",
    )
    with authenticated_as(client, owner):
        response = client.post(
            "/bookings",
            json={
                "flight_id": flight["id"],
                "passenger_name": "Synthetic Owner Test",
                "passenger_email": "owner-test@example.com",
                "seats": 1,
                "payment_method": "CARD",
            },
        )
    assert response.status_code == 201, response.text
    return response.json()


def test_passenger_cannot_read_or_cancel_booking_owned_by_another_identity(client: TestClient):
    booking = _create_booking(client)
    attacker = User(id=802, email="synthetic-attacker@example.test", name="Synthetic Attacker", role="passenger")
    with authenticated_as(client, attacker):
        by_id = client.get(f"/bookings/{booking['id']}")
        by_reference = client.get(f"/bookings/reference/{booking['reference']}")
        cancellation = client.post(f"/bookings/{booking['id']}/cancel")

    assert by_id.status_code == 403
    assert by_reference.status_code == 403
    assert cancellation.status_code == 403

def test_passenger_cannot_create_or_read_payment_for_another_users_booking(client: TestClient):
    owner = User(id=803, email="payment-owner@example.test", name="Payment Owner", role="passenger")
    booking = _create_booking(client, owner_id=owner.id)
    with authenticated_as(client, owner):
        payment = client.post(
            "/payments",
            json={"booking_id": booking["id"], "method": "CREDIT_CARD"},
        )
    assert payment.status_code == 201, payment.text

    attacker = User(id=804, email="payment-attacker@example.test", name="Payment Attacker", role="passenger")
    with authenticated_as(client, attacker):
        payment_create = client.post(
            "/payments",
            json={"booking_id": booking["id"], "method": "CREDIT_CARD"},
        )
        payment_read = client.get(f"/payments/{booking['id']}")

    assert payment_create.status_code == 403
    assert payment_read.status_code == 403


def test_booking_creation_requires_authentication(client: TestClient):
    flight = client.get("/flights").json()[0]
    response = client.post(
        "/bookings",
        json={
            "flight_id": flight["id"],
            "passenger_name": "Unauthenticated Test",
            "passenger_email": "unauthenticated@example.com",
            "seats": 1,
            "payment_method": "CARD",
        },
    )
    assert response.status_code == 401


def test_payment_endpoints_require_authentication(client: TestClient):
    # 1. Unauthenticated payment submission -> 401
    pay_resp = client.post(
        "/payments",
        json={"booking_id": 1, "method": "CREDIT_CARD"},
    )
    assert pay_resp.status_code == 401

    # 2. Unauthenticated payment lookup -> 401
    get_resp = client.get("/payments/1")
    assert get_resp.status_code == 401


def test_booking_reference_lookup_requires_authentication(client: TestClient):
    response = client.get("/bookings/reference/QAH-TESTREF")
    assert response.status_code == 401


def test_demo_users_endpoint_never_exposes_credentials(client: TestClient):
    response = client.get("/auth/demo-users")
    assert response.status_code == 200
    users = response.json()
    assert len(users) > 0
    forbidden_keys = {"password", "secret", "token", "hash", "salt"}
    for u in users:
        assert "role" in u
        assert "name" in u
        assert "email" in u
        for key in forbidden_keys:
            assert key not in u, f"Sensitive key '{key}' exposed in demo-users API"


def test_production_environment_safeguards(client: TestClient, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "environment", "production")

    # 1. Demo users listing is disabled (404)
    demo_resp = client.get("/auth/demo-users")
    assert demo_resp.status_code == 404

    # 2. Demo login is disabled (503)
    login_resp = client.post(
        "/auth/login",
        json={"email": "passenger@qahub.io", "password": "passenger123"},
    )
    assert login_resp.status_code == 503
    assert "disabled in production" in login_resp.json()["detail"]

    # 3. Booking creation disabled until prod auth configured (503)
    owner = User(id=805, email="prod-test@example.test", name="Prod Test", role="passenger")
    with authenticated_as(client, owner):
        booking_resp = client.post(
            "/bookings",
            json={
                "flight_id": 1,
                "passenger_name": "Prod Test",
                "passenger_email": "prod@example.com",
                "seats": 1,
            },
        )
    assert booking_resp.status_code == 503
    assert "production authentication is configured" in booking_resp.json()["detail"]

    # 4. Payment processing disabled until prod auth configured (503)
    with authenticated_as(client, owner):
        pay_resp = client.post(
            "/payments",
            json={"booking_id": 1, "method": "CREDIT_CARD"},
        )
    assert pay_resp.status_code == 503
    assert "production authentication is configured" in pay_resp.json()["detail"]


def test_jwt_secret_production_validation(monkeypatch):
    import pytest
    from app.core.auth import _jwt_secret
    from app.core.config import settings

    monkeypatch.setattr(settings, "environment", "production")

    # Empty secret in production must raise RuntimeError
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setattr(settings, "jwt_secret", "")
    with pytest.raises(RuntimeError, match="at least 32 characters"):
        _jwt_secret()

    # Short secret (<32 chars) in production must raise RuntimeError
    monkeypatch.setenv("JWT_SECRET", "too-short-secret")
    with pytest.raises(RuntimeError, match="at least 32 characters"):
        _jwt_secret()

    # Default 'change-me' placeholder must raise RuntimeError
    monkeypatch.setenv("JWT_SECRET", "change-me")
    with pytest.raises(RuntimeError, match="at least 32 characters"):
        _jwt_secret()

    # Valid >= 32 chars secret passes
    valid_secret = "a" * 32
    monkeypatch.setenv("JWT_SECRET", valid_secret)
    assert _jwt_secret() == valid_secret
