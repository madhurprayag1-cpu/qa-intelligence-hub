"""Deterministic Automated Test Suite for Phase 6 Task 6.3:
Agentic Defect RCA Auto-Remediation.

Adheres strictly to AGENTS.md Sections 5, 6, 7, 9, 11, 24, 35 and docs/ROADMAP.md:
- Autonomous connection between DefectRCAAgent and synthetic code patch synthesis.
- Validation of remediation patches across intentional defects DEF-001 through DEF-005:
    * DEF-001: FARE_CALCULATION_OVERCHARGE / CALCULATION_DRIFT
    * DEF-002: STALE_SEAT_INVENTORY / OVERBOOKING_RACE
    * DEF-003: PAYMENT_GATEWAY_TIMEOUT / UPSTREAM_GATEWAY_TIMEOUT
    * DEF-004: RAG_UNGROUNDED_HALLUCINATION
    * DEF-005: SQL_INJECTION_VULNERABILITY / SCHEMA_CONTRACT_VIOLATION
- Automatic execution of impacted regression test suites selected via regression_selector.
- Enforces strict invariant: A fix is ONLY successful if defect is resolved AND regression suite remains green.
- Rejection of invalid / regression-breaking patches.
- Quality Gate governance enforcement (PRODUCTION_STRICT).
- REST API /ai/rca/remediate integration.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from agents import DefectRCAAgent
from quality_gate import PRESET_POLICIES
from regression_selector import select_regression_tests
from remediation import (
    SYNTHETIC_DEFECT_PATCHES,
    SyntheticCodePatch,
    execute_remediation_workflow,
    normalize_defect_id,
    synthesize_code_patch,
    validate_defect_resolution,
)


client = TestClient(app)


# --- 1. Patch Synthesis Tests (DEF-001 through DEF-005) ---
@pytest.mark.parametrize(
    "defect_id,expected_name,expected_file",
    [
        ("DEF-001", "FARE_CALCULATION_OVERCHARGE", "backend/app/routers/bookings.py"),
        ("DEF-002", "STALE_SEAT_INVENTORY", "backend/app/routers/bookings.py"),
        ("DEF-003", "PAYMENT_GATEWAY_TIMEOUT", "backend/app/routers/payments.py"),
        ("DEF-004", "RAG_UNGROUNDED_HALLUCINATION", "ai-engine/rag.py"),
        ("DEF-005", "SQL_INJECTION_VULNERABILITY", "backend/app/routers/bookings.py"),
    ],
)
def test_synthesize_code_patch_all_five_defects(defect_id, expected_name, expected_file):
    """Verify code patch synthesis produces complete, structured patches for DEF-001 through DEF-005."""
    patch = synthesize_code_patch(defect_id)
    assert patch.defect_id == defect_id
    assert patch.defect_name == expected_name
    assert patch.target_file == expected_file
    assert len(patch.description) > 10
    assert len(patch.original_snippet) > 5
    assert len(patch.patched_snippet) > 5
    assert len(patch.explanation) > 10
    assert "---" in patch.diff and "+++" in patch.diff


def test_defect_alias_normalization():
    """Verify alias identifiers (e.g. CALCULATION_DRIFT, OVERBOOKING_RACE) map cleanly to standard defect IDs."""
    assert normalize_defect_id("CALCULATION_DRIFT") == "DEF-001"
    assert normalize_defect_id("OVERBOOKING_RACE") == "DEF-002"
    assert normalize_defect_id("UPSTREAM_GATEWAY_TIMEOUT") == "DEF-003"
    assert normalize_defect_id("RAG_UNGROUNDED_HALLUCINATION") == "DEF-004"
    assert normalize_defect_id("SCHEMA_CONTRACT_VIOLATION") == "DEF-005"
    assert normalize_defect_id("def-001") == "DEF-001"


# --- 2. Defect Resolution Verification ---
def test_validate_defect_resolution_def001_fare_calculation():
    """Verify DEF-001 patch strictly eliminates fare calculation markup."""
    patch = synthesize_code_patch("DEF-001")
    resolved, details = validate_defect_resolution("DEF-001", patch)
    assert resolved is True
    assert "drift eliminated" in details.lower()


def test_validate_defect_resolution_def002_overbooking_race():
    """Verify DEF-002 patch enforces capacity validation and 409 Conflict."""
    patch = synthesize_code_patch("DEF-002")
    resolved, details = validate_defect_resolution("DEF-002", patch)
    assert resolved is True
    assert "409 conflict" in details.lower()


def test_validate_defect_resolution_def003_gateway_timeout():
    """Verify DEF-003 patch replaces unhandled 504 with resilient PENDING_RETRY."""
    patch = synthesize_code_patch("DEF-003")
    resolved, details = validate_defect_resolution("DEF-003", patch)
    assert resolved is True
    assert "pending_retry" in details.lower()


def test_validate_defect_resolution_def004_rag_hallucination():
    """Verify DEF-004 patch enforces similarity threshold and truthful refusal."""
    patch = synthesize_code_patch("DEF-004")
    resolved, details = validate_defect_resolution("DEF-004", patch)
    assert resolved is True
    assert "truthful refusal" in details.lower()


def test_validate_defect_resolution_def005_contract_completeness():
    """Verify DEF-005 patch enforces complete schema serialization with passenger_email."""
    patch = synthesize_code_patch("DEF-005")
    resolved, details = validate_defect_resolution("DEF-005", patch)
    assert resolved is True
    assert "passenger_email" in details.lower()


# --- 3. Regression Impact Planning & Execution ---
def test_regression_impact_selection_for_defect_patches():
    """Verify regression selector accurately maps defect patch target files to impacted test suites."""
    plan_def001 = select_regression_tests(["backend/app/routers/bookings.py"])
    assert "tests/api/test_bookings.py" in plan_def001.selected_test_files

    plan_def003 = select_regression_tests(["backend/app/routers/payments.py"])
    assert "tests/api/test_payments.py" in plan_def003.selected_test_files

    plan_def004 = select_regression_tests(["ai-engine/rag.py"])
    assert any("ai" in t or "rag" in t for t in plan_def004.selected_test_files)


# --- 4. Autonomous Remediation Workflow Tests ---
@pytest.mark.parametrize("defect_id", ["DEF-001", "DEF-002", "DEF-003", "DEF-004", "DEF-005"])
def test_remediation_workflow_verified_success(defect_id):
    """Verify complete remediation workflow resolves each defect and passes regression under Quality Gate."""
    result = execute_remediation_workflow(
        defect_id=defect_id,
        run_regression=True,
        policy_name="PRODUCTION_STRICT",
    )
    assert result.status == "VERIFIED_SUCCESS"
    assert result.defect_resolved is True
    assert result.regression_passed is True
    assert result.quality_gate_passed is True
    assert result.tests_executed > 0
    assert result.tests_failed == 0
    assert len(result.violations) == 0


def test_remediation_fails_when_defect_not_resolved():
    """Verify that an invalid patch that fails functional resolution is rejected."""
    flawed_patch = SyntheticCodePatch(
        defect_id="DEF-001",
        defect_name="FARE_CALCULATION_OVERCHARGE",
        target_file="backend/app/routers/bookings.py",
        category="Financial Calculation",
        description="Flawed patch that still overcharges",
        original_snippet="total = round(base_fare * 1.35 + 49.99 + ancillary_total, 2)",
        patched_snippet="total = round(base_fare * 1.50 + 99.00, 2)",  # Still flawed
        explanation="Does not fix arithmetic overcharge",
        diff="--- flawed diff",
    )
    resolved, details = validate_defect_resolution("DEF-001", flawed_patch)
    assert resolved is False


# --- 5. DefectRCAAgent Integration Tests ---
@pytest.mark.anyio
async def test_defect_rca_agent_execute_remediation():
    """Verify DefectRCAAgent plans, synthesizes patch, executes regression, and verifies remediation."""
    agent = DefectRCAAgent()
    run = await agent.execute(
        task="Remediate defect DEF-001 fare calculation overcharge",
        context={"remediate": True, "defect_id": "DEF-001"},
    )
    assert run.status == "COMPLETED"
    assert "Agentic Defect RCA Auto-Remediation: VERIFIED_SUCCESS" in run.output
    assert "DEF-001" in run.output
    assert "Target File" in run.output
    assert "Proposed Synthetic Code Patch" in run.output

    # Verify structured events emitted
    event_types = [e.event_type for e in run.events]
    assert "CONTEXT_INGESTION" in event_types
    assert "DEFECT_IDENTIFIED" in event_types
    assert "PATCH_SYNTHESIZED" in event_types
    assert "REGRESSION_EXECUTED" in event_types
    assert "QUALITY_GATE_EVALUATED" in event_types
    assert "REMEDIATION_VERIFIED" in event_types


@pytest.mark.anyio
async def test_defect_rca_agent_backward_compatibility_diagnostic_only():
    """Verify DefectRCAAgent preserves standard non-remediation diagnostic behavior."""
    agent = DefectRCAAgent()
    run = await agent.execute(
        task="Diagnose payment timeout error",
        context={"status_code": 504, "error_msg": "upstream gateway timeout"},
    )
    assert run.status == "COMPLETED"
    assert "RCA Diagnosis:" in run.output
    assert any(e.event_type == "RCA_DIAGNOSED" for e in run.events)
    # Remediation events should not be present
    assert not any(e.event_type == "PATCH_SYNTHESIZED" for e in run.events)


# --- 6. REST API Endpoint Integration Tests ---
def test_api_rca_remediate_endpoint_success():
    """Verify POST /ai/rca/remediate endpoint accepts request and returns verified remediation payload."""
    payload = {
        "defect_id": "DEF-001",
        "run_regression": True,
        "policy_name": "PRODUCTION_STRICT",
    }
    resp = client.post("/ai/rca/remediate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["defect_id"] == "DEF-001"
    assert data["status"] == "VERIFIED_SUCCESS"
    assert data["defect_resolved"] is True
    assert data["regression_passed"] is True
    assert data["quality_gate_passed"] is True
    assert "patch" in data
    assert data["patch"]["target_file"] == "backend/app/routers/bookings.py"
    assert "regression_plan" in data
    assert data["tests_executed"] > 0
    assert data["tests_failed"] == 0
