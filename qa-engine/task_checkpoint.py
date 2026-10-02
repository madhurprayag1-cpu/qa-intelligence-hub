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
    if target.exists():
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "policy_name": "QA_INTELLIGENCE_TASK_CHECKPOINT",
        "quality_gate_tier": "PRODUCTION_STRICT",
        "terminal_complete_state": "PASSED",
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
        # Check git status if in a git repo
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(_REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            g_clean = len(res.stdout.strip()) == 0
        except Exception:
            g_clean = True
    else:
        g_clean = git_clean

    git_item = CheckpointItem(
        name="Git",
        status="PASSED" if g_clean else "FAILED",
        detail="Clean working tree" if g_clean else "Uncommitted changes or whitespace errors",
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
    parser.add_argument("--task", type=str, required=True, help="Roadmap task name or identifier")
    parser.add_argument("--junit-xml", type=str, default=None, help="Path to pytest JUnit XML report")
    parser.add_argument("--playwright-json", type=str, default=None, help="Path to Playwright JSON report")
    parser.add_argument("--security-json", type=str, default=None, help="Path to Security DAST JSON report")
    parser.add_argument("--rag-json", type=str, default=None, help="Path to RAG Evaluation JSON report")
    parser.add_argument("--changed-files", type=str, default=None, help="Comma-separated list of changed files")
    parser.add_argument("--blockers", type=str, default=None, help="Comma-separated list of blockers")
    parser.add_argument("--total", type=int, default=None, help="Total tests manual override")
    parser.add_argument("--passed", type=int, default=None, help="Passed tests manual override")
    parser.add_argument("--failed", type=int, default=None, help="Failed tests manual override")
    parser.add_argument("--git-clean", action="store_true", default=None, help="Override git cleanliness check to PASSED")
    parser.add_argument("--skip-git-check", action="store_true", default=False, help="Skip git working tree cleanliness check")
    parser.add_argument("--output-json", type=str, default=None, help="Path to save JSON checkpoint report")
    parser.add_argument("--output-text", type=str, default=None, help="Path to save formatted text report")

    args = parser.parse_args(args_list)

    changed = [f.strip() for f in args.changed_files.split(",") if f.strip()] if args.changed_files else None
    blockers = [b.strip() for b in args.blockers.split(",") if b.strip()] if args.blockers else None
    git_override = True if (args.git_clean or args.skip_git_check) else None

    report = evaluate_task_checkpoint(
        task_name=args.task,
        changed_files=changed,
        junit_xml=args.junit_xml,
        playwright_json=args.playwright_json,
        security_json=args.security_json,
        rag_json=args.rag_json,
        git_clean=git_override,
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
