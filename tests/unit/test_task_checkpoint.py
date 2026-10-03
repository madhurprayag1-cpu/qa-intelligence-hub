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
    select_next_milestone,
    assess_ci_artifacts,
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


@pytest.mark.parametrize("contents", ["{invalid json", "[]", '{"policy_name": "incomplete"}'])
def test_load_checkpoint_config_fails_closed_for_invalid_policy(tmp_path, contents):
    config_path = tmp_path / "task-checkpoint.json"
    config_path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError, match="Unable to load|must contain|required fields"):
        load_checkpoint_config(config_path)


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


def test_checkpoint_cli_execution_passed(tmp_path, monkeypatch):
    """Verify run_cli returns exit code 0 when checkpoint passes."""
    out_json = tmp_path / "checkpoint.json"
    out_txt = tmp_path / "checkpoint.txt"

    class CleanGitResult:
        returncode = 0
        stdout = ""

    monkeypatch.setattr("task_checkpoint.subprocess.run", lambda *args, **kwargs: CleanGitResult())
    args = [
        "--task", "Task 6.5: DAST Gate",
        "--total", "100",
        "--passed", "100",
        "--failed", "0",
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
    ]
    exit_code = run_gate_cli(args)
    assert exit_code == 1
    with pytest.raises(SystemExit) as exc_info:
        run_gate_cli(["--task-checkpoint", "No git bypass", "--skip-git-check"])
    assert exc_info.value.code == 2


def test_checkpoint_fails_when_git_status_cannot_be_evaluated(monkeypatch):
    def raise_git_unavailable(*args, **kwargs):
        raise FileNotFoundError("git executable unavailable")

    monkeypatch.setattr("task_checkpoint.subprocess.run", raise_git_unavailable)
    report = evaluate_task_checkpoint(
        task_name="Git failure behavior",
        changed_files=["docs/ROADMAP.md"],
        total_override=10,
        passed_override=10,
        failed_override=0,
    )

    assert report.git.status == "FAILED"
    assert "could not be evaluated" in report.git.detail
    assert report.final_status == "FAILED"


def test_checkpoint_fails_when_git_status_returns_error(monkeypatch):
    class FailedGitResult:
        returncode = 128
        stdout = ""

    monkeypatch.setattr("task_checkpoint.subprocess.run", lambda *args, **kwargs: FailedGitResult())
    report = evaluate_task_checkpoint(
        task_name="Git non-zero behavior",
        changed_files=["docs/ROADMAP.md"],
        total_override=10,
        passed_override=10,
        failed_override=0,
    )

    assert report.git.status == "FAILED"
    assert report.final_status == "FAILED"


def test_checkpoint_cli_does_not_accept_git_skip_option():
    with pytest.raises(SystemExit) as exc_info:
        run_checkpoint_cli(["--task", "No git bypass", "--skip-git-check"])

    assert exc_info.value.code == 2


def _selector_fixture(tmp_path, monkeypatch, *, status_output="", evidence=None, blockers=None):
    root = tmp_path
    (root / "docs").mkdir()
    (root / ".qa").mkdir()
    roadmap = "## Phase 1 — Previous [100% Complete]\n* **Checkpoint**: COMPLETE.\n\n## Release Preparation & Deployment Verification\n"
    (root / "docs" / "ROADMAP.md").write_text(roadmap, encoding="utf-8")
    config = {
        "policy_name": "QA_INTELLIGENCE_TASK_CHECKPOINT",
        "quality_gate_tier": "PRODUCTION_STRICT",
        "terminal_complete_state": "PASSED",
        "universal_checks": [],
        "conditional_checks": [],
        "required_evidence": ["pytest_report_xml", "quality_gate_summary_md", "git_clean_status"],
        "current_state": {
            "current_milestone": "Release Preparation & Deployment Verification",
            "current_milestone_status": "NOT_STARTED",
            "last_completed_milestone": "Phase 1 — Previous",
            "blockers": blockers or [],
        },
    }
    config_path = root / ".qa" / "task-checkpoint.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    class GitResult:
        returncode = 0
        stdout = "a" * 40 + "\n"

    class StatusResult:
        returncode = 0
        stdout = status_output

    def fake_run(args, **kwargs):
        return GitResult() if args[1] == "rev-parse" else StatusResult()

    monkeypatch.setattr("task_checkpoint.subprocess.run", fake_run)
    result = select_next_milestone(
        roadmap_path=root / "docs" / "ROADMAP.md",
        config_path=config_path,
        repo_root=root,
        evidence=evidence,
    )
    return result, config_path


def test_selector_current_release_milestone_is_not_started_and_blocked_without_evidence(tmp_path, monkeypatch):
    result, _ = _selector_fixture(tmp_path, monkeypatch)
    assert result["milestone"] == "Release Preparation & Deployment Verification"
    assert result["status"] == "NOT_STARTED"
    assert result["eligibility"] == "BLOCKED"
    assert result["eligible"] is False


def test_selector_missing_evidence_is_blocked(tmp_path, monkeypatch):
    result, _ = _selector_fixture(tmp_path, monkeypatch)
    assert result["eligibility"] == "BLOCKED"
    assert all(value == "MISSING" for value in result["evidence"].values())


def test_selector_stale_evidence_is_not_eligible(tmp_path, monkeypatch):
    evidence = {
        key: {"status": "PASSED", "revision": "old-revision"}
        for key in ("pytest_report_xml", "quality_gate_summary_md", "git_clean_status")
    }
    result, _ = _selector_fixture(tmp_path, monkeypatch, evidence=evidence)
    assert result["eligibility"] == "STALE/UNVERIFIED"
    assert result["eligible"] is False


def test_selector_valid_prerequisites_and_revision_evidence_are_eligible(tmp_path, monkeypatch):
    evidence = {
        key: {"status": "PASSED", "revision": "a" * 40}
        for key in ("pytest_report_xml", "quality_gate_summary_md", "git_clean_status")
    }
    result, _ = _selector_fixture(tmp_path, monkeypatch, evidence=evidence)
    assert result["eligibility"] == "NOT_STARTED"
    assert result["eligible"] is True


def test_selector_reports_dirty_worktree_without_modifying_it(tmp_path, monkeypatch):
    dirty = " M .gitignore\n?? .qa/local-report.txt\n"
    result, config_path = _selector_fixture(tmp_path, monkeypatch, status_output=dirty)
    original_config = config_path.read_text(encoding="utf-8")
    assert result["git"]["status"] == "DIRTY"
    assert result["git"]["changes"] == dirty.splitlines()
    assert config_path.exists()
    assert config_path.read_text(encoding="utf-8") == original_config
    assert result["eligibility"] == "BLOCKED"


def test_selector_does_not_accept_unrevisioned_or_inferred_evidence(tmp_path, monkeypatch):
    evidence = {
        "pytest_report_xml": {"status": "PASSED", "revision": "a" * 40},
        "quality_gate_summary_md": {"status": "PASSED"},
        "git_clean_status": {"status": "PASSED", "revision": "a" * 40},
    }
    result, _ = _selector_fixture(tmp_path, monkeypatch, evidence=evidence)
    assert result["evidence"]["quality_gate_summary_md"] == "STALE"
    assert result["eligible"] is False


@pytest.mark.parametrize(
    ("marker", "complete"),
    [
        ("[100% Complete]", True),
        ("[COMPLETED]", True),
        ("[NOT_STARTED]", False),
        ("[FAILED]", False),
        ("[STALE/UNVERIFIED]", False),
        ("", False),
    ],
)
def test_selector_prerequisite_requires_explicit_roadmap_completion(tmp_path, monkeypatch, marker, complete):
    _selector_fixture(tmp_path, monkeypatch)
    roadmap_path = tmp_path / "docs" / "ROADMAP.md"
    roadmap = roadmap_path.read_text(encoding="utf-8")
    roadmap_path.write_text(
        roadmap.replace("Phase 1 — Previous [100% Complete]", f"Phase 1 — Previous {marker}")
        .replace("* **Checkpoint**: COMPLETE.", "* **Checkpoint**: COMPLETE." if complete else "* **Checkpoint**: NOT_STARTED."),
        encoding="utf-8",
    )
    result = select_next_milestone(
        roadmap_path=roadmap_path,
        config_path=tmp_path / ".qa" / "task-checkpoint.json",
        repo_root=tmp_path,
        evidence={
            key: {"status": "PASSED", "revision": "a" * 40}
            for key in ("pytest_report_xml", "quality_gate_summary_md", "git_clean_status")
        },
    )
    prerequisite_blocked = any("not verifiably marked complete" in blocker for blocker in result["blockers"])
    assert prerequisite_blocked is (not complete)


def test_ci_evidence_requires_all_reports_and_successful_jobs(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    artifact = tmp_path / "artifacts"
    (artifact / "backend").mkdir(parents=True)
    (artifact / "e2e").mkdir()
    (artifact / "frontend" / "dist").mkdir(parents=True)
    (artifact / "frontend" / "dist" / "index.html").write_text("built", encoding="utf-8")
    revision = "b" * 40

    class GitResult:
        returncode = 0
        stdout = revision + "\n"

    class StatusResult:
        returncode = 0
        stdout = ""

    monkeypatch.setattr(
        "task_checkpoint.subprocess.run",
        lambda args, **kwargs: GitResult() if args[1] == "rev-parse" else StatusResult(),
    )
    (artifact / "backend" / "pytest-report.xml").write_text(
        '<testsuites tests="1" failures="0" errors="0" skipped="0"/>', encoding="utf-8"
    )
    (artifact / "backend" / "security-dast-report.json").write_text(
        json.dumps({"status": "SECURE", "total_scans": 1, "passed_scans": 1,
                    "failed_scans": 0, "vulnerabilities_count": 0,
                    "critical_vulnerabilities": 0, "pci_dss_violations": 0,
                    "compliance_rate": 1.0, "findings": []}), encoding="utf-8"
    )
    approved_summary = "APPROVED\n| evaluated | Evaluated at `now` |"
    (artifact / "backend" / "quality-gate-summary.md").write_text(
        "### 🛡️ Release Quality Gate: 🟢 **APPROVED** (`PRODUCTION_STRICT` Policy)\n"
        "All quality gate invariants satisfied.\n" + approved_summary,
        encoding="utf-8",
    )
    (artifact / "e2e" / "playwright-report.json").write_text(
        json.dumps({"stats": {"expected": 1, "unexpected": 0, "skipped": 0, "flaky": 0}}), encoding="utf-8"
    )
    (artifact / "e2e" / "e2e-quality-gate-summary.md").write_text(
        "### 🛡️ Release Quality Gate: 🟢 **APPROVED** (`PRODUCTION_STRICT` Policy)\n"
        "All quality gate invariants satisfied.\n" + approved_summary,
        encoding="utf-8",
    )
    jobs = {"backend": "success", "frontend": "success", "e2e": "success"}
    result = assess_ci_artifacts(artifact, revision, jobs, repo_root=root)
    assert result["status"] == "PASSED"
    assert set(result["ci_evidence"]) >= {"pytest_report_xml", "quality_gate_summary_md"}

    (artifact / "e2e" / "e2e-quality-gate-summary.md").unlink()
    partial = assess_ci_artifacts(artifact, revision, jobs, repo_root=root)
    assert partial["status"] == "BLOCKED"
    stale = assess_ci_artifacts(artifact, "c" * 40, jobs, repo_root=root)
    assert stale["status"] == "STALE/UNVERIFIED"
    failed = assess_ci_artifacts(artifact, revision, {**jobs, "frontend": "failure"}, repo_root=root)
    assert failed["status"] == "FAILED"
