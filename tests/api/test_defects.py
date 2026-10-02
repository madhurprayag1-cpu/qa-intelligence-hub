import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.flight import Flight
from tests.conftest import authenticated


def test_list_and_get_defects(client: TestClient):
    """Verify defects catalog endpoint returns all documented intentional defect scenarios."""
    res = client.get("/defects")
    assert res.status_code == 200
    defects = res.json()
    assert len(defects) >= 5

    ids = [d["id"] for d in defects]
    assert "OVERBOOKING_RACE" in ids
    assert "CALCULATION_DRIFT" in ids
    assert "STALE_INVENTORY" in ids
    assert "UPSTREAM_GATEWAY_TIMEOUT" in ids
    assert "SCHEMA_CONTRACT_VIOLATION" in ids

    # Test individual defect lookup
    single_res = client.get("/defects/OVERBOOKING_RACE")
    assert single_res.status_code == 200
    defect_obj = single_res.json()
    assert defect_obj["id"] == "OVERBOOKING_RACE"
    assert "POST /bookings" in defect_obj["affected_endpoint"]

    # Test unknown defect returns 404
    missing_res = client.get("/defects/NON_EXISTENT_DEFECT")
    assert missing_res.status_code == 404


def test_overbooking_race_defect_simulation(client: TestClient, db_session: Session):
    """
    Demonstrate that without defect header, system rejects booking with 409 when seats are 0.
    With 'X-Simulate-Defect: OVERBOOKING_RACE', it allows overbooking past capacity.
    """
    # Find or adjust a flight with 0 available seats
    flight = db_session.query(Flight).filter(Flight.active.is_(True)).first()
    assert flight is not None
    original_seats = flight.available_seats

    try:
        flight.available_seats = 0
        db_session.commit()

        booking_payload = {
            "flight_id": flight.id,
            "passenger_name": "QA Overbooking Tester",
            "passenger_email": "overbook@test.com",
            "seats": 2,
        }

        # 1. Standard Production Behavior: must reject with 409 Insufficient seat availability
        with authenticated(client):
            normal_res = client.post("/bookings", json=booking_payload)
        assert normal_res.status_code == 409
        assert "Insufficient seat availability" in normal_res.json()["detail"]

        # 2. Defect Simulation: bypasses validation and succeeds (simulating concurrency bug)
        with authenticated(client):
            defect_res = client.post(
                "/bookings",
                json=booking_payload,
                headers={"X-Simulate-Defect": "OVERBOOKING_RACE"},
            )
        assert defect_res.status_code == 201
        created_booking = defect_res.json()
        assert created_booking["status"] == "CONFIRMED"

        # Verify invariant violation in DB: available_seats went negative (-2)
        db_session.refresh(flight)
        assert flight.available_seats == -2

    finally:
        flight.available_seats = original_seats
        db_session.commit()


def test_calculation_drift_defect_simulation(client: TestClient, db_session: Session):
    """Verify that CALCULATION_DRIFT header introduces price drift on booking and payment."""
    flight = db_session.query(Flight).filter(Flight.active.is_(True), Flight.available_seats > 5).first()
    assert flight is not None

    booking_payload = {
        "flight_id": flight.id,
        "passenger_name": "Fare Drift Tester",
        "passenger_email": "faredrift@test.com",
        "seats": 2,
    }

    expected_clean_price = round(float(flight.base_price) * 2, 2)

    # 1. Standard calculation: exact base * seats
    with authenticated(client):
        clean_res = client.post("/bookings", json=booking_payload)
    assert clean_res.status_code == 201
    clean_booking = clean_res.json()
    assert clean_booking["total_amount"] == expected_clean_price

    # 2. Simulated Defect calculation: drifted price
    with authenticated(client):
        drift_res = client.post(
            "/bookings",
            json=booking_payload,
            headers={"X-Simulate-Defect": "CALCULATION_DRIFT"},
        )
    assert drift_res.status_code == 201
    drift_booking = drift_res.json()
    assert drift_booking["total_amount"] != expected_clean_price
    # Verify drift formula: round(base * seats * 1.35 + 49.99, 2)
    expected_drifted = round(expected_clean_price * 1.35 + 49.99, 2)
    assert drift_booking["total_amount"] == expected_drifted


def test_upstream_gateway_timeout_defect_simulation(client: TestClient, db_session: Session):
    """Verify that UPSTREAM_GATEWAY_TIMEOUT simulates 504 gateway failure in payment endpoint."""
    flight = db_session.query(Flight).filter(Flight.active.is_(True), Flight.available_seats > 2).first()
    assert flight is not None

    with authenticated(client):
        b_res = client.post(
            "/bookings",
            json={
                "flight_id": flight.id,
                "passenger_name": "Gateway Timeout Tester",
                "passenger_email": "timeout@test.com",
                "seats": 1,
            },
        )
    assert b_res.status_code == 201
    booking_id = b_res.json()["id"]

    # Trigger payment with UPSTREAM_GATEWAY_TIMEOUT simulation
    with authenticated(client):
        pay_res = client.post(
            "/payments",
            json={
                "booking_id": booking_id,
                "method": "CREDIT_CARD",
            },
            headers={"X-Simulate-Defect": "UPSTREAM_GATEWAY_TIMEOUT"},
        )
    assert pay_res.status_code == 504
    assert "Upstream payment gateway timeout" in pay_res.json()["detail"]


def test_stale_inventory_defect_simulation(client: TestClient):
    """Verify that STALE_INVENTORY header returns inflated inventory of 999 seats."""
    # Normal search
    normal_res = client.get("/search/flights?origin=ATH&destination=SKG")
    assert normal_res.status_code == 200
    normal_flights = normal_res.json()
    assert len(normal_flights) > 0
    assert normal_flights[0]["available_seats"] < 999

    # Defect search
    stale_res = client.get(
        "/search/flights?origin=ATH&destination=SKG",
        headers={"X-Simulate-Defect": "STALE_INVENTORY"},
    )
    assert stale_res.status_code == 200
    stale_flights = stale_res.json()
    assert len(stale_flights) > 0
    for f in stale_flights:
        assert f["available_seats"] == 999


def test_schema_contract_violation_defect_simulation(client: TestClient, db_session: Session):
    """Verify that SCHEMA_CONTRACT_VIOLATION header omits required passenger_email in response."""
    flight = db_session.query(Flight).filter(Flight.active.is_(True), Flight.available_seats > 2).first()
    assert flight is not None

    with authenticated(client):
        b_res = client.post(
            "/bookings",
            json={
                "flight_id": flight.id,
                "passenger_name": "Contract Tester",
                "passenger_email": "contract@test.com",
                "seats": 1,
            },
        )
    assert b_res.status_code == 201
    booking_id = b_res.json()["id"]

    # Normal fetch contains passenger_email
    with authenticated(client):
        normal_fetch = client.get(f"/bookings/{booking_id}")
    assert normal_fetch.status_code == 200
    assert "passenger_email" in normal_fetch.json()
    assert normal_fetch.json()["passenger_email"] == "contract@test.com"

    # Defect simulated fetch omits passenger_email
    with authenticated(client):
        defect_fetch = client.get(
            f"/bookings/{booking_id}",
            headers={"X-Simulate-Defect": "SCHEMA_CONTRACT_VIOLATION"},
        )
    assert defect_fetch.status_code == 200
    defect_data = defect_fetch.json()
    assert "passenger_email" not in defect_data
