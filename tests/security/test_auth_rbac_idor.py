from fastapi.testclient import TestClient
from tests.conftest import authenticated


def test_auth_login_success_and_jwt_issuance(client: TestClient):
    response = client.post(
        "/auth/login",
        json={"email": "passenger@qahub.io", "password": "passenger123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "passenger@qahub.io"
    assert data["user"]["role"] == "passenger"


def test_auth_login_invalid_password(client: TestClient):
    response = client.post(
        "/auth/login",
        json={"email": "passenger@qahub.io", "password": "wrongpassword!"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_auth_me_profile_retrieval(client: TestClient):
    # 1. Without token -> 401
    unauth_resp = client.get("/auth/me")
    assert unauth_resp.status_code == 401

    # 2. Login as QA Engineer
    login_resp = client.post(
        "/auth/login",
        json={"email": "qa@qahub.io", "password": "qa123"},
    )
    token = login_resp.json()["access_token"]

    # 3. With token -> 200
    auth_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert auth_resp.status_code == 200
    profile = auth_resp.json()
    assert profile["email"] == "qa@qahub.io"
    assert profile["role"] == "qa_engineer"


def test_tampered_jwt_token_rejection(client: TestClient):
    login_resp = client.post(
        "/auth/login",
        json={"email": "passenger@qahub.io", "password": "passenger123"},
    )
    valid_token = login_resp.json()["access_token"]

    # Tamper with signature
    tampered_token = valid_token[:-5] + "XXXXX"
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp.status_code == 401
    assert "tampered" in resp.json()["detail"].lower() or "signature" in resp.json()["detail"].lower()


def test_idor_passenger_cannot_inspect_other_passenger_booking(client: TestClient):
    # 1. Create a booking for victim passenger
    flights_resp = client.get("/flights")
    available_flights = [f for f in flights_resp.json() if f.get("available_seats", 0) > 3]
    flight = available_flights[0]

    with authenticated(client, email="qa@qahub.io"):
        booking_resp = client.post(
            "/bookings",
            json={
                "flight_id": flight["id"],
                "passenger_name": "Victim Passenger",
                "passenger_email": "victim@example.com",
                "seats": 1,
                "payment_method": "CARD",
            },
        )
    assert booking_resp.status_code == 201
    booking_id = booking_resp.json()["id"]

    # 2. Login as attacker passenger
    attacker_login = client.post(
        "/auth/login",
        json={"email": "passenger@qahub.io", "password": "passenger123"},
    )
    attacker_token = attacker_login.json()["access_token"]

    # 3. Attacker attempts to inspect victim's booking via numeric ID -> 403 Forbidden (IDOR)
    idor_resp = client.get(
        f"/bookings/{booking_id}",
        headers={"Authorization": f"Bearer {attacker_token}"},
    )
    assert idor_resp.status_code == 403
    assert "IDOR protection prevented access" in idor_resp.json()["detail"]


def test_idor_passenger_cannot_cancel_other_passenger_booking(client: TestClient):
    flights_resp = client.get("/flights")
    available_flights = [f for f in flights_resp.json() if f.get("available_seats", 0) > 3]
    flight = available_flights[0]

    with authenticated(client, email="qa@qahub.io"):
        booking_resp = client.post(
            "/bookings",
            json={
                "flight_id": flight["id"],
                "passenger_name": "Victim Passenger",
                "passenger_email": "victim@example.com",
                "seats": 1,
                "payment_method": "CARD",
            },
        )
    assert booking_resp.status_code == 201
    booking_id = booking_resp.json()["id"]

    attacker_login = client.post(
        "/auth/login",
        json={"email": "passenger@qahub.io", "password": "passenger123"},
    )
    attacker_token = attacker_login.json()["access_token"]

    # Attacker attempts to cancel victim's booking -> 403 Forbidden (IDOR)
    cancel_resp = client.post(
        f"/bookings/{booking_id}/cancel",
        headers={"Authorization": f"Bearer {attacker_token}"},
    )
    assert cancel_resp.status_code == 403
    assert "IDOR protection prevented cancellation" in cancel_resp.json()["detail"]


def test_staff_role_can_inspect_booking_for_customer_support(client: TestClient):
    flights_resp = client.get("/flights")
    available_flights = [f for f in flights_resp.json() if f.get("available_seats", 0) > 3]
    flight = available_flights[0]

    with authenticated(client):
        booking_resp = client.post(
            "/bookings",
            json={
                "flight_id": flight["id"],
                "passenger_name": "Customer",
                "passenger_email": "customer@example.com",
                "seats": 1,
                "payment_method": "CARD",
            },
        )
    assert booking_resp.status_code == 201
    booking_id = booking_resp.json()["id"]

    # Login as QA Engineer (support persona)
    staff_login = client.post(
        "/auth/login",
        json={"email": "qa@qahub.io", "password": "qa123"},
    )
    staff_token = staff_login.json()["access_token"]

    # QA / Admin has permission to inspect for verification
    resp = client.get(
        f"/bookings/{booking_id}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == booking_id


def test_rbac_passenger_cannot_override_quality_gate(client: TestClient):
    # Login as passenger
    pax_login = client.post(
        "/auth/login",
        json={"email": "passenger@qahub.io", "password": "passenger123"},
    )
    pax_token = pax_login.json()["access_token"]

    # Attempt to sign off release quality gate override
    override_resp = client.post(
        "/quality-gate/override",
        headers={"Authorization": f"Bearer {pax_token}"},
        json={
            "override_reason": "Emergency customer bypass requested",
            "target_release": "v1.2.0",
        },
    )
    assert override_resp.status_code == 403
    assert "Insufficient privileges" in override_resp.json()["detail"]


def test_rbac_release_manager_can_override_quality_gate(client: TestClient):
    # Login as release manager
    rel_login = client.post(
        "/auth/login",
        json={"email": "release@qahub.io", "password": "release123"},
    )
    rel_token = rel_login.json()["access_token"]

    # Successfully sign off release override
    override_resp = client.post(
        "/quality-gate/override",
        headers={"Authorization": f"Bearer {rel_token}"},
        json={
            "override_reason": "Executive CAB sign-off for critical patch release",
            "target_release": "v1.2.0",
        },
    )
    assert override_resp.status_code == 200
    data = override_resp.json()
    assert data["approved"] is True
    assert data["override_role"] == "release_manager"
    assert data["override_by"] == "release@qahub.io"
    assert "audit_timestamp" in data


def test_auth_demo_session_issuance_and_booking_authorization(client: TestClient):
    # 1. Obtain server-controlled demo passenger session
    resp = client.post("/auth/demo-session")
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "passenger@qahub.io"
    assert data["user"]["role"] == "passenger"

    token = data["access_token"]

    # 2. Verify identity through /auth/me
    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "passenger@qahub.io"

    # 3. Create booking with server-issued demo token
    flights = client.get("/flights").json()
    flight = next(f for f in flights if f.get("available_seats", 0) > 2)
    booking_resp = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "flight_id": flight["id"],
            "passenger_name": "Demo Passenger Alice",
            "passenger_email": "passenger@qahub.io",
            "seats": 1,
            "payment_method": "CARD",
        },
    )
    assert booking_resp.status_code == 201
    booking = booking_resp.json()
    assert booking["passenger_email"] == "passenger@qahub.io"
    assert booking["status"] == "CONFIRMED"

    # 4. Verify unauthenticated booking request without token is rejected with 401
    unauth_resp = client.post(
        "/bookings",
        json={
            "flight_id": flight["id"],
            "passenger_name": "Unauth User",
            "passenger_email": "unauth@example.com",
            "seats": 1,
        },
    )
    assert unauth_resp.status_code == 401
    assert "Missing Authorization Bearer token" in unauth_resp.json()["detail"]

