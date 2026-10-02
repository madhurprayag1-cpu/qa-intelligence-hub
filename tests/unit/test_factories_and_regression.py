import pytest
from factories import BookingPayloadFactory, PassengerFactory, PaymentPayloadFactory
from regression_selector import select_regression_tests


def test_passenger_factory_build_and_batch():
    passenger = PassengerFactory.build(loyalty_tier="GOLD")
    assert passenger.name
    assert "@qahub.io" in passenger.email
    assert passenger.passport_number.startswith("P")
    assert passenger.loyalty_tier == "GOLD"

    batch = PassengerFactory.build_batch(5)
    assert len(batch) == 5
    # Ensure distinct emails
    emails = {p.email for p in batch}
    assert len(emails) == 5


def test_passenger_factory_security_and_boundary():
    xss_passenger = PassengerFactory.build_security_xss()
    assert "<script>" in xss_passenger.name

    long_passenger = PassengerFactory.build_boundary_long_name()
    assert len(long_passenger.name) == 255


def test_booking_payload_factory():
    payload = BookingPayloadFactory.build(flight_id=42, seats=2)
    assert payload["flight_id"] == 42
    assert payload["seats"] == 2
    assert "passenger_name" in payload
    assert "passenger_email" in payload

    boundary_max = BookingPayloadFactory.build_boundary_max_seats(flight_id=42)
    assert boundary_max["seats"] == 9

    invalid_neg = BookingPayloadFactory.build_invalid_negative_seats(flight_id=42)
    assert invalid_neg["seats"] == -1


def test_payment_payload_factory():
    p3ds = PaymentPayloadFactory.build_3ds(booking_id=101, outcome="SUCCESS")
    assert p3ds["booking_id"] == 101
    assert p3ds["method"] == "CREDIT_CARD_3DS"
    assert p3ds["three_ds_result"] == "SUCCESS"

    pcard = PaymentPayloadFactory.build_direct_card(booking_id=102)
    assert pcard["method"] == "CREDIT_CARD"

    pwallet = PaymentPayloadFactory.build_wallet(booking_id=103)
    assert pwallet["method"] == "WALLET"


def test_regression_selector_payments_change():
    plan = select_regression_tests(["backend/app/routers/payments.py"])
    assert "tests/api/test_payments.py" in plan.selected_test_files
    assert "payment" in plan.selected_tags
    assert plan.playwright_command is not None
    assert "booking_3ds_e2e.spec.ts" in plan.playwright_command


def test_regression_selector_ai_change():
    plan = select_regression_tests(["ai-engine/rag.py", "backend/app/routers/ai.py"])
    assert "tests/ai/test_ai_platform.py" in plan.selected_test_files
    assert "ai" in plan.selected_tags
    assert "qa_platform_e2e.spec.ts" in plan.playwright_command


def test_regression_selector_unknown_fallback():
    plan = select_regression_tests(["random_script.py"])
    assert "tests/api/" in plan.selected_test_files
