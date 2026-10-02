import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class QualityGatePolicy:
    """Configurable quality policy per AGENTS.md Section 24."""
    name: str = "PRODUCTION_STRICT"
    min_pass_rate: float = 1.0  # 1.0 = 100%
    max_failure_rate: float = 0.0
    max_critical_defects: int = 0
    min_rag_groundedness: float = 0.85
    min_rag_context_relevance: float = 0.80
    min_rag_citation_accuracy: float = 0.85
    min_rag_truthful_refusal: float = 0.90
    max_contract_failures: int = 0
    max_security_vulnerabilities: int = 0
    max_critical_security_vulnerabilities: int = 0
    max_pci_dss_violations: int = 0
    min_security_compliance_rate: float = 1.0
    max_flaky_tests: int = 0
    min_total_tests: int = 1


# Predefined policy tiers
PRESET_POLICIES: Dict[str, QualityGatePolicy] = {
    "PRODUCTION_STRICT": QualityGatePolicy(
        name="PRODUCTION_STRICT",
        min_pass_rate=1.0,
        max_failure_rate=0.0,
        max_critical_defects=0,
        min_rag_groundedness=0.85,
        min_rag_context_relevance=0.80,
        min_rag_citation_accuracy=0.85,
        min_rag_truthful_refusal=0.90,
        max_contract_failures=0,
        max_security_vulnerabilities=0,
        max_critical_security_vulnerabilities=0,
        max_pci_dss_violations=0,
        min_security_compliance_rate=1.0,
        max_flaky_tests=0,
        min_total_tests=1,
    ),
    "STAGING_STANDARD": QualityGatePolicy(
        name="STAGING_STANDARD",
        min_pass_rate=0.95,
        max_failure_rate=0.05,
        max_critical_defects=0,
        min_rag_groundedness=0.75,
        min_rag_context_relevance=0.70,
        min_rag_citation_accuracy=0.75,
        min_rag_truthful_refusal=0.80,
        max_contract_failures=1,
        max_security_vulnerabilities=0,
        max_critical_security_vulnerabilities=0,
        max_pci_dss_violations=0,
        min_security_compliance_rate=1.0,
        max_flaky_tests=2,
        min_total_tests=1,
    ),
    "DEV_PR_FAST": QualityGatePolicy(
        name="DEV_PR_FAST",
        min_pass_rate=0.90,
        max_failure_rate=0.10,
        max_critical_defects=0,
        min_rag_groundedness=0.70,
        min_rag_context_relevance=0.60,
        min_rag_citation_accuracy=0.70,
        min_rag_truthful_refusal=0.70,
        max_contract_failures=2,
        max_security_vulnerabilities=0,
        max_critical_security_vulnerabilities=0,
        max_pci_dss_violations=0,
        min_security_compliance_rate=1.0,
        max_flaky_tests=3,
        min_total_tests=1,
    ),
}


@dataclass
class QualityGateInput:
    """Consolidated quality signals from execution runs."""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    critical_defects: int = 0
    contract_failures: int = 0
    security_vulnerabilities: int = 0
    critical_security_vulnerabilities: int = 0
    pci_dss_violations: int = 0
    security_compliance_rate: Optional[float] = None
    security_findings: List[Dict[str, Any]] = field(default_factory=list)
    rag_groundedness_score: Optional[float] = None
    rag_context_relevance_score: Optional[float] = None
    rag_citation_accuracy_score: Optional[float] = None
    rag_truthful_refusal_score: Optional[float] = None
    flaky_tests: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityGateResult:
    passed: bool
    total: int
    passed_tests: int
    failed_tests: int
    skipped: int
    failure_rate: float
    status: str = "PASSED"
    policy_name: str = "DEFAULT"
    pass_rate: float = 1.0
    violations: List[str] = field(default_factory=list)
    signals: Dict[str, Any] = field(default_factory=dict)
    evaluated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def evaluate_gate(
    total: int,
    passed: int,
    failed: int,
    skipped: int = 0,
    max_failure_rate: float = 0.0,
) -> QualityGateResult:
    """Backward-compatible basic quality gate evaluator."""
    rate = failed / total if total else 1.0
    pass_rate = passed / total if total else 0.0
    is_passed = total > 0 and rate <= max_failure_rate
    violations = []
    if total == 0:
        violations.append("Test suite is empty (total = 0)")
    if rate > max_failure_rate:
        violations.append(f"Failure rate {rate:.2%} exceeded threshold {max_failure_rate:.2%}")

    return QualityGateResult(
        passed=is_passed,
        total=total,
        passed_tests=passed,
        failed_tests=failed,
        skipped=skipped,
        failure_rate=rate,
        pass_rate=pass_rate,
        status="PASSED" if is_passed else "FAILED",
        policy_name="LEGACY_EVALUATE_GATE",
        violations=violations,
        signals={
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "failure_rate": rate,
        },
    )


def evaluate_policy_gate(
    inp: QualityGateInput,
    policy: Optional[QualityGatePolicy] = None,
) -> QualityGateResult:
    """Multi-signal policy quality gate evaluation."""
    p = policy or PRESET_POLICIES["PRODUCTION_STRICT"]
    violations: List[str] = []

    # 1. Minimum test suite size
    if inp.total_tests < p.min_total_tests:
        violations.append(
            f"Suite contains {inp.total_tests} tests, below minimum required {p.min_total_tests}"
        )

    # 2. Pass rate & failure rate
    pass_rate = (inp.passed_tests / inp.total_tests) if inp.total_tests > 0 else 0.0
    failure_rate = (inp.failed_tests / inp.total_tests) if inp.total_tests > 0 else 1.0

    if pass_rate < p.min_pass_rate:
        violations.append(
            f"Pass rate {pass_rate:.1%} is below required minimum {p.min_pass_rate:.1%}"
        )
    if failure_rate > p.max_failure_rate:
        violations.append(
            f"Failure rate {failure_rate:.1%} exceeds maximum allowable {p.max_failure_rate:.1%}"
        )

    # 3. Critical defects
    if inp.critical_defects > p.max_critical_defects:
        violations.append(
            f"Found {inp.critical_defects} critical defects, maximum allowed is {p.max_critical_defects}"
        )

    # 4. API Contract Failures
    if inp.contract_failures > p.max_contract_failures:
        violations.append(
            f"Found {inp.contract_failures} API contract failures, maximum allowed is {p.max_contract_failures}"
        )

    # 5. Security vulnerabilities & PCI DSS (AGENTS.md Section 21)
    if inp.security_vulnerabilities > p.max_security_vulnerabilities:
        violations.append(
            f"Found {inp.security_vulnerabilities} security findings, maximum allowed is {p.max_security_vulnerabilities}"
        )
    if inp.critical_security_vulnerabilities > p.max_critical_security_vulnerabilities:
        violations.append(
            f"Found {inp.critical_security_vulnerabilities} critical security findings (SQLi/OWASP), maximum allowed is {p.max_critical_security_vulnerabilities}"
        )
    if inp.pci_dss_violations > p.max_pci_dss_violations:
        violations.append(
            f"Found {inp.pci_dss_violations} PCI DSS cardholder data violations (unmasked PAN/CVV), maximum allowed is {p.max_pci_dss_violations}"
        )
    if inp.security_compliance_rate is not None:
        if inp.security_compliance_rate < p.min_security_compliance_rate:
            violations.append(
                f"Security compliance rate {inp.security_compliance_rate:.1%} is below required minimum {p.min_security_compliance_rate:.1%}"
            )

    # 6. Flaky tests
    if inp.flaky_tests > p.max_flaky_tests:
        violations.append(
            f"Found {inp.flaky_tests} flaky tests, threshold is {p.max_flaky_tests}"
        )

    # 7. AI / RAG Quality Signals (Multi-Signal Governance)
    if inp.rag_groundedness_score is not None:
        if inp.rag_groundedness_score < p.min_rag_groundedness:
            violations.append(
                f"RAG groundedness score {inp.rag_groundedness_score:.2f} is below required {p.min_rag_groundedness:.2f}"
            )

    if inp.rag_context_relevance_score is not None:
        if inp.rag_context_relevance_score < p.min_rag_context_relevance:
            violations.append(
                f"RAG context relevance score {inp.rag_context_relevance_score:.2f} is below required {p.min_rag_context_relevance:.2f}"
            )

    if inp.rag_citation_accuracy_score is not None:
        if inp.rag_citation_accuracy_score < p.min_rag_citation_accuracy:
            violations.append(
                f"RAG citation accuracy score {inp.rag_citation_accuracy_score:.2f} is below required {p.min_rag_citation_accuracy:.2f}"
            )

    if inp.rag_truthful_refusal_score is not None:
        if inp.rag_truthful_refusal_score < p.min_rag_truthful_refusal:
            violations.append(
                f"RAG truthful refusal score {inp.rag_truthful_refusal_score:.2f} is below required {p.min_rag_truthful_refusal:.2f}"
            )

    is_passed = len(violations) == 0

    return QualityGateResult(
        passed=is_passed,
        total=inp.total_tests,
        passed_tests=inp.passed_tests,
        failed_tests=inp.failed_tests,
        skipped=inp.skipped_tests,
        failure_rate=failure_rate,
        pass_rate=pass_rate,
        status="PASSED" if is_passed else "FAILED",
        policy_name=p.name,
        violations=violations,
        signals={
            "total_tests": inp.total_tests,
            "passed_tests": inp.passed_tests,
            "failed_tests": inp.failed_tests,
            "critical_defects": inp.critical_defects,
            "contract_failures": inp.contract_failures,
            "security_vulnerabilities": inp.security_vulnerabilities,
            "critical_security_vulnerabilities": inp.critical_security_vulnerabilities,
            "pci_dss_violations": inp.pci_dss_violations,
            "security_compliance_rate": inp.security_compliance_rate,
            "security_findings": inp.security_findings,
            "rag_groundedness_score": inp.rag_groundedness_score,
            "rag_context_relevance_score": inp.rag_context_relevance_score,
            "rag_citation_accuracy_score": inp.rag_citation_accuracy_score,
            "rag_truthful_refusal_score": inp.rag_truthful_refusal_score,
            "flaky_tests": inp.flaky_tests,
        },
    )


def parse_junit_xml(xml_content_or_path: str) -> QualityGateInput:
    """Parse Pytest JUnit XML format into QualityGateInput."""
    if Path(xml_content_or_path).exists():
        tree = ET.parse(xml_content_or_path)
        root = tree.getroot()
    else:
        root = ET.fromstring(xml_content_or_path)

    # Handlers for both <testsuite> and <testsuites>
    total = int(root.attrib.get("tests", 0))
    failures = int(root.attrib.get("failures", 0))
    errors = int(root.attrib.get("errors", 0))
    skipped = int(root.attrib.get("skipped", 0))

    if root.tag == "testsuites":
        for ts in root.findall("testsuite"):
            total += int(ts.attrib.get("tests", 0))
            failures += int(ts.attrib.get("failures", 0))
            errors += int(ts.attrib.get("errors", 0))
            skipped += int(ts.attrib.get("skipped", 0))

    total_failures = failures + errors
    passed = max(0, total - total_failures - skipped)

    return QualityGateInput(
        total_tests=total,
        passed_tests=passed,
        failed_tests=total_failures,
        skipped_tests=skipped,
        metadata={"source": "junit_xml"},
    )


def parse_playwright_json(json_content_or_path: str) -> QualityGateInput:
    """Parse Playwright JSON report into QualityGateInput."""
    if Path(json_content_or_path).exists():
        data = json.loads(Path(json_content_or_path).read_text(encoding="utf-8"))
    else:
        data = json.loads(json_content_or_path)

    stats = data.get("stats", {})
    expected = stats.get("expected", 0)
    unexpected = stats.get("unexpected", 0)
    flaky = stats.get("flaky", 0)
    skipped = stats.get("skipped", 0)
    total = expected + unexpected + flaky + skipped

    return QualityGateInput(
        total_tests=total,
        passed_tests=expected,
        failed_tests=unexpected,
        skipped_tests=skipped,
        flaky_tests=flaky,
        metadata={"source": "playwright_json", "duration": stats.get("duration", 0)},
    )


def parse_rag_eval_json(json_content_or_path: str) -> QualityGateInput:
    """
    Parse RAG evaluation benchmark JSON report into QualityGateInput.
    Supports top-level scores, nested metrics dicts, and test counts.
    """
    if Path(json_content_or_path).exists():
        data = json.loads(Path(json_content_or_path).read_text(encoding="utf-8"))
    else:
        data = json.loads(json_content_or_path)

    metrics = data.get("metrics", data)

    # Extract test counts if present
    total = int(data.get("total_queries", data.get("total_tests", data.get("total", 0))))
    passed = int(data.get("passed_queries", data.get("passed_tests", data.get("passed", total))))
    failed = int(data.get("failed_queries", data.get("failed_tests", data.get("failed", 0))))
    skipped = int(data.get("skipped_queries", data.get("skipped_tests", data.get("skipped", 0))))

    # Extract multi-signal RAG metrics
    groundedness = metrics.get(
        "groundedness", metrics.get("rag_groundedness_score", metrics.get("groundedness_score"))
    )
    context_relevance = metrics.get(
        "context_relevance",
        metrics.get("rag_context_relevance_score", metrics.get("context_relevance_score")),
    )
    citation_accuracy = metrics.get(
        "citation_accuracy",
        metrics.get("rag_citation_accuracy_score", metrics.get("citation_accuracy_score")),
    )
    truthful_refusal = metrics.get(
        "truthful_refusal",
        metrics.get("rag_truthful_refusal_score", metrics.get("truthful_refusal_score")),
    )

    return QualityGateInput(
        total_tests=total,
        passed_tests=passed,
        failed_tests=failed,
        skipped_tests=skipped,
        rag_groundedness_score=float(groundedness) if groundedness is not None else None,
        rag_context_relevance_score=float(context_relevance) if context_relevance is not None else None,
        rag_citation_accuracy_score=float(citation_accuracy) if citation_accuracy is not None else None,
        rag_truthful_refusal_score=float(truthful_refusal) if truthful_refusal is not None else None,
        metadata={"source": "rag_eval_json", **data.get("metadata", {})},
    )


def parse_security_scan_json(json_content_or_path: str) -> QualityGateInput:
    """
    Parse Security DAST scan JSON report into QualityGateInput.
    Supports SecurityTestingAgent reports and SecurityScanner audit summaries.
    """
    if Path(json_content_or_path).exists():
        data = json.loads(Path(json_content_or_path).read_text(encoding="utf-8"))
    else:
        data = json.loads(json_content_or_path)

    findings = data.get("findings", [])
    total_scans = int(data.get("total_scans", data.get("scans_count", len(findings) if findings else 1)))
    failed_scans = int(data.get("failed_scans", len(findings)))
    passed_scans = int(data.get("passed_scans", max(0, total_scans - failed_scans)))

    critical_count = int(
        data.get(
            "critical_vulnerabilities",
            sum(1 for f in findings if f.get("severity") == "CRITICAL"),
        )
    )
    pci_count = int(
        data.get(
            "pci_dss_violations",
            sum(1 for f in findings if "PCI_DSS" in f.get("category", "")),
        )
    )
    total_findings = int(data.get("vulnerabilities_count", len(findings)))

    compliance_rate = float(
        data.get(
            "compliance_rate",
            (passed_scans / total_scans) if total_scans > 0 else (1.0 if total_findings == 0 else 0.0),
        )
    )

    return QualityGateInput(
        total_tests=total_scans,
        passed_tests=passed_scans,
        failed_tests=failed_scans,
        security_vulnerabilities=total_findings,
        critical_security_vulnerabilities=critical_count,
        pci_dss_violations=pci_count,
        security_compliance_rate=compliance_rate,
        security_findings=findings,
        metadata={"source": "security_dast_json", "status": data.get("status", "COMPLETED")},
    )
