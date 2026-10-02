"""Tests for Task Completion & Definition-of-Done Checkpoint System.

Adheres to docs/TASK_COMPLETION_CHECKLIST.md and .qa/task-checkpoint.json:
- Validates machine-readable policy loading
- Validates context-triggered conditional check resolution
- Validates universal check verification (acceptance criteria, tests, regression, security, data safety, git, docs)
- Validates quality gate enforcement under PRODUCTION_STRICT tier
- Validates blocker handling and terminal completion states
- Validates structured report text formatting and CLI entrypoints
"""

import json
import sys
from pathlib import Path
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "qa-engine") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "qa-engine"))

from cli_gate import run_cli as run_gate_cli
from quality_gate import QualityGateInput
from task_checkpoint import (
    CheckpointItem,
    TaskCheckpointReport,
    evaluate_task_checkpoint,
    is_check_triggered,
    load_checkpoint_config,
    run_cli as run_checkpoint_cli,
)


def test_load_checkpoint_config():
    """Verify loading machine-readable policy from .qa/task-checkpoint.json."""
    config = load_checkpoint_config()
    assert config["policy_name"] == "QA_INTELLIGENCE_TASK_CHECKPOINT"
    assert config["quality_gate_tier"] == "PRODUCTION_STRICT"
    assert config["terminal_complete_state"] == "PASSED"
    assert "universal_checks" in config
    assert "conditional_checks" in config

    u_ids = {c["id"] for c in config["universal_checks"]}
    assert "U1_ACCEPTANCE_CRITERIA" in u_ids
    assert "U5_QUALITY_GATE" in u_ids
    assert "U6_SECURITY_REGRESSION" in u_ids
    assert "U7_DATA_SAFETY" in u_ids


def test_conditional_trigger_mapping():
    """Verify conditional check triggers accurately map changed files."""
    config = load_checkpoint_config()

    # Frontend file should trigger Playwright and Frontend Lint
    frontend_files = ["frontend/src/App.tsx", "frontend/src/types.ts"]
    assert is_check_triggered("C1_PLAYWRIGHT_E2E", frontend_files, config) is True
    assert is_check_triggered("C7_FRONTEND_LINT_BUILD", frontend_files, config) is True
    assert is_check_triggered("C3_RAG_EVALUATION", frontend_files, config) is False

    # Documentation file should NOT trigger Playwright or Lint
    doc_files = ["docs/ROADMAP.md", "README.md"]
    assert is_check_triggered("C1_PLAYWRIGHT_E2E", doc_files, config) is False
    assert is_check_triggered("C7_FRONTEND_LINT_BUILD", doc_files, config) is False

    # AI engine file should trigger RAG evaluation
    ai_files = ["ai-engine/rag.py"]
    assert is_check_triggered("C3_RAG_EVALUATION", ai_files, config) is True

    # Backend router should trigger Contract and DAST checks
    backend_files = ["backend/app/routers/bookings.py"]
    assert is_check_triggered("C2_API_CONTRACT", backend_files, config) is True
    assert is_check_triggered("C4_SECURITY_DAST", backend_files, config) is True


def test_checkpoint_evaluation_passed():
    """Verify evaluate_task_checkpoint passes when all universal checks are satisfied."""
    report = evaluate_task_checkpoint(
        task_name="Task 6.5: Automated Continuous Security Scanning (DAST) Gate",
        changed_files=["docs/ROADMAP.md"],
        acceptance_criteria_passed=True,
        total_override=50,
        passed_override=50,
        failed_override=0,
        git_clean=True,
        doc_updated=True,
    )

    assert report.final_status == "PASSED"
    assert report.status == "PASSED"
    assert report.acceptance_criteria.status == "PASSED"
    assert report.tests.status == "PASSED"
    assert report.regression.status == "PASSED"
    assert report.quality_gate.status == "PASSED"
    assert report.security.status == "PASSED"
    assert report.git.status == "PASSED"
    assert report.documentation.status == "PASSED"
    assert len(report.blockers) == 0


def test_checkpoint_evaluation_failed_on_unmet_acceptance_criteria():
    """Verify task checkpoint fails if acceptance criteria are unmet."""
    report = evaluate_task_checkpoint(
        task_name="Task 7.1: Healthcare Domain Pack",
        acceptance_criteria_passed=False,
        total_override=50,
        passed_override=50,
        failed_override=0,
        git_clean=True,
    )

    assert report.final_status == "FAILED"
    assert report.status == "FAILED"
    assert report.acceptance_criteria.status == "FAILED"


def test_checkpoint_evaluation_failed_on_test_failures():
    """Verify task checkpoint fails if any automated tests fail."""
    report = evaluate_task_checkpoint(
        task_name="Task 6.5: Security Scanning",
        acceptance_criteria_passed=True,
        total_override=50,
        passed_override=48,
        failed_override=2,
        git_clean=True,
    )

    assert report.final_status == "FAILED"
    assert report.status == "FAILED"
    assert report.tests.status == "FAILED"
    assert report.regression.status == "FAILED"
    assert report.quality_gate.status == "FAILED"


def test_checkpoint_evaluation_failed_on_security_vulnerability(tmp_path):
    """Verify task checkpoint fails if security DAST scan finds vulnerabilities."""
    vuln_dast = {
        "status": "VULNERABLE",
        "total_scans": 5,
        "passed_scans": 4,
        "failed_scans": 1,
        "vulnerabilities_count": 1,
        "critical_vulnerabilities": 1,
        "pci_dss_violations": 1,
        "compliance_rate": 0.8,
        "findings": [
            {
                "category": "PCI_DSS_EXPOSURE",
                "severity": "CRITICAL",
                "location": "card_number",
                "description": "Unmasked PAN",
                "remediation": "Mask PAN",
            }
        ],
    }
    sec_file = tmp_path / "sec_vuln.json"
    sec_file.write_text(json.dumps(vuln_dast), encoding="utf-8")

    report = evaluate_task_checkpoint(
        task_name="Task 6.5: Security Scanning",
        security_json=sec_file,
        total_override=50,
        passed_override=50,
        failed_override=0,
        git_clean=True,
    )

    assert report.final_status == "FAILED"
    assert report.status == "FAILED"
    assert report.security.status == "FAILED"
    assert report.quality_gate.status == "FAILED"


def test_checkpoint_evaluation_blocked_on_active_blockers():
    """Verify task checkpoint sets status BLOCKED when external blockers exist."""
    report = evaluate_task_checkpoint(
        task_name="Task 7.1: Healthcare Domain Pack",
        acceptance_criteria_passed=True,
        total_override=50,
        passed_override=50,
        failed_override=0,
        blockers=["Upstream HL7 FHIR validator service unavailable"],
        git_clean=True,
    )

    assert report.final_status == "FAILED"
    assert report.status == "BLOCKED"
    assert len(report.blockers) == 1


def test_to_formatted_text_output_structure():
    """Verify to_formatted_text produces the exact expected structured report."""
    item_pass = CheckpointItem(name="Acceptance Criteria", status="PASSED", detail="Verified")
    report = TaskCheckpointReport(
        task="Task 6.5: Automated Continuous Security Scanning (DAST) Gate",
        status="PASSED",
        acceptance_criteria=item_pass,
        tests=CheckpointItem(name="Tests", status="PASSED", detail="248/248 passed"),
        regression=CheckpointItem(name="Regression", status="PASSED", detail="100% hermetic pass"),
        playwright=CheckpointItem(name="Playwright", status="PASSED", detail="17/17 passed"),
        lint=CheckpointItem(name="Lint", status="PASSED", detail="0 errors"),
        contract=CheckpointItem(name="Contract", status="PASSED", detail="Verified"),
        security=CheckpointItem(name="Security", status="PASSED", detail="Zero findings, PCI DSS compliant"),
        rag=CheckpointItem(name="RAG", status="PASSED", detail="Grounded"),
        quality_gate=CheckpointItem(name="Quality Gate", status="PASSED", detail="PRODUCTION_STRICT"),
        data_safety=CheckpointItem(name="Data Safety", status="PASSED", detail="Local hermetic"),
        architecture=CheckpointItem(name="Architecture", status="PASSED", detail="Provider-independent"),
        git=CheckpointItem(name="Git", status="PASSED", detail="Clean working tree"),
        documentation=CheckpointItem(name="Documentation", status="PASSED", detail="ROADMAP.md aligned"),
        blockers=[],
        final_status="PASSED",
    )

    output = report.to_formatted_text()
    assert "TASK CHECKPOINT" in output
    assert "Task: Task 6.5: Automated Continuous Security Scanning (DAST) Gate" in output
    assert "Status: PASSED" in output
    assert "Acceptance Criteria: PASSED (Verified)" in output
    assert "Tests: PASSED (248/248 passed)" in output
    assert "Regression: PASSED (100% hermetic pass)" in output
    assert "Playwright: PASSED (17/17 passed)" in output
    assert "Lint: PASSED (0 errors)" in output
    assert "Contract: PASSED (Verified)" in output
    assert "Security: PASSED (Zero findings, PCI DSS compliant)" in output
    assert "RAG: PASSED (Grounded)" in output
    assert "Quality Gate: PASSED (PRODUCTION_STRICT)" in output
    assert "Data Safety: PASSED (Local hermetic)" in output
    assert "Architecture: PASSED (Provider-independent)" in output
    assert "Git: PASSED (Clean working tree)" in output
    assert "Documentation: PASSED (ROADMAP.md aligned)" in output
    assert "Blockers: None" in output
    assert "FINAL STATUS:" in output
    assert output.strip().endswith("PASSED")


def test_checkpoint_cli_execution_passed(tmp_path):
    """Verify run_cli returns exit code 0 when checkpoint passes."""
    out_json = tmp_path / "checkpoint.json"
    out_txt = tmp_path / "checkpoint.txt"

    args = [
        "--task", "Task 6.5: DAST Gate",
        "--total", "100",
        "--passed", "100",
        "--failed", "0",
        "--skip-git-check",
        "--output-json", str(out_json),
        "--output-text", str(out_txt),
    ]
    exit_code = run_checkpoint_cli(args)
    assert exit_code == 0
    assert out_json.exists()
    assert out_txt.exists()

    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["final_status"] == "PASSED"
    assert "TASK CHECKPOINT" in out_txt.read_text(encoding="utf-8")


def test_checkpoint_cli_execution_failed():
    """Verify run_cli returns exit code 1 when checkpoint fails."""
    args = [
        "--task", "Task 6.5: DAST Gate",
        "--total", "100",
        "--passed", "95",
        "--failed", "5",
        "--skip-git-check",
    ]
    exit_code = run_checkpoint_cli(args)
    assert exit_code == 1


def test_cli_gate_integration_with_task_checkpoint():
    """Verify qa-engine/cli_gate.py --task-checkpoint executes the DoD checkpoint."""
    args = [
        "--task-checkpoint", "Task 6.5: DAST Gate",
        "--total", "100",
        "--passed", "100",
        "--failed", "0",
        "--skip-git-check",
    ]
    exit_code = run_gate_cli(args)
    assert exit_code == 0
