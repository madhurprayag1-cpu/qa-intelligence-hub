import pytest
from fastapi.testclient import TestClient


def test_get_quality_gate_policies(client: TestClient):
    """Verify endpoint returns preset policies with required thresholds."""
    res = client.get("/quality-gate/policies")
    assert res.status_code == 200
    policies = res.json()
    assert "PRODUCTION_STRICT" in policies
    assert "STAGING_STANDARD" in policies
    assert "DEV_PR_FAST" in policies

    strict = policies["PRODUCTION_STRICT"]
    assert strict["min_pass_rate"] == 1.0
    assert strict["max_critical_defects"] == 0
    assert strict["min_rag_groundedness"] == 0.85


def test_evaluate_quality_gate_passed(client: TestClient):
    """Verify successful evaluation under PRODUCTION_STRICT policy."""
    payload = {
        "policy_name": "PRODUCTION_STRICT",
        "total_tests": 40,
        "passed_tests": 40,
        "failed_tests": 0,
        "critical_defects": 0,
        "contract_failures": 0,
        "rag_groundedness_score": 0.95,
    }
    res = client.post("/quality-gate/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["passed"] is True
    assert data["status"] == "PASSED"
    assert data["pass_rate"] == 1.0
    assert len(data["violations"]) == 0


def test_evaluate_quality_gate_failed_violations(client: TestClient):
    """Verify quality gate blocks release when test failures and critical defects are present."""
    payload = {
        "policy_name": "PRODUCTION_STRICT",
        "total_tests": 40,
        "passed_tests": 38,
        "failed_tests": 2,
        "critical_defects": 1,
        "contract_failures": 1,
        "rag_groundedness_score": 0.60,
    }
    res = client.post("/quality-gate/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["passed"] is False
    assert data["status"] == "FAILED"
    assert len(data["violations"]) >= 3


def test_evaluate_quality_gate_custom_policy(client: TestClient):
    """Verify evaluation with custom policy overrides."""
    payload = {
        "custom_policy": {
            "name": "CUSTOM_PERMISSIVE",
            "min_pass_rate": 0.80,
            "max_failure_rate": 0.20,
            "max_critical_defects": 2,
            "min_rag_groundedness": 0.50,
            "max_contract_failures": 2,
            "max_security_vulnerabilities": 0,
            "max_flaky_tests": 5,
            "min_total_tests": 1,
        },
        "total_tests": 10,
        "passed_tests": 8,
        "failed_tests": 2,
        "critical_defects": 1,
    }
    res = client.post("/quality-gate/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["passed"] is True
    assert data["policy_name"] == "CUSTOM_PERMISSIVE"
