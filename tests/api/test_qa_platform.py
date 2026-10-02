"""QA Platform Engine API Tests: Layers, Regression Impact, Test Runner & AI Reporting.

Adheres to AGENTS.md Sections 2, 5, 6, 11, 24:
- Verifies /qa/layers endpoint for test pyramid metadata
- Verifies /qa/regression/impact for git diff impact calculation
- Verifies /qa/test-runner/execute with telemetry and Quality Gate persistence
- Verifies /qa/reporting/release-report for AI-generated executive sign-offs
"""

import pytest
from fastapi.testclient import TestClient


def test_get_qa_layers(client: TestClient):
    """Verify test pyramid layers metadata endpoint."""
    resp = client.get("/qa/layers")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_layers"] == 9
    assert data["total_tests"] >= 120

    layer_ids = [l["id"] for l in data["layers"]]
    expected_layers = ["database", "regression", "contract", "unit", "api", "security", "ai", "agents", "performance"]
    for el in expected_layers:
        assert el in layer_ids


def test_calculate_regression_impact_preset(client: TestClient):
    """Verify calculating test impact using preset PR diff."""
    payload = {"preset": "PAYMENTS_3DS"}
    resp = client.post("/qa/regression/impact", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "tests/api/test_payments.py" in data["selected_test_files"]
    assert "payment" in data["selected_tags"]
    assert data["playwright_command"] is not None
    assert "booking_3ds_e2e.spec.ts" in data["playwright_command"]
    assert len(data["reasoning"]) >= 2


def test_calculate_regression_impact_custom_files(client: TestClient):
    """Verify calculating test impact from custom list of changed files."""
    payload = {
        "changed_files": [
            "ai-engine/rag.py",
            "backend/app/models/booking.py",
        ]
    }
    resp = client.post("/qa/regression/impact", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "tests/ai/test_ai_platform.py" in data["selected_test_files"]
    assert "tests/database/test_database_invariants.py" in data["selected_test_files"]
    assert "ai" in data["selected_tags"]
    assert "database" in data["selected_tags"]


def test_test_runner_execute_specific_layer(client: TestClient):
    """Verify executing specific test layer through test runner API."""
    payload = {
        "layer": "database",
        "evaluate_quality_gate": True,
        "policy_name": "PRODUCTION_STRICT",
    }
    resp = client.post("/qa/test-runner/execute", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_tests"] == 10
    assert data["passed_tests"] == 10
    assert data["failed_tests"] == 0
    assert data["duration_ms"] > 0
    assert len(data["results"]) == 10

    # Quality Gate should have evaluated and passed
    assert data["quality_gate"] is not None
    assert data["quality_gate"]["passed"] is True
    assert data["quality_gate"]["status"] == "PASSED"
    assert data["quality_gate"]["run_id"].startswith("QG-RUN-")


def test_test_runner_execute_all_layers(client: TestClient):
    """Verify executing full multi-layer test suite with gate evaluation."""
    payload = {
        "layer": "all",
        "evaluate_quality_gate": True,
        "policy_name": "PRODUCTION_STRICT",
    }
    resp = client.post("/qa/test-runner/execute", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_tests"] >= 120
    assert data["passed_tests"] == data["total_tests"]
    assert data["failed_tests"] == 0
    assert data["quality_gate"]["passed"] is True


def test_generate_release_report_endpoint(client: TestClient):
    """Verify AI ReportingAgent release report synthesis endpoint."""
    payload = {
        "policy_name": "PRODUCTION_STRICT",
        "total_tests": 143,
        "passed_tests": 143,
        "failed_tests": 0,
        "critical_defects": 0,
        "contract_failures": 0,
        "security_vulnerabilities": 0,
        "rag_groundedness_score": 0.95,
        "quality_gate_status": "PASSED",
        "violations": [],
    }
    resp = client.post("/qa/reporting/release-report", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["events"]) >= 2


def test_self_heal_selector_endpoint(client: TestClient):
    """Verify UIHealingAgent self-healing selector endpoint."""
    payload = {
        "broken_selector": "//div[3]/form/button[@type='submit']",
        "dom_snippet": '<button data-testid="checkout-submit-btn">Complete Purchase</button>',
        "failure_message": "Timeout 5000ms waiting for locator",
        "target_action": "click",
    }
    resp = client.post("/qa/self-heal/selector", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "COMPLETED"
    rec = data["recommendation"]
    assert rec["healed_selector"] == "page.getByTestId('checkout-submit-btn')"
    assert rec["resilience_rating"] == "HIGH"
    assert "await page.getByTestId('checkout-submit-btn').click();" in rec["code_replacement"]


def test_performance_stress_test_endpoint(client: TestClient):
    """Verify high-concurrency stress test endpoint."""
    payload = {
        "endpoint": "/health",
        "total_requests": 20,
        "concurrency": 5,
    }
    resp = client.post("/qa/performance/stress-test", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_requests"] == 20
    assert data["successful_requests"] == 20
    assert data["requests_per_second"] > 0
    assert "p95_latency_ms" in data
    assert data["p95_latency_ms"] < 250.0


def test_get_ai_providers_status_endpoint(client: TestClient):
    """Verify AI provider status and abstraction compliance endpoint."""
    resp = client.get("/qa/ai/providers/status")
    assert resp.status_code == 200
    data = resp.json()

    assert data["provider_abstraction_compliant"] is True
    assert "active_provider" in data
    assert "current_mode" in data
    assert "gemini" in data["providers"]
    assert "claude" in data["providers"]
    assert "openai" in data["providers"]
    assert "mock" in data["providers"]
    assert data["providers"]["mock"]["configured"] is True
