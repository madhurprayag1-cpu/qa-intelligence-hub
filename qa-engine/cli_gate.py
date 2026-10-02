"""Quality Gate CLI & PR Governance Evaluator.

Adheres to AGENTS.md Section 23 & 24:
- Evaluates CI test reports (JUnit XML, Playwright JSON) and multi-signal telemetry
- Enforces configurable release policies (PRODUCTION_STRICT, STAGING_STANDARD, DEV_PR_FAST)
- Formats rich GitHub PR markdown reports
- Returns deterministic exit codes (0 = APPROVED, 1 = BLOCKED)
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Ensure parent directory is in sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "qa-engine") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "qa-engine"))

from quality_gate import (
    PRESET_POLICIES,
    QualityGateInput,
    QualityGateResult,
    evaluate_policy_gate,
    parse_junit_xml,
    parse_playwright_json,
    parse_rag_eval_json,
    parse_security_scan_json,
)

# Ensure Windows stdout prints UTF-8 emojis without charmap encoding errors
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _format_rag_row(
    label: str,
    score: Optional[float],
    min_threshold: float,
    pass_label: str = "Pass",
    fail_label: str = "Fail",
) -> str:
    if score is None:
        return f"| **{label}** | `N/A` | >= {min_threshold:.2f} | ⚪ N/A |"
    passed = score >= min_threshold
    status = f"✅ {pass_label}" if passed else f"❌ {fail_label}"
    return f"| **{label}** | `{score:.2f}` | >= {min_threshold:.2f} | {status} |"


def generate_pr_markdown_report(result: QualityGateResult) -> str:
    """Formats an executive GitHub Flavored Markdown comment for Pull Requests."""
    verdict_badge = "🟢 **APPROVED**" if result.passed else "🔴 **BLOCKED**"
    headline = (
        "### 🛡️ Release Quality Gate: "
        + verdict_badge
        + f" (`{result.policy_name}` Policy)"
    )

    policy = PRESET_POLICIES.get(result.policy_name, PRESET_POLICIES["PRODUCTION_STRICT"])

    grounded_val = result.signals.get("rag_groundedness_score")
    relevance_val = result.signals.get("rag_context_relevance_score")
    citations_val = result.signals.get("rag_citation_accuracy_score")
    refusal_val = result.signals.get("rag_truthful_refusal_score")

    rag_grounded_row = _format_rag_row(
        "RAG Groundedness",
        grounded_val,
        policy.min_rag_groundedness,
        pass_label="Grounded",
        fail_label="Hallucination",
    )
    rag_relevance_row = _format_rag_row(
        "Context Relevance",
        relevance_val,
        policy.min_rag_context_relevance,
        pass_label="Relevant",
        fail_label="Noisy/Irrelevant",
    )
    rag_citation_row = _format_rag_row(
        "Citation Accuracy",
        citations_val,
        policy.min_rag_citation_accuracy,
        pass_label="Accurate",
        fail_label="Fabricated/Uncited",
    )
    rag_refusal_row = _format_rag_row(
        "Truthful Refusal",
        refusal_val,
        policy.min_rag_truthful_refusal,
        pass_label="Truthful",
        fail_label="Untruthful Refusal",
    )

    sec_vulns = result.signals.get("security_vulnerabilities", 0)
    crit_sec = result.signals.get("critical_security_vulnerabilities", 0)
    pci_sec = result.signals.get("pci_dss_violations", 0)

    summary_table = f"""
| Metric | Result | Target / Threshold | Status |
| :--- | :--- | :--- | :--- |
| **Pass Rate** | `{result.pass_rate:.1%}` ({result.passed_tests}/{result.total}) | >= {policy.min_pass_rate:.1%} | {"✅ Pass" if result.failure_rate == 0 else "❌ Fail"} |
| **Failed Tests** | `{result.failed_tests}` | 0 | {"✅ Pass" if result.failed_tests == 0 else "❌ Fail"} |
| **Critical Defects** | `{result.signals.get('critical_defects', 0)}` | 0 | {"✅ None" if result.signals.get('critical_defects', 0) == 0 else "❌ Critical"} |
| **Contract Failures** | `{result.signals.get('contract_failures', 0)}` | 0 | {"✅ Verified" if result.signals.get('contract_failures', 0) == 0 else "❌ Broken"} |
| **Security Findings** | `{sec_vulns}` | 0 | {"✅ Secure" if sec_vulns == 0 else "❌ Finding"} |
| **Critical OWASP Flaws** | `{crit_sec}` | 0 | {"✅ None" if crit_sec == 0 else "❌ Critical Flaw"} |
| **PCI DSS Violations** | `{pci_sec}` | 0 | {"✅ Masked / Compliant" if pci_sec == 0 else "❌ Unmasked Card Data"} |
{rag_grounded_row}
{rag_relevance_row}
{rag_citation_row}
{rag_refusal_row}
"""

    security_details_section = ""
    findings = result.signals.get("security_findings", [])
    if findings:
        security_details_section = "\n#### 🛡️ Security DAST & PCI DSS Audit Findings:\n"
        for idx, f in enumerate(findings[:10], 1):
            category = f.get("category", "VULNERABILITY")
            severity = f.get("severity", "HIGH")
            loc = f.get("location", "payload")
            desc = f.get("description", "")
            remed = f.get("remediation", "")
            security_details_section += (
                f"{idx}. **[{severity}] {category}** (`{loc}`): {desc}\n"
                f"   - *Remediation*: {remed}\n"
            )
        if len(findings) > 10:
            security_details_section += f"\n*...and {len(findings) - 10} more findings.*"

    violations_section = ""
    if result.violations:
        violations_section = "\n#### ⚠️ Policy Violations Detected:\n"
        for v in result.violations:
            violations_section += f"- ❌ {v}\n"
    else:
        violations_section = "\n> [!NOTE]\n> All quality gate invariants satisfied. Release candidate meets promotion standards.\n"

    footer = f"\n*Evaluated at `{result.evaluated_at}` by QA Intelligence Governance Engine.*"
    return f"{headline}\n{summary_table}\n{security_details_section}\n{violations_section}\n{footer}\n"


def run_cli(args_list: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="QA Intelligence Hub — Multi-Signal Release Quality Gate Evaluator"
    )
    parser.add_argument(
        "--policy",
        choices=list(PRESET_POLICIES.keys()),
        default="PRODUCTION_STRICT",
        help="Quality policy tier to enforce",
    )
    parser.add_argument(
        "--junit-xml",
        type=str,
        default=None,
        help="Path to pytest JUnit XML report file",
    )
    parser.add_argument(
        "--playwright-json",
        type=str,
        default=None,
        help="Path to Playwright test results JSON file",
    )
    parser.add_argument(
        "--rag-json",
        type=str,
        default=None,
        help="Path to RAG evaluation benchmark JSON file",
    )
    parser.add_argument(
        "--total",
        type=int,
        default=None,
        help="Manual override: total tests run",
    )
    parser.add_argument(
        "--passed",
        type=int,
        default=None,
        help="Manual override: passed tests count",
    )
    parser.add_argument(
        "--failed",
        type=int,
        default=None,
        help="Manual override: failed tests count",
    )
    parser.add_argument(
        "--critical-defects",
        type=int,
        default=0,
        help="Number of active critical defects",
    )
    parser.add_argument(
        "--contract-failures",
        type=int,
        default=0,
        help="Number of API schema contract failures",
    )
    parser.add_argument(
        "--security-findings",
        type=int,
        default=0,
        help="Number of security findings",
    )
    parser.add_argument(
        "--task-checkpoint",
        type=str,
        default=None,
        help="Execute Task Completion / DoD checkpoint verification for the specified task",
    )
    parser.add_argument(
        "--skip-git-check",
        action="store_true",
        default=False,
        help="Skip git working tree cleanliness check during task checkpoint",
    )
    parser.add_argument(
        "--security-json",
        type=str,
        default=None,
        help="Path to security DAST report JSON file",
    )
    parser.add_argument(
        "--critical-security",
        type=int,
        default=None,
        help="Manual override: number of critical security findings",
    )
    parser.add_argument(
        "--pci-violations",
        type=int,
        default=None,
        help="Manual override: number of PCI DSS violations",
    )
    parser.add_argument(
        "--rag-score",
        "--rag-groundedness",
        dest="rag_groundedness",
        type=float,
        default=None,
        help="RAG groundedness score (0.0 to 1.0)",
    )
    parser.add_argument(
        "--rag-relevance",
        "--rag-context-relevance",
        dest="rag_relevance",
        type=float,
        default=None,
        help="RAG context relevance score (0.0 to 1.0)",
    )
    parser.add_argument(
        "--rag-citations",
        "--rag-citation-accuracy",
        dest="rag_citations",
        type=float,
        default=None,
        help="RAG citation accuracy score (0.0 to 1.0)",
    )
    parser.add_argument(
        "--rag-refusal",
        "--rag-truthful-refusal",
        dest="rag_refusal",
        type=float,
        default=None,
        help="RAG truthful refusal score (0.0 to 1.0)",
    )
    parser.add_argument(
        "--output-markdown",
        type=str,
        default=None,
        help="Path to write GitHub PR markdown comment report",
    )

    args = parser.parse_args(args_list)

    if args.task_checkpoint:
        from task_checkpoint import evaluate_task_checkpoint
        cp_report = evaluate_task_checkpoint(
            task_name=args.task_checkpoint,
            junit_xml=args.junit_xml,
            playwright_json=args.playwright_json,
            security_json=args.security_json,
            rag_json=args.rag_json,
            total_override=args.total,
            passed_override=args.passed,
            failed_override=args.failed,
            git_clean=True if args.skip_git_check else None,
        )
        print("\n" + cp_report.to_formatted_text() + "\n")
        if args.output_markdown:
            out_p = Path(args.output_markdown)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(f"```text\n{cp_report.to_formatted_text()}\n```\n", encoding="utf-8")
        return 0 if cp_report.final_status == "PASSED" else 1

    # Ingest from reports if provided
    gate_input = QualityGateInput()
    if args.junit_xml and Path(args.junit_xml).exists():
        gate_input = parse_junit_xml(args.junit_xml)
    elif args.playwright_json and Path(args.playwright_json).exists():
        gate_input = parse_playwright_json(args.playwright_json)

    # Ingest from RAG benchmark JSON if provided
    if args.rag_json and Path(args.rag_json).exists():
        rag_input = parse_rag_eval_json(args.rag_json)
        if gate_input.total_tests == 0 and rag_input.total_tests > 0:
            gate_input.total_tests = rag_input.total_tests
            gate_input.passed_tests = rag_input.passed_tests
            gate_input.failed_tests = rag_input.failed_tests
            gate_input.skipped_tests = rag_input.skipped_tests
        if rag_input.rag_groundedness_score is not None:
            gate_input.rag_groundedness_score = rag_input.rag_groundedness_score
        if rag_input.rag_context_relevance_score is not None:
            gate_input.rag_context_relevance_score = rag_input.rag_context_relevance_score
        if rag_input.rag_citation_accuracy_score is not None:
            gate_input.rag_citation_accuracy_score = rag_input.rag_citation_accuracy_score
        if rag_input.rag_truthful_refusal_score is not None:
            gate_input.rag_truthful_refusal_score = rag_input.rag_truthful_refusal_score

    # Ingest from Security DAST JSON if provided
    if args.security_json and Path(args.security_json).exists():
        sec_input = parse_security_scan_json(args.security_json)
        gate_input.security_vulnerabilities = max(
            gate_input.security_vulnerabilities, sec_input.security_vulnerabilities
        )
        gate_input.critical_security_vulnerabilities = max(
            gate_input.critical_security_vulnerabilities, sec_input.critical_security_vulnerabilities
        )
        gate_input.pci_dss_violations = max(
            gate_input.pci_dss_violations, sec_input.pci_dss_violations
        )
        if sec_input.security_compliance_rate is not None:
            gate_input.security_compliance_rate = sec_input.security_compliance_rate
        gate_input.security_findings.extend(sec_input.security_findings)

    # Apply command-line overrides if given
    if args.total is not None:
        gate_input.total_tests = args.total
    if args.passed is not None:
        gate_input.passed_tests = args.passed
    if args.failed is not None:
        gate_input.failed_tests = args.failed

    gate_input.critical_defects = args.critical_defects
    gate_input.contract_failures = args.contract_failures
    if args.security_findings > 0 or gate_input.security_vulnerabilities == 0:
        gate_input.security_vulnerabilities = max(gate_input.security_vulnerabilities, args.security_findings)
    if args.critical_security is not None:
        gate_input.critical_security_vulnerabilities = args.critical_security
    if args.pci_violations is not None:
        gate_input.pci_dss_violations = args.pci_violations

    if args.rag_groundedness is not None:
        gate_input.rag_groundedness_score = args.rag_groundedness
    if args.rag_relevance is not None:
        gate_input.rag_context_relevance_score = args.rag_relevance
    if args.rag_citations is not None:
        gate_input.rag_citation_accuracy_score = args.rag_citations
    if args.rag_refusal is not None:
        gate_input.rag_truthful_refusal_score = args.rag_refusal

    # Evaluate
    policy = PRESET_POLICIES.get(args.policy, PRESET_POLICIES["PRODUCTION_STRICT"])
    result = evaluate_policy_gate(gate_input, policy=policy)

    markdown_report = generate_pr_markdown_report(result)

    if args.output_markdown:
        out_p = Path(args.output_markdown)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(markdown_report, encoding="utf-8")
        print(f"Quality gate PR report written to: {args.output_markdown}")

    print("\n" + markdown_report)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(run_cli())
