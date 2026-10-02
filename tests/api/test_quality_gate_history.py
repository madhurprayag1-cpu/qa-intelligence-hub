"""Quality Gate Execution History & Audit Telemetry Tests.

Adheres to AGENTS.md Sections 14, 22, 24 & 25:
- Verifies persistent audit trail of quality gate decisions in PostgreSQL/SQLite
- Tests GET /quality-gate/runs listing and filtering
- Tests GET /quality-gate/runs/{run_id} detailed telemetry retrieval
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.models.quality_gate_run import QualityGateRunModel


@pytest.fixture
def test_client_with_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)


    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def test_evaluate_persists_run_and_returns_run_id(test_client_with_db):
    payload = {
        "policy_name": "PRODUCTION_STRICT",
        "total_tests": 85,
        "passed_tests": 85,
        "failed_tests": 0,
        "critical_defects": 0,
        "contract_failures": 0,
        "security_vulnerabilities": 0,
        "rag_groundedness_score": 0.94,
    }
    resp = test_client_with_db.post("/quality-gate/evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "run_id" in data
    assert data["run_id"].startswith("QG-RUN-")
    assert data["passed"] is True
    assert data["status"] == "PASSED"
    assert data["pass_rate"] == 1.0


def test_list_and_get_quality_gate_runs(test_client_with_db):
    # 1. Trigger two evaluations
    payload_a = {
        "policy_name": "PRODUCTION_STRICT",
        "total_tests": 100,
        "passed_tests": 100,
        "failed_tests": 0,
    }
    payload_b = {
        "policy_name": "STAGING_STANDARD",
        "total_tests": 100,
        "passed_tests": 90,
        "failed_tests": 10,
        "critical_defects": 1,
    }

    res_a = test_client_with_db.post("/quality-gate/evaluate", json=payload_a)
    assert res_a.status_code == 200
    run_id_a = res_a.json()["run_id"]

    res_b = test_client_with_db.post("/quality-gate/evaluate", json=payload_b)
    assert res_b.status_code == 200
    run_id_b = res_b.json()["run_id"]

    # 2. List runs
    list_res = test_client_with_db.get("/quality-gate/runs")
    assert list_res.status_code == 200
    runs = list_res.json()
    assert len(runs) >= 2
    retrieved_ids = [r["run_id"] for r in runs]
    assert run_id_a in retrieved_ids
    assert run_id_b in retrieved_ids

    # 3. Retrieve individual run by run_id
    detail_res = test_client_with_db.get(f"/quality-gate/runs/{run_id_b}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["run_id"] == run_id_b
    assert detail["passed"] is False
    assert detail["status"] == "FAILED"
    assert detail["policy_name"] == "STAGING_STANDARD"
    assert len(detail["violations"]) > 0

    # 4. Unknown run returns 404
    missing_res = test_client_with_db.get("/quality-gate/runs/QG-RUN-NONEXISTENT")
    assert missing_res.status_code == 404
