"""Unit tests for executable governance controls."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "qa-engine"))
from governance_controls import (
    authorize_action, classify_failure, coverage_gaps, evaluate_definition_of_done,
    validate_execution_policy, validate_healing_proposal, validate_test_data,
    validate_traceability,
)


def test_policy_defaults_and_boundaries():
    assert validate_execution_policy({}).passed
    assert validate_execution_policy({"retries": 3, "timeout_seconds": 600, "workers": 32}).passed


@pytest.mark.parametrize("policy", [
    {"retries": -1}, {"retries": 4}, {"timeout_seconds": 0},
    {"timeout_seconds": 601}, {"workers": 0}, {"workers": 33},
    {"allow_production_mutations": True},
])
def test_invalid_policy_fails_closed(policy):
    assert not validate_execution_policy(policy).passed


def test_production_mutation_denied_even_with_approval():
    assert not authorize_action("deploy", "production", "release-manager").passed
    assert authorize_action("inspect", "production").passed


def test_unknown_action_denied_and_approval_required():
    assert not authorize_action("arbitrary_shell", "test").passed
    assert not authorize_action("deploy", "staging").passed
    assert authorize_action("deploy", "staging", "reviewer").passed


def test_synthetic_data_required():
    assert validate_test_data({"synthetic": True, "fixture": "demo"}, "test").passed
    assert not validate_test_data({"synthetic": False}, "test").passed
    assert not validate_test_data({"synthetic": True, "api_key": "demo"}, "test").passed
    assert not validate_test_data({"synthetic": True}, "production").passed


def test_traceability_fails_for_unmapped_and_duplicate_requirements():
    result = validate_traceability(
        [{"id": "R1"}, {"id": "R2"}, {"id": "R1"}],
        [{"requirement_id": "R1", "enabled": True}],
    )
    assert not result.passed
    assert any("R2" in err for err in result.errors)
    assert any("duplicate" in err for err in result.errors)


def test_coverage_gap_detection():
    assert coverage_gaps(
        [{"id": "R1"}, {"id": "R2"}],
        [{"requirement_id": "R1", "enabled": True}],
    ) == ["R2"]


def test_healing_requires_review_and_safe_locator_proposal():
    good = {"change_type": "locator", "domain": "catalog", "confidence": 0.95,
            "human_approved": True, "auto_apply": False}
    assert validate_healing_proposal(good).passed
    assert not validate_healing_proposal({**good, "confidence": 0.8}).passed
    assert not validate_healing_proposal({**good, "domain": "payments"}).passed
    assert not validate_healing_proposal({**good, "auto_apply": True}).passed
    assert not validate_healing_proposal({**good, "human_approved": False}).passed


@pytest.mark.parametrize(("message", "status", "expected"), [
    ("request timed out", None, "TIMEOUT"),
    ("connection refused", None, "INFRASTRUCTURE"),
    ("expected 2 actual 3", None, "ASSERTION"),
    ("schema contract invalid", None, "CONTRACT"),
    ("element not found locator", None, "LOCATOR"),
    ("forbidden", 403, "AUTHORIZATION"),
    ("other", None, "UNKNOWN"),
])
def test_failure_categories(message, status, expected):
    assert classify_failure(message, status) == expected


def test_definition_of_done_requires_revision_bound_evidence():
    complete = {
        "tests_passed": True, "security_passed": True, "coverage_complete": True,
        "review_approved": True, "tested_revision": "abc", "release_revision": "abc",
        "critical_defects": 0, "evidence_uri": "evidence://run", "skipped_tests": 0,
    }
    assert evaluate_definition_of_done(complete).passed
    assert not evaluate_definition_of_done({**complete, "release_revision": "different"}).passed
    assert not evaluate_definition_of_done({**complete, "security_passed": False}).passed


def test_mcp_runtime_authorization_allows_read_only_tools_in_production():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ai-engine"))
    from mcp_server import authorize_mcp_tool

    assert authorize_mcp_tool("audit_security_vulnerabilities", "production").passed
    assert authorize_mcp_tool("generate_release_report", "production").passed
    assert authorize_mcp_tool("heal_playwright_selector", "production").passed


def test_mcp_runtime_authorization_fails_closed_for_unregistered_tools():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ai-engine"))
    from mcp_server import authorize_mcp_tool

    result = authorize_mcp_tool("arbitrary_shell_or_write", "production")
    assert not result.passed


def test_tool_registry_denies_production_writes_before_handler(monkeypatch):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "qa-engine"))
    from autonomous.contracts import AgentPermission
    from autonomous.tools import ToolRegistry

    monkeypatch.setenv("QA_ENVIRONMENT", "production")
    registry = ToolRegistry()
    read_result = registry.invoke(
        "repo_reader", AgentPermission.READ_ONLY, "test-agent", file_path="README.md"
    )
    assert read_result["status"] == "SUCCESS"

    catalog_result = registry.invoke(
        "catalog_tool", AgentPermission.READ_ONLY, "test-agent"
    )
    assert catalog_result["status"] == "PERMISSION_DENIED"

    file_result = registry.invoke(
        "file_editor", AgentPermission.READ_WRITE_BRANCH, "test-agent",
        file_path="should-not-be-created.txt", content="blocked",
    )
    assert file_result["status"] == "PERMISSION_DENIED"
    assert "prohibited" in file_result["error"]

    api_result = registry.invoke(
        "api_client", AgentPermission.RELEASE, "test-agent",
        method="POST", path="/health", json_data={},
    )
    assert api_result["status"] == "PERMISSION_DENIED"


def test_tool_registry_fails_closed_for_invalid_runtime_policy(monkeypatch):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "qa-engine"))
    from autonomous.contracts import AgentPermission
    from autonomous.tools import ToolRegistry

    monkeypatch.setenv("QA_TOOL_TIMEOUT_SECONDS", "0")
    result = ToolRegistry().invoke(
        "repo_reader", AgentPermission.READ_ONLY, "test-agent", file_path="README.md"
    )
    assert result["status"] == "PERMISSION_DENIED"
    assert "Invalid execution policy" in result["error"]


def test_orchestrator_rejects_invalid_timeout_before_subprocess(monkeypatch, tmp_path):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "qa-engine"))
    from orchestrator import ExecutionAgent

    monkeypatch.setenv("QA_ORCHESTRATOR_TIMEOUT_SECONDS", "0")
    report_path = tmp_path / "pytest-report.xml"
    code, output = ExecutionAgent().run_pytest(report_path)
    assert code != 0
    assert "Execution policy rejected" in output
    assert "timeout_seconds must be between 1 and 600" in output
    assert not report_path.exists()
