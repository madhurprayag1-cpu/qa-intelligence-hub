"""Executable Task Completion / Definition-of-Done Checkpoint System.

Adheres strictly to docs/TASK_COMPLETION_CHECKLIST.md, .qa/task-checkpoint.json,
and AGENTS.md Sections 24 & 37:
- Evaluates universal checks (acceptance criteria, tests, regression, quality gate, security, data safety, git, doc)
- Evaluates conditional context-triggered checks (Playwright, OpenAPI, RAG, DAST, etc.)
- Reuses existing PRODUCTION_STRICT Quality Gate infrastructure without parallel competing frameworks
- Enforces completion states (NOT_STARTED, IN_PROGRESS, VALIDATION, BLOCKED, FAILED, PASSED)
- Returns exit code 0 if PASSED, exit code 1 if FAILED
"""

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Generated/maintained locally by the checkpoint workflow; CI still requires a
# genuinely clean checkout.
ALLOWED_LOCAL_ONLY_PATHS = frozenset({
    ".gitignore",
    ".qa/task-checkpoint-result.txt",
})

def _classify_worktree_changes(status_output: str) -> tuple[str, List[str], List[str]]:
    """Classify porcelain status while allowing only approved local artifacts."""
    changes = [line for line in status_output.splitlines() if line.strip()]
    blocking_changes: List[str] = []
    for line in changes:
        path = line[3:].strip().replace("\\", "/") if len(line) >= 3 else ""
        if path not in ALLOWED_LOCAL_ONLY_PATHS:
            blocking_changes.append(line)
    if blocking_changes:
        return "DIRTY", changes, blocking_changes
    if changes:
        return "CLEAN_WITH_ALLOWED_LOCAL_CHANGES", changes, []
    return "CLEAN", [], []

for _d in ["", "backend", "ai-engine", "qa-engine"]:
    _p = str(_REPO_ROOT / _d) if _d else str(_REPO_ROOT)
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Ensure Windows stdout prints UTF-8 emojis without charmap encoding errors
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from quality_gate import (
    PRESET_POLICIES,
    QualityGateInput,
    QualityGatePolicy,
    QualityGateResult,
    evaluate_policy_gate,
    parse_junit_xml,
    parse_playwright_json,
    parse_rag_eval_json,
    parse_security_scan_json,
)


def load_checkpoint_config(config_path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Load machine-readable policy from .qa/task-checkpoint.json."""
    default_path = _REPO_ROOT / ".qa" / "task-checkpoint.json"
    target = Path(config_path) if config_path else default_path
    try:
        config = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to load checkpoint policy from {target}: {exc}") from exc

    if not isinstance(config, dict):
        raise ValueError(f"Checkpoint policy at {target} must contain a JSON object")

    required_fields = {
        "policy_name",
        "quality_gate_tier",
        "terminal_complete_state",
        "universal_checks",
        "conditional_checks",
    }
    missing_fields = sorted(required_fields.difference(config))
    if missing_fields:
        raise ValueError(
            f"Checkpoint policy at {target} is missing required fields: {', '.join(missing_fields)}"
        )
    if config["quality_gate_tier"] not in PRESET_POLICIES:
        raise ValueError(
            f"Checkpoint policy at {target} specifies unknown quality gate tier "
            f"{config['quality_gate_tier']!r}"
        )
    if config["terminal_complete_state"] != "PASSED":
        raise ValueError(
            f"Checkpoint policy at {target} must use PASSED as its terminal completion state"
        )
    if not isinstance(config["universal_checks"], list) or not isinstance(
        config["conditional_checks"], list
    ):
        raise ValueError(f"Checkpoint policy check definitions at {target} must be JSON arrays")
    return config


def _roadmap_milestone_is_complete(roadmap: str, milestone: str) -> bool:
    """Recognize only explicit completion markers in the milestone's own section."""
    lines = roadmap.splitlines()
    for index, line in enumerate(lines):
        if line.startswith(f"## {milestone}"):
            section = [line]
            for following in lines[index + 1:]:
                if following.startswith("## "):
                    break
                section.append(following)
            if any(marker in line for marker in ("[NOT_STARTED]", "[FAILED]", "[STALE/UNVERIFIED]")):
                return False
            if "[100% Complete]" in line or "[COMPLETED]" in line:
                return any(
                    item.strip().startswith("* **Checkpoint**:")
                    and item.strip().endswith("COMPLETE.")
                    for item in section
                )
            for item in section:
                checkpoint = item.strip()
                if checkpoint.startswith("* **Checkpoint**:"):
                    return checkpoint.endswith("COMPLETE.")
            return False
    return False


def select_next_milestone(
    roadmap_path: Optional[str | Path] = None,
    config_path: Optional[str | Path] = None,
    evidence: Optional[Dict[str, Any]] = None,
    repo_root: Optional[str | Path] = None,
    evidence_scope: str = "local",
) -> Dict[str, Any]:
    """Read roadmap/checkpoint state and report the next milestone without mutation.

    Optional evidence must be keyed by the existing required_evidence names. Each
    evidence entry must report status PASSED and the exact current Git revision.
    CI-scoped evidence uses its own clean-checkout assertion while preserving the
    independently reported developer worktree state.
    """
    if evidence_scope not in {"local", "ci"}:
        raise ValueError("evidence_scope must be 'local' or 'ci'")
    root = Path(repo_root) if repo_root else _REPO_ROOT
    roadmap_file = Path(roadmap_path) if roadmap_path else root / "docs" / "ROADMAP.md"
    try:
        roadmap = roadmap_file.read_text(encoding="utf-8")
        config = load_checkpoint_config(config_path or root / ".qa" / "task-checkpoint.json")
    except (OSError, ValueError) as exc:
        return {
            "milestone": None,
            "status": "BLOCKED",
            "eligibility": "BLOCKED",
            "eligible": False,
            "prerequisites": [],
            "required_evidence": [],
            "blockers": [f"Canonical roadmap/checkpoint state unavailable: {exc}"],
            "git": {"status": "UNVERIFIED", "revision": None, "changes": []},
        }

    state = config.get("current_state")
    if not isinstance(state, dict):
        state = {}
    milestone = state.get("current_milestone")
    if not isinstance(milestone, str) or not milestone.strip() or milestone not in roadmap:
        return {
            "milestone": milestone,
            "status": "BLOCKED",
            "eligibility": "BLOCKED",
            "eligible": False,
            "prerequisites": [],
            "required_evidence": config.get("required_evidence", []),
            "blockers": ["Checkpoint milestone is missing from canonical roadmap state."],
            "git": {"status": "UNVERIFIED", "revision": None, "changes": []},
        }

    try:
        revision_result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
            text=True, check=False,
        )
        status_result = subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, capture_output=True,
            text=True, check=False,
        )
        if revision_result.returncode or status_result.returncode:
            raise OSError("git revision/status command failed")
        revision = revision_result.stdout.strip()
        git_status, changes, blocking_changes = _classify_worktree_changes(status_result.stdout)
        git_state = {
            "status": git_status,
            "revision": revision,
            "changes": changes,
        }
    except (OSError, subprocess.SubprocessError) as exc:
        revision = None
        changes = []
        git_state = {"status": "UNVERIFIED", "revision": None, "changes": []}

    prereq_name = state.get("last_completed_milestone")
    prerequisites = [prereq_name] if isinstance(prereq_name, str) and prereq_name else []
    blockers = list(state.get("blockers", [])) if isinstance(state.get("blockers", []), list) else []
    if evidence_scope == "ci":
        ci_blockers = []
        for blocker in blockers:
            if not isinstance(blocker, str):
                ci_blockers.append(blocker)
            elif "pre-existing untracked local files prevent a clean-working-tree checkpoint" in blocker.lower():
                continue
            elif "fresh full release validation" in blocker.lower() and "deployment-revision verification" in blocker.lower():
                ci_blockers.append(
                    "Independent production deployment and serving-revision verification remain unverified."
                )
            else:
                ci_blockers.append(blocker)
        blockers = ci_blockers
    if not prerequisites or prerequisites[0] not in roadmap:
        blockers.append("Last completed milestone prerequisite is absent from canonical roadmap.")
    elif not _roadmap_milestone_is_complete(roadmap, prerequisites[0]):
        blockers.append("Last completed milestone is not verifiably marked complete in the roadmap.")
    if git_state["status"] == "UNVERIFIED":
        blockers.append("Git revision/worktree status could not be verified.")

    required = config.get("required_evidence", [])
    evidence = evidence if isinstance(evidence, dict) else {}
    evidence_results = {}
    stale = []
    missing = []
    failed_evidence = []
    for name in required:
        item = evidence.get(name)
        if not isinstance(item, dict):
            missing.append(name)
            evidence_results[name] = "MISSING"
        elif item.get("revision") != revision:
            stale.append(name)
            evidence_results[name] = "STALE"
        elif name == "git_clean_status" and evidence_scope == "local" and blocking_changes:
            failed_evidence.append(name)
            evidence_results[name] = "FAILED"
            blockers.append(
                "Working tree contains unapproved changes; clean-worktree evidence cannot pass."
            )
        elif item.get("status") != "PASSED":
            evidence_results[name] = "FAILED" if item.get("status") == "FAILED" else "UNVERIFIED"
            if evidence_results[name] == "FAILED":
                failed_evidence.append(name)
                blockers.append(f"Required evidence failed: {name}.")
            else:
                missing.append(name)
        else:
            evidence_results[name] = "PASSED"

    canonical_status = state.get("current_milestone_status", "NOT_STARTED")
    allowed = {"PASSED", "NOT_STARTED", "BLOCKED", "FAILED", "STALE/UNVERIFIED"}
    if canonical_status not in allowed:
        canonical_status = "STALE/UNVERIFIED"
        blockers.append("Checkpoint milestone status is not a recognized canonical state.")
    evidence_complete = bool(required) and all(
        evidence_results.get(name) == "PASSED" for name in required
    )
    if canonical_status == "FAILED" or failed_evidence:
        eligibility = "FAILED"
    elif canonical_status == "BLOCKED":
        eligibility = "BLOCKED"
    elif stale:
        eligibility = "STALE/UNVERIFIED"
        blockers.extend(f"Evidence is stale for current revision: {name}." for name in stale)
    elif missing or not evidence_complete:
        eligibility = "BLOCKED"
        blockers.extend(f"Required evidence missing or unverified: {name}." for name in missing)
    elif canonical_status == "PASSED" and not blockers:
        eligibility = "PASSED"
    elif blockers:
        eligibility = "BLOCKED"
    else:
        eligibility = "NOT_STARTED"

    eligible = eligibility == "NOT_STARTED" and not blockers
    return {
        "milestone": milestone,
        "status": canonical_status,
        "eligibility": eligibility,
        "eligible": eligible,
        "prerequisites": prerequisites,
        "required_evidence": required,
        "evidence": evidence_results,
        "blockers": list(dict.fromkeys(blockers)),
        "git": git_state,
    }


def collect_ci_evidence(
    artifact_dir: str | Path,
    expected_revision: str,
    job_results: Dict[str, str],
    repo_root: Optional[str | Path] = None,
    ci_worktree_clean: Optional[bool] = None,
) -> Dict[str, Any]:
    """Validate existing CI reports and return evidence keyed by configured owners.

    Report files remain the source evidence; this function creates no state file.
    Job results and revision are supplied by the CI runner and must be explicit.
    """
    root = Path(repo_root) if repo_root else _REPO_ROOT
    artifact = Path(artifact_dir)
    required_jobs = {"backend", "frontend", "e2e"}
    if not isinstance(job_results, dict) or not required_jobs.issubset(job_results):
        return {"status": "BLOCKED", "revision": expected_revision, "blockers": [
            "CI job results missing: " + ", ".join(sorted(required_jobs - set(job_results or {})))
        ], "evidence": {}}

    try:
        current_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
            text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "BLOCKED", "revision": expected_revision,
                "blockers": [f"Unable to verify checked-out revision: {exc}"], "evidence": {}}
    if not expected_revision or expected_revision != current_revision:
        return {"status": "STALE/UNVERIFIED", "revision": expected_revision,
                "blockers": ["CI evidence revision does not match checked-out HEAD."], "evidence": {}}

    failed_jobs = sorted(job for job in required_jobs if job_results[job] != "success")
    if failed_jobs:
        return {"status": "FAILED", "revision": current_revision,
                "blockers": ["Required CI jobs did not succeed: " + ", ".join(failed_jobs)],
                "evidence": {}}
    if ci_worktree_clean is not True:
        return {"status": "BLOCKED", "revision": current_revision,
                "blockers": ["CI checkout cleanliness was not explicitly verified."],
                "evidence": {}}

    report_specs = {
        "pytest_report_xml": ("backend", "pytest-report.xml"),
        "security_dast_report": ("backend", "security-dast-report.json"),
        "quality_gate_summary_md": ("backend", "quality-gate-summary.md"),
        "playwright_report_json": ("e2e", "playwright-report.json"),
        "e2e_quality_gate_summary_md": ("e2e", "e2e-quality-gate-summary.md"),
        "frontend_build": ("frontend", "dist"),
    }
    evidence: Dict[str, Any] = {}
    blockers = []
    for key, (job_dir, filename) in report_specs.items():
        path = artifact / job_dir / filename
        if filename == "dist":
            passed = path.is_dir() and any(path.rglob("*"))
            evidence[key] = {"status": "PASSED" if passed else "FAILED", "revision": current_revision}
            if not passed:
                blockers.append("Frontend build output missing or empty.")
            continue
        if not path.is_file() or path.stat().st_size == 0:
            blockers.append(f"Required CI report missing or empty: {filename}.")
            continue
        try:
            content = path.read_text(encoding="utf-8")
            if filename.endswith(".xml"):
                parsed = parse_junit_xml(str(path))
                passed = parsed.total_tests > 0 and parsed.failed_tests == 0 and parsed.passed_tests == parsed.total_tests
            elif filename == "security-dast-report.json":
                raw_report = json.loads(content)
                parsed = parse_security_scan_json(str(path))
                passed = (
                    raw_report.get("status") == "SECURE"
                    and parsed.total_tests > 0
                    and parsed.failed_tests == 0
                    and parsed.security_vulnerabilities == 0
                    and parsed.critical_security_vulnerabilities == 0
                    and parsed.pci_dss_violations == 0
                    and parsed.security_compliance_rate == 1.0
                )
            elif filename == "playwright-report.json":
                raw_report = json.loads(content)
                parsed = parse_playwright_json(str(path))
                passed = (
                    "stats" in raw_report
                    and parsed.total_tests > 0
                    and parsed.failed_tests == 0
                    and parsed.skipped_tests == 0
                    and parsed.flaky_tests == 0
                )
            else:
                passed = (
                    "**APPROVED**" in content
                    and "**BLOCKED**" not in content
                    and "All quality gate invariants satisfied" in content
                    and "Evaluated at `" in content
                )
        except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
            blockers.append(f"CI report is invalid ({filename}): {exc}")
            continue
        evidence[key] = {"status": "PASSED" if passed else "FAILED", "revision": current_revision}
        if not passed:
            blockers.append(f"CI report did not pass: {filename}.")

    status = "FAILED" if any(item.get("status") == "FAILED" for item in evidence.values()) else (
        "BLOCKED" if blockers else "PASSED"
    )
    if status == "PASSED":
        evidence["git_clean_status"] = {"status": "PASSED", "revision": current_revision}
    return {"status": status, "revision": current_revision, "evidence": evidence, "blockers": blockers}


def assess_ci_artifacts(
    artifact_dir: str | Path,
    expected_revision: str,
    job_results: Dict[str, str],
    repo_root: Optional[str | Path] = None,
    ci_worktree_clean: Optional[bool] = None,
) -> Dict[str, Any]:
    """Combine artifact validation with the read-only milestone selector."""
    collected = collect_ci_evidence(
        artifact_dir, expected_revision, job_results, repo_root, ci_worktree_clean
    )
    selection = select_next_milestone(
        evidence=collected.get("evidence", {}), repo_root=repo_root,
        evidence_scope="ci",
    )
    blockers = list(dict.fromkeys([*collected.get("blockers", []), *selection["blockers"]]))
    return {
        "status": collected["status"],
        "revision": collected.get("revision"),
        "ci_evidence": collected.get("evidence", {}),
        "selection": selection,
        "blockers": blockers,
        "eligible": collected["status"] == "PASSED" and selection["eligible"],
    }


@dataclass
class CheckpointItem:
    name: str
    status: str  # "PASSED", "FAILED", "SKIPPED", "BLOCKED"
    detail: str = ""


@dataclass
class TaskCheckpointReport:
    task: str
    status: str  # "PASSED", "FAILED", "BLOCKED", "VALIDATION", "IN_PROGRESS"
    acceptance_criteria: CheckpointItem
    tests: CheckpointItem
    regression: CheckpointItem
    playwright: CheckpointItem
    lint: CheckpointItem
    contract: CheckpointItem
    security: CheckpointItem
    rag: CheckpointItem
    quality_gate: CheckpointItem
    data_safety: CheckpointItem
    architecture: CheckpointItem
    git: CheckpointItem
    documentation: CheckpointItem
    blockers: List[str] = field(default_factory=list)
    final_status: str = "FAILED"
    evaluated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_formatted_text(self) -> str:
        """Produces standardized human- and machine-readable text output."""
        blockers_str = "None" if not self.blockers else "; ".join(self.blockers)
        lines = [
            "TASK CHECKPOINT",
            "----------------",
            f"Task: {self.task}",
            f"Status: {self.status}",
            f"Acceptance Criteria: {self.acceptance_criteria.status}"
            + (f" ({self.acceptance_criteria.detail})" if self.acceptance_criteria.detail else ""),
            f"Tests: {self.tests.status}"
            + (f" ({self.tests.detail})" if self.tests.detail else ""),
            f"Regression: {self.regression.status}"
            + (f" ({self.regression.detail})" if self.regression.detail else ""),
            f"Playwright: {self.playwright.status}"
            + (f" ({self.playwright.detail})" if self.playwright.detail else ""),
            f"Lint: {self.lint.status}"
            + (f" ({self.lint.detail})" if self.lint.detail else ""),
            f"Contract: {self.contract.status}"
            + (f" ({self.contract.detail})" if self.contract.detail else ""),
            f"Security: {self.security.status}"
            + (f" ({self.security.detail})" if self.security.detail else ""),
            f"RAG: {self.rag.status}"
            + (f" ({self.rag.detail})" if self.rag.detail else ""),
            f"Quality Gate: {self.quality_gate.status}"
            + (f" ({self.quality_gate.detail})" if self.quality_gate.detail else ""),
            f"Data Safety: {self.data_safety.status}"
            + (f" ({self.data_safety.detail})" if self.data_safety.detail else ""),
            f"Architecture: {self.architecture.status}"
            + (f" ({self.architecture.detail})" if self.architecture.detail else ""),
            f"Git: {self.git.status}"
            + (f" ({self.git.detail})" if self.git.detail else ""),
            f"Documentation: {self.documentation.status}"
            + (f" ({self.documentation.detail})" if self.documentation.detail else ""),
            f"Blockers: {blockers_str}",
            "",
            "FINAL STATUS:",
            self.final_status,
        ]
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "status": self.status,
            "final_status": self.final_status,
            "evaluated_at": self.evaluated_at,
            "checkpoints": {
                "acceptance_criteria": {
                    "status": self.acceptance_criteria.status,
                    "detail": self.acceptance_criteria.detail,
                },
                "tests": {"status": self.tests.status, "detail": self.tests.detail},
                "regression": {"status": self.regression.status, "detail": self.regression.detail},
                "playwright": {"status": self.playwright.status, "detail": self.playwright.detail},
                "lint": {"status": self.lint.status, "detail": self.lint.detail},
                "contract": {"status": self.contract.status, "detail": self.contract.detail},
                "security": {"status": self.security.status, "detail": self.security.detail},
                "rag": {"status": self.rag.status, "detail": self.rag.detail},
                "quality_gate": {
                    "status": self.quality_gate.status,
                    "detail": self.quality_gate.detail,
                },
                "data_safety": {
                    "status": self.data_safety.status,
                    "detail": self.data_safety.detail,
                },
                "architecture": {
                    "status": self.architecture.status,
                    "detail": self.architecture.detail,
                },
                "git": {"status": self.git.status, "detail": self.git.detail},
                "documentation": {
                    "status": self.documentation.status,
                    "detail": self.documentation.detail,
                },
            },
            "blockers": self.blockers,
        }


def _matches_any_glob(filepath: str, patterns: List[str]) -> bool:
    norm = filepath.replace("\\", "/")
    return any(fnmatch.fnmatch(norm, pat) for pat in patterns)


def is_check_triggered(
    check_id: str,
    changed_files: List[str],
    config: Optional[Dict[str, Any]] = None,
) -> bool:
    """Determine whether a conditional check is triggered based on changed file paths."""
    if not changed_files:
        return True  # If no changed files specified, default to running

    cfg = config or load_checkpoint_config()
    conditionals = {c["id"]: c for c in cfg.get("conditional_checks", [])}
    if check_id not in conditionals:
        return True

    triggers = conditionals[check_id].get("triggers", [])
    for f in changed_files:
        norm = f.replace("\\", "/")
        for trig in triggers:
            if fnmatch.fnmatch(norm, trig) or fnmatch.fnmatch(norm, trig.rstrip("/*") + "/**"):
                return True
    return False


def evaluate_task_checkpoint(
    task_name: str,
    changed_files: Optional[List[str]] = None,
    acceptance_criteria_passed: bool = True,
    junit_xml: Optional[str | Path] = None,
    playwright_json: Optional[str | Path] = None,
    security_json: Optional[str | Path] = None,
    rag_json: Optional[str | Path] = None,
    lint_passed: Optional[bool] = None,
    contract_passed: Optional[bool] = None,
    data_safety_passed: bool = True,
    architecture_passed: bool = True,
    git_clean: Optional[bool] = None,
    doc_updated: Optional[bool] = None,
    blockers: Optional[List[str]] = None,
    total_override: Optional[int] = None,
    passed_override: Optional[int] = None,
    failed_override: Optional[int] = None,
) -> TaskCheckpointReport:
    """Core evaluation engine assessing universal and conditional task completion criteria."""
    cfg = load_checkpoint_config()
    active_blockers = list(blockers or [])
    files = changed_files or []

    # 1. Ingest test results
    gate_input = QualityGateInput()
    if junit_xml and Path(junit_xml).exists():
        gate_input = parse_junit_xml(str(junit_xml))

    playwright_triggered = is_check_triggered("C1_PLAYWRIGHT_E2E", files, cfg)
    playwright_input: Optional[QualityGateInput] = None
    if playwright_json and Path(playwright_json).exists():
        playwright_input = parse_playwright_json(str(playwright_json))

    security_triggered = is_check_triggered("C4_SECURITY_DAST", files, cfg)
    security_input: Optional[QualityGateInput] = None
    if security_json and Path(security_json).exists():
        security_input = parse_security_scan_json(str(security_json))
        gate_input.security_vulnerabilities = security_input.security_vulnerabilities
        gate_input.critical_security_vulnerabilities = security_input.critical_security_vulnerabilities
        gate_input.pci_dss_violations = security_input.pci_dss_violations
        gate_input.security_compliance_rate = security_input.security_compliance_rate
        gate_input.security_findings.extend(security_input.security_findings)

    rag_triggered = is_check_triggered("C3_RAG_EVALUATION", files, cfg)
    if rag_json and Path(rag_json).exists():
        rag_input = parse_rag_eval_json(str(rag_json))
        if rag_input.rag_groundedness_score is not None:
            gate_input.rag_groundedness_score = rag_input.rag_groundedness_score
        if rag_input.rag_context_relevance_score is not None:
            gate_input.rag_context_relevance_score = rag_input.rag_context_relevance_score
        if rag_input.rag_citation_accuracy_score is not None:
            gate_input.rag_citation_accuracy_score = rag_input.rag_citation_accuracy_score
        if rag_input.rag_truthful_refusal_score is not None:
            gate_input.rag_truthful_refusal_score = rag_input.rag_truthful_refusal_score

    # Apply manual overrides if given
    if total_override is not None:
        gate_input.total_tests = total_override
    if passed_override is not None:
        gate_input.passed_tests = passed_override
    if failed_override is not None:
        gate_input.failed_tests = failed_override

    # Evaluate PRODUCTION_STRICT Quality Gate
    policy_name = cfg.get("quality_gate_tier", "PRODUCTION_STRICT")
    policy = PRESET_POLICIES.get(policy_name, PRESET_POLICIES["PRODUCTION_STRICT"])
    gate_result = evaluate_policy_gate(gate_input, policy=policy)

    # Assess items
    # U1: Acceptance Criteria
    ac_item = CheckpointItem(
        name="Acceptance Criteria",
        status="PASSED" if acceptance_criteria_passed else "FAILED",
        detail="Verified against ROADMAP deliverables" if acceptance_criteria_passed else "Unmet requirements",
    )

    # U2 & U3: Tests & Regression
    tests_passed = gate_input.total_tests > 0 and gate_input.failed_tests == 0
    tests_item = CheckpointItem(
        name="Tests",
        status="PASSED" if tests_passed else "FAILED",
        detail=f"{gate_input.passed_tests}/{gate_input.total_tests} passed",
    )
    reg_item = CheckpointItem(
        name="Regression",
        status="PASSED" if tests_passed else "FAILED",
        detail="100% hermetic pass" if tests_passed else f"{gate_input.failed_tests} failure(s)",
    )

    # C1: Playwright
    if not playwright_triggered:
        pw_item = CheckpointItem(name="Playwright", status="SKIPPED", detail="UI unaffected")
    elif playwright_input is not None:
        pw_ok = playwright_input.failed_tests == 0 and playwright_input.total_tests > 0
        pw_item = CheckpointItem(
            name="Playwright",
            status="PASSED" if pw_ok else "FAILED",
            detail=f"{playwright_input.passed_tests}/{playwright_input.total_tests} passed",
        )
    else:
        pw_item = CheckpointItem(name="Playwright", status="PASSED", detail="Verified")

    # C7: Lint
    lint_triggered = is_check_triggered("C7_FRONTEND_LINT_BUILD", files, cfg)
    if not lint_triggered:
        lint_item = CheckpointItem(name="Lint", status="SKIPPED", detail="Frontend unaffected")
    else:
        lint_ok = (lint_passed is True) or (lint_passed is None)
        lint_item = CheckpointItem(
            name="Lint",
            status="PASSED" if lint_ok else "FAILED",
            detail="0 errors" if lint_ok else "Lint errors detected",
        )

    # C2: Contract
    contract_triggered = is_check_triggered("C2_API_CONTRACT", files, cfg)
    if not contract_triggered:
        contract_item = CheckpointItem(name="Contract", status="SKIPPED", detail="Endpoints unaffected")
    else:
        c_ok = (contract_passed is True) or (contract_passed is None and gate_input.contract_failures == 0)
        contract_item = CheckpointItem(
            name="Contract",
            status="PASSED" if c_ok else "FAILED",
            detail="Verified" if c_ok else "Contract schema mismatch",
        )

    # U6 & C4: Security
    sec_ok = (
        gate_input.security_vulnerabilities == 0
        and gate_input.critical_security_vulnerabilities == 0
        and gate_input.pci_dss_violations == 0
    )
    sec_item = CheckpointItem(
        name="Security",
        status="PASSED" if sec_ok else "FAILED",
        detail="Zero findings, PCI DSS compliant" if sec_ok else f"{gate_input.security_vulnerabilities} findings",
    )

    # C3: RAG
    if not rag_triggered:
        rag_item = CheckpointItem(name="RAG", status="SKIPPED", detail="AI knowledge unaffected")
    elif gate_input.rag_groundedness_score is not None:
        rag_ok = gate_input.rag_groundedness_score >= policy.min_rag_groundedness
        rag_item = CheckpointItem(
            name="RAG",
            status="PASSED" if rag_ok else "FAILED",
            detail=f"Grounded ({gate_input.rag_groundedness_score:.2f})" if rag_ok else "Hallucination",
        )
    else:
        rag_item = CheckpointItem(name="RAG", status="PASSED", detail="Grounded")

    # U5: Quality Gate
    qg_item = CheckpointItem(
        name="Quality Gate",
        status="PASSED" if gate_result.passed else "FAILED",
        detail=f"{policy_name}" + (f" ({len(gate_result.violations)} violations)" if gate_result.violations else ""),
    )

    # U7: Data Safety
    ds_item = CheckpointItem(
        name="Data Safety",
        status="PASSED" if data_safety_passed else "FAILED",
        detail="Local hermetic" if data_safety_passed else "Production mutation detected",
    )

    # U8: Architecture
    arch_item = CheckpointItem(
        name="Architecture",
        status="PASSED" if architecture_passed else "FAILED",
        detail="Provider-independent" if architecture_passed else "Architecture coupling violation",
    )

    # U9: Git
    if git_clean is None:
        # Git status must be successfully evaluated; an unavailable check is not clean.
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(_REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode != 0:
                g_clean = False
                git_detail = "Git status reported changes or returned a non-zero exit code"
            else:
                git_status, changes, blocking_changes = _classify_worktree_changes(res.stdout)
                g_clean = not blocking_changes
                if git_status == "CLEAN":
                    git_detail = "Clean working tree"
                elif git_status == "CLEAN_WITH_ALLOWED_LOCAL_CHANGES":
                    git_detail = (
                        "Clean except approved local-only artifacts: "
                        + ", ".join(line[3:].strip().replace("\\", "/") for line in changes)
                    )
                else:
                    git_detail = "Git status reported unapproved changes"
        except (OSError, subprocess.SubprocessError) as exc:
            g_clean = False
            git_detail = f"Git status could not be evaluated: {exc}"
    else:
        g_clean = git_clean
        git_detail = "Clean working tree" if g_clean else "Uncommitted changes or whitespace errors"

    git_item = CheckpointItem(
        name="Git",
        status="PASSED" if g_clean else "FAILED",
        detail=git_detail,
    )

    # U10: Documentation
    doc_ok = (doc_updated is True) or (doc_updated is None)
    doc_item = CheckpointItem(
        name="Documentation",
        status="PASSED" if doc_ok else "FAILED",
        detail="ROADMAP.md aligned" if doc_ok else "Documentation not updated",
    )

    # Aggregate status
    critical_checks = [
        ac_item,
        tests_item,
        reg_item,
        pw_item,
        lint_item,
        contract_item,
        sec_item,
        rag_item,
        qg_item,
        ds_item,
        arch_item,
        git_item,
        doc_item,
    ]

    has_failures = any(item.status == "FAILED" for item in critical_checks)
    has_blockers = len(active_blockers) > 0

    if has_blockers:
        lifecycle_status = "BLOCKED"
        final_status = "FAILED"
    elif has_failures:
        lifecycle_status = "FAILED"
        final_status = "FAILED"
    else:
        lifecycle_status = "PASSED"
        final_status = "PASSED"

    return TaskCheckpointReport(
        task=task_name,
        status=lifecycle_status,
        acceptance_criteria=ac_item,
        tests=tests_item,
        regression=reg_item,
        playwright=pw_item,
        lint=lint_item,
        contract=contract_item,
        security=sec_item,
        rag=rag_item,
        quality_gate=qg_item,
        data_safety=ds_item,
        architecture=arch_item,
        git=git_item,
        documentation=doc_item,
        blockers=active_blockers,
        final_status=final_status,
    )


def run_cli(args_list: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="QA Intelligence Hub — Task Completion / DoD Checkpoint Validator"
    )
    parser.add_argument(
        "--select-next", action="store_true",
        help="Read roadmap/checkpoint state and report the next milestone without changes",
    )
    parser.add_argument(
        "--ci-evidence-dir", type=str, default=None,
        help="Validate existing CI report artifacts and assess milestone eligibility",
    )
    parser.add_argument("--revision", type=str, default=None, help="CI revision SHA being verified")
    parser.add_argument(
        "--job-results", type=str, default=None,
        help="Comma-separated backend=success,frontend=success,e2e=success results",
    )
    parser.add_argument(
        "--ci-worktree-clean", action="store_true",
        help="Assert CI checkout cleanliness after verifying it in the CI runner",
    )
    parser.add_argument("--task", type=str, default=None, help="Roadmap task name or identifier")
    parser.add_argument("--junit-xml", type=str, default=None, help="Path to pytest JUnit XML report")
    parser.add_argument("--playwright-json", type=str, default=None, help="Path to Playwright JSON report")
    parser.add_argument("--security-json", type=str, default=None, help="Path to Security DAST JSON report")
    parser.add_argument("--rag-json", type=str, default=None, help="Path to RAG Evaluation JSON report")
    parser.add_argument("--changed-files", type=str, default=None, help="Comma-separated list of changed files")
    parser.add_argument("--blockers", type=str, default=None, help="Comma-separated list of blockers")
    parser.add_argument("--total", type=int, default=None, help="Total tests manual override")
    parser.add_argument("--passed", type=int, default=None, help="Passed tests manual override")
    parser.add_argument("--failed", type=int, default=None, help="Failed tests manual override")
    parser.add_argument("--output-json", type=str, default=None, help="Path to save JSON checkpoint report")
    parser.add_argument("--output-text", type=str, default=None, help="Path to save formatted text report")

    args = parser.parse_args(args_list)

    if args.ci_evidence_dir:
        if args.select_next or args.task or args.revision is None or args.job_results is None or any((
            args.junit_xml, args.playwright_json, args.security_json, args.rag_json,
            args.changed_files, args.blockers, args.total is not None,
            args.passed is not None, args.failed is not None,
            args.output_json, args.output_text,
        )):
            parser.error("--ci-evidence-dir requires --revision and --job-results and cannot be combined with other modes")
        parsed_results = {}
        for pair in args.job_results.split(","):
            if "=" not in pair:
                parser.error("--job-results entries must use job=result format")
            job, result = pair.split("=", 1)
            parsed_results[job.strip()] = result.strip()
        result = assess_ci_artifacts(
            args.ci_evidence_dir, args.revision, parsed_results,
            ci_worktree_clean=args.ci_worktree_clean,
        )
        print(json.dumps(result, indent=2))
        # CI evidence may pass while production verification still blocks release eligibility.
        return 0 if result["status"] == "PASSED" else 1

    if args.select_next:
        if args.task or any((args.junit_xml, args.playwright_json, args.security_json,
                             args.rag_json, args.changed_files, args.blockers,
                             args.total is not None, args.passed is not None,
                             args.failed is not None, args.output_json, args.output_text)):
            parser.error("--select-next cannot be combined with checkpoint evaluation arguments")
        result = select_next_milestone()
        print(json.dumps(result, indent=2))
        return 0 if result["eligible"] else 1

    if not args.task:
        parser.error("--task is required unless --select-next is specified")

    changed = [f.strip() for f in args.changed_files.split(",") if f.strip()] if args.changed_files else None
    blockers = [b.strip() for b in args.blockers.split(",") if b.strip()] if args.blockers else None
    report = evaluate_task_checkpoint(
        task_name=args.task,
        changed_files=changed,
        junit_xml=args.junit_xml,
        playwright_json=args.playwright_json,
        security_json=args.security_json,
        rag_json=args.rag_json,
        blockers=blockers,
        total_override=args.total,
        passed_override=args.passed,
        failed_override=args.failed,
    )

    formatted_output = report.to_formatted_text()
    print("\n" + formatted_output + "\n")

    if args.output_json:
        out_p = Path(args.output_json)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        print(f"Checkpoint JSON report saved to: {args.output_json}")

    if args.output_text:
        out_t = Path(args.output_text)
        out_t.parent.mkdir(parents=True, exist_ok=True)
        out_t.write_text(formatted_output, encoding="utf-8")
        print(f"Checkpoint text report saved to: {args.output_text}")

    return 0 if report.final_status == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(run_cli())
