import asyncio

import pytest
from fastapi import HTTPException

from app.core.auth import get_current_domain_user
from app.core.config import settings
from app.core.production_safety import ProductionSafetyMiddleware


@pytest.fixture
def production_mode(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    ProductionSafetyMiddleware.reset_rate_limits()
    yield
    ProductionSafetyMiddleware.reset_rate_limits()


def test_production_blocks_booking_and_payment_mutations(client, production_mode):
    booking = client.post("/bookings", json={})
    payment = client.post("/payments", json={})
    assert booking.status_code == 403
    assert payment.status_code == 403
    assert booking.json()["detail"] == "This operation is disabled in the public production demo."


def test_production_blocks_persistent_ai_and_qa_operations(client, production_mode):
    knowledge = client.post(
        "/ai/rag/knowledge",
        json={"document_id": "demo-doc", "text": "Synthetic test-only knowledge."},
    )
    observation = client.post("/qa/production/observations", json={})
    requirement = client.post(
        "/qa/requirements/analyze",
        json={"requirement": "Persisted requirement analysis should be disabled."},
    )
    assert knowledge.status_code == 403
    assert observation.status_code == 403
    assert requirement.status_code == 403


def test_sensitive_record_reads_are_not_public(client, production_mode):
    checks = [
        client.get("/healthcare/patients"),
        client.get("/healthcare/observations"),
        client.get("/fintech/accounts"),
        client.get("/ecommerce/orders"),
        client.get("/telecom/subscribers"),
        client.get("/qa/production/incidents"),
        client.get("/qa/runtime/metrics"),
    ]
    assert all(response.status_code == 404 for response in checks)
    assert all(response.json() == {"detail": "Not found"} for response in checks)


def test_public_synthetic_catalog_remains_available(client, production_mode):
    response = client.get("/healthcare/practitioners")
    assert response.status_code == 200
    assert response.json()


def test_public_read_only_ai_operation_remains_available(client, production_mode):
    response = client.post(
        "/ai/evaluate/groundedness",
        json={"answer": "A synthetic answer.", "context": "Synthetic context."},
    )
    assert response.status_code == 200


def test_production_domain_identity_cannot_be_forged_with_headers(production_mode):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            get_current_domain_user(
                credentials=None,
                x_user_role="admin",
                x_user_id="1",
            )
        )
    assert exc.value.status_code == 401


def test_production_disables_intentional_defect_injection(client, production_mode):
    response = client.get(
        "/search/flights?origin=ATH&destination=SKG",
        headers={"X-Simulate-Defect": "STALE_INVENTORY"},
    )
    assert response.status_code == 200
    assert all(row["available_seats"] != 999 for row in response.json())


def test_public_post_rate_limit_returns_429_and_retry_after(client, production_mode, monkeypatch):
    monkeypatch.setattr(ProductionSafetyMiddleware, "MAX_REQUESTS_PER_WINDOW", 2)
    payload = {"answer": "A synthetic answer.", "context": "Synthetic context."}
    first = client.post("/ai/evaluate/groundedness", json=payload)
    second = client.post("/ai/evaluate/groundedness", json=payload)
    third = client.post("/ai/evaluate/groundedness", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.headers["Retry-After"] == "60"


def test_cors_does_not_trust_arbitrary_vercel_subdomains(client, production_mode):
    response = client.options(
        "/health",
        headers={
            "Origin": "https://untrusted-preview.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers

def test_security_headers_are_set_on_public_responses(client, production_mode):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
