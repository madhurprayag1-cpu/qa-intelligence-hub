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


def test_get_qa_layers_include_all(client: TestClient):
    """Verify full 11-layer topology when include_all is requested."""
    resp = client.get("/qa/layers?include_all=true")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_layers"] >= 11
    assert data["total_tests"] >= 450
    layer_ids = [l["id"] for l in data["layers"]]
    assert "domain" in layer_ids
    assert "ui" in layer_ids


def test_get_capability_catalog(client: TestClient):
    """Verify paginated capability catalog retrieval."""
    resp = client.get("/qa/catalog?limit=10&page=1")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] >= 450
    assert data["page"] == 1
    assert data["limit"] == 10
    assert len(data["capabilities"]) == 10
    first_cap = data["capabilities"][0]
    assert "id" in first_cap
    assert "domain" in first_cap
    assert "feature" in first_cap
    assert "layer" in first_cap
    assert "expected_result" in first_cap


def test_get_capability_catalog_filtering(client: TestClient):
    """Verify domain and layer filtering on capability catalog."""
    resp = client.get("/qa/catalog?domain=airline&layer=API&limit=10")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] > 0
    for cap in data["capabilities"]:
        assert cap["domain"].lower() == "airline"
        assert cap["layer"].upper() == "API"


def test_get_catalog_summary(client: TestClient):
    """Verify summary metrics endpoint for Master Capability Inventory."""
    resp = client.get("/qa/catalog/summary")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_capabilities"] >= 450
    assert "by_domain" in data
    assert "by_layer" in data
    assert "by_priority" in data
    assert "airline" in data["by_domain"]
    assert "healthcare" in data["by_domain"]


def test_get_latest_evidence(client: TestClient):
    """Verify structured test execution run and evidence records endpoint."""
    resp = client.get("/qa/evidence/latest?limit=25")
    assert resp.status_code == 200
    data = resp.json()

    assert "run_id" in data
    assert "total_tests" in data
    assert "records" in data
    if data["total_tests"] > 0:
        assert len(data["records"]) <= 25
        first_rec = data["records"][0]
        assert "test_id" in first_rec
        assert "status" in first_rec
        assert "evidence" in first_rec


def test_requirement_analysis_traceability_endpoint(client: TestClient):
    response = client.post(
        "/qa/requirements/analyze",
        json={
            "requirement_id": "REQ-API-001",
            "requirement": "Support secure passenger self-service cancellation",
            "domain": "airline",
            "impacted_components": ["API", "UI", "database", "security"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["requirement_id"] == "REQ-API-001"
    assert data["traceability_status"] == "READY_FOR_IMPLEMENTATION"
    assert len(data["acceptance_criteria"]) == 3
    assert len(data["test_scenarios"]) == 3
    assert {s["type"] for s in data["test_scenarios"]} == {"POSITIVE", "NEGATIVE", "BOUNDARY"}
    assert data["run_id"].startswith("RUN-")


def test_runtime_metrics_endpoint(client: TestClient):
    health = client.get("/health")
    assert health.status_code == 200
    response = client.get("/qa/runtime/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["scope"] == "process_instance"
    assert data["total_requests"] >= 1
    assert data["error_requests_5xx"] >= 0
    assert 0.0 <= data["error_rate"] <= 1.0
    assert data["p95_latency_ms"] >= 0.0


def test_requirement_trace_persistence_and_engineering_plan(client: TestClient):
    payload = {
        "requirement_id": "REQ-PERSIST-001",
        "requirement": "Provide secure self-service booking cancellation",
        "domain": "airline",
        "impacted_components": ["API", "UI", "database", "security"],
    }
    response = client.post("/qa/requirements/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["persisted"] is True
    assert data["requirement_id"] == "REQ-PERSIST-001"

    trace = client.get("/qa/requirements/REQ-PERSIST-001")
    assert trace.status_code == 200
    trace_data = trace.json()
    assert trace_data["requirement_id"] == "REQ-PERSIST-001"
    assert len(trace_data["acceptance_criteria"]) == 3
    assert len(trace_data["test_scenarios"]) == 3

    plan = client.post(
        "/qa/requirements/REQ-PERSIST-001/engineering-plan",
        json={"requirement_id": "REQ-PERSIST-001"},
    )
    assert plan.status_code == 200
    plan_data = plan.json()
    assert plan_data["status"] == "PLAN_READY_FOR_CONTROLLED_IMPLEMENTATION"
    assert any(step["name"] == "PRODUCTION_STRICT_GATE" for step in plan_data["phases"])

    test_plan = client.get("/qa/requirements/REQ-PERSIST-001/test-plan")
    assert test_plan.status_code == 200
    test_plan_data = test_plan.json()
    assert test_plan_data["total_scenarios"] == 3
    assert "SECURITY" in test_plan_data["required_layers"]


test_marker_removed__DO_NOT_USE
# kept synchronous because TestClient calls are synchronous
def test_production_observation_creates_incident_and_supports_resolution(client: TestClient):
    response = await client.post(
        "/qa/production/observations",
        json={
            "source": "production-smoke",
            "signal": "api_failure",
            "status": "CRITICAL",
            "summary": "Payment API returned 504 during checkout",
            "details": {
                "status_code": 504,
                "endpoint": "/payments",
                "error_message": "3DS timeout while waiting for provider",
            },
            "serving_sha": "TEST-SHA",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["incident_created"] is True
    assert data["incident_id"]

    incidents = client.get("/qa/production/incidents?status=OPEN")
    assert incidents.status_code == 200
    incident_list = incidents.json()
    assert incident_list["total"] >= 1
    incident_id = data["incident_id"]

    detail = client.get(f"/qa/production/incidents/{incident_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "OPEN"

    resolved = client.post(
        f"/qa/production/incidents/{incident_id}/resolve",
        json={"corrective_action": "Fix timeout handling and rerun focused plus full regression."},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "RESOLVED"
