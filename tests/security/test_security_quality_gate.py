"""Deterministic Automated Test Suite for Phase 6 Task 6.5:
Automated Continuous Security Scanning (DAST) Gate.

Adheres strictly to AGENTS.md Sections 6, 21, 24 and docs/ROADMAP.md Task 6.5:
- Verifies SecurityTestingAgent batch scanning and convenience methods
- Verifies DAST security scanner execution (baseline vs attack verification suites)
- Enforces Quality Gate rejection on OWASP vulnerabilities (SQLi, XSS, Prompt Injection, IDOR)
- Enforces Quality Gate rejection on PCI DSS non-compliance (unmasked PAN, CVV storage)
- Verifies parse_security_scan_json integration into multi-signal quality gate
- Verifies cli_gate.py --security-json ingestion and GitHub PR markdown reporting
- Verifies REST API contracts: /ai/security/scan-suite, /quality-gate/evaluate, /quality-gate/policies
"""

import json
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "ai-engine") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "ai-engine"))
if str(_REPO_ROOT / "qa-engine") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "qa-engine"))

from agents import SecurityTestingAgent
from app.main import app
from cli_gate import generate_pr_markdown_report, run_cli
from quality_gate import (
    PRESET_POLICIES,
    QualityGateInput,
    QualityGatePolicy,
    evaluate_policy_gate,
    parse_security_scan_json,
)
from security_scanner import (
    ATTACK_VERIFICATION_SUITE,
    BASELINE_GATE_SUITE,
    run_dast_scan,
    save_scan_report,
)

client = TestClient(app)


# --- 1. SecurityTestingAgent Batch & Convenience Methods ---

@pytest.mark.anyio
async def test_security_agent_audit_payload():
    """Verify audit_payload returns a parsed dictionary with security verdict."""
    agent = SecurityTestingAgent()
    clean_res = await agent.audit_payload(
        endpoint="/bookings",
        payload={"passenger_name": "Elena Papadopoulos", "seats": 1},
    )
    assert clean_res["status"] == "SECURE"
    assert clean_res["findings_count"] == 0
    assert clean_res["pci_dss_compliant"] is True

    attack_res = await agent.audit_payload(
        endpoint="/bookings",
        payload={"passenger_name": "<script>alert('XSS')</script>", "seats": 1},
    )
    assert attack_res["status"] == "VULNERABLE"
    assert attack_res["findings_count"] >= 1
    assert any(f["category"] == "CROSS_SITE_SCRIPTING" for f in attack_res["findings"])


@pytest.mark.anyio
async def test_security_agent_scan_suite_baseline():
    """Verify scan_suite on baseline gate suite returns 100% compliance and zero vulnerabilities."""
    agent = SecurityTestingAgent()
    report = await agent.scan_suite(BASELINE_GATE_SUITE)

    assert report["status"] == "SECURE"
    assert report["total_scans"] == len(BASELINE_GATE_SUITE)
    assert report["passed_scans"] == len(BASELINE_GATE_SUITE)
    assert report["failed_scans"] == 0
    assert report["vulnerabilities_count"] == 0
    assert report["critical_vulnerabilities"] == 0
    assert report["pci_dss_violations"] == 0
    assert report["compliance_rate"] == 1.0
    assert len(report["findings"]) == 0


@pytest.mark.anyio
async def test_security_agent_scan_suite_attacks():
    """Verify scan_suite on attack suite identifies all OWASP & PCI DSS vectors."""
    agent = SecurityTestingAgent()
    report = await agent.scan_suite(ATTACK_VERIFICATION_SUITE)

    assert report["status"] == "VULNERABLE"
    assert report["vulnerabilities_count"] >= len(ATTACK_VERIFICATION_SUITE)
    assert report["critical_vulnerabilities"] >= 3  # SQLi + PCI DSS PAN + PCI DSS CVV
    assert report["pci_dss_violations"] >= 2  # PAN + CVV
    assert report["owasp_violations"] >= 4  # SQLi, XSS, Prompt Injection, IDOR
    assert report["compliance_rate"] == 0.0

    categories = {f["category"] for f in report["findings"]}
    assert "SQL_INJECTION" in categories
    assert "CROSS_SITE_SCRIPTING" in categories
    assert "PCI_DSS_EXPOSURE" in categories
    assert "PCI_DSS_CVV_STORAGE" in categories
    assert "PROMPT_INJECTION" in categories
    assert "IDOR_AUTHORIZATION_BYPASS" in categories


# --- 2. Security Scanner Module Tests ---

def test_run_dast_scan_baseline_sync():
    """Verify run_dast_scan executes synchronously and passes baseline."""
    report = run_dast_scan(mode="gate")
    assert report["status"] == "SECURE"
    assert report["compliance_rate"] == 1.0
    assert report["vulnerabilities_count"] == 0


def test_run_dast_scan_attack_sync(tmp_path):
    """Verify run_dast_scan executes attack suite and serializes report."""
    report = run_dast_scan(mode="attack")
    assert report["status"] == "VULNERABLE"
    assert report["vulnerabilities_count"] > 0

    out_file = tmp_path / "security_report.json"
    save_scan_report(report, out_file)
    assert out_file.exists()

    loaded = json.loads(out_file.read_text(encoding="utf-8"))
    assert loaded["status"] == "VULNERABLE"
    assert loaded["vulnerabilities_count"] == report["vulnerabilities_count"]


# --- 3. Quality Gate Ingestion & Policy Evaluation ---

def test_parse_security_scan_json(tmp_path):
    """Verify parse_security_scan_json extracts all quality signals accurately."""
    sample_report = {
        "status": "VULNERABLE",
        "total_scans": 5,
        "passed_scans": 3,
        "failed_scans": 2,
        "vulnerabilities_count": 2,
        "critical_vulnerabilities": 1,
        "pci_dss_violations": 1,
        "compliance_rate": 0.60,
        "findings": [
            {
                "category": "SQL_INJECTION",
                "severity": "CRITICAL",
                "location": "request_payload",
                "description": "SQL injection payload detected",
                "remediation": "Use ORM parameterization",
            },
            {
                "category": "PCI_DSS_EXPOSURE",
                "severity": "CRITICAL",
                "location": "card_number",
                "description": "Unmasked PAN detected",
                "remediation": "Mask card number to last 4 digits",
            },
        ],
    }
    json_path = tmp_path / "dast_sample.json"
    json_path.write_text(json.dumps(sample_report), encoding="utf-8")

    inp = parse_security_scan_json(str(json_path))
    assert inp.total_tests == 5
    assert inp.passed_tests == 3
    assert inp.failed_tests == 2
    assert inp.security_vulnerabilities == 2
    assert inp.critical_security_vulnerabilities == 1
    assert inp.pci_dss_violations == 1
    assert inp.security_compliance_rate == 0.60
    assert len(inp.security_findings) == 2


def test_quality_gate_passes_clean_security_scan():
    """Verify clean security audit passes PRODUCTION_STRICT gate."""
    clean_input = QualityGateInput(
        total_tests=50,
        passed_tests=50,
        failed_tests=0,
        security_vulnerabilities=0,
        critical_security_vulnerabilities=0,
        pci_dss_violations=0,
        security_compliance_rate=1.0,
    )
    result = evaluate_policy_gate(clean_input, PRESET_POLICIES["PRODUCTION_STRICT"])
    assert result.passed is True
    assert result.status == "PASSED"
    assert len(result.violations) == 0
    assert result.signals["security_vulnerabilities"] == 0
    assert result.signals["pci_dss_violations"] == 0


def test_quality_gate_fails_on_sqli_vulnerability():
    """Verify Quality Gate blocks release if an OWASP SQLi vulnerability is detected."""
    sqli_input = QualityGateInput(
        total_tests=50,
        passed_tests=50,
        failed_tests=0,
        security_vulnerabilities=1,
        critical_security_vulnerabilities=1,
        pci_dss_violations=0,
    )
    result = evaluate_policy_gate(sqli_input, PRESET_POLICIES["PRODUCTION_STRICT"])
    assert result.passed is False
    assert result.status == "FAILED"
    assert any("security findings" in v.lower() for v in result.violations)
    assert any("critical security findings" in v.lower() for v in result.violations)


def test_quality_gate_fails_on_pci_dss_unmasked_pan():
    """Verify Quality Gate blocks release if unmasked cardholder PAN is detected."""
    pci_input = QualityGateInput(
        total_tests=50,
        passed_tests=50,
        failed_tests=0,
        security_vulnerabilities=1,
        critical_security_vulnerabilities=1,
        pci_dss_violations=1,
    )
    result = evaluate_policy_gate(pci_input, PRESET_POLICIES["PRODUCTION_STRICT"])
    assert result.passed is False
    assert any("pci dss" in v.lower() for v in result.violations)


def test_quality_gate_fails_on_low_compliance_rate():
    """Verify Quality Gate blocks release if security compliance rate is under 100%."""
    rate_input = QualityGateInput(
        total_tests=50,
        passed_tests=50,
        failed_tests=0,
        security_compliance_rate=0.85,  # Below 1.0
    )
    result = evaluate_policy_gate(rate_input, PRESET_POLICIES["PRODUCTION_STRICT"])
    assert result.passed is False
    assert any("compliance rate" in v.lower() for v in result.violations)


# --- 4. CLI & Markdown PR Reporting Tests ---

def test_generate_pr_markdown_report_includes_security_table():
    """Verify PR markdown report includes security and PCI DSS audit status."""
    inp = QualityGateInput(
        total_tests=100,
        passed_tests=100,
        failed_tests=0,
        security_vulnerabilities=0,
        critical_security_vulnerabilities=0,
        pci_dss_violations=0,
    )
    res = evaluate_policy_gate(inp, PRESET_POLICIES["PRODUCTION_STRICT"])
    md = generate_pr_markdown_report(res)

    assert "Security Findings" in md
    assert "Critical OWASP Flaws" in md
    assert "PCI DSS Violations" in md
    assert "Masked / Compliant" in md


def test_generate_pr_markdown_report_formats_findings_breakdown():
    """Verify PR markdown report formats detailed security findings and remediation."""
    inp = QualityGateInput(
        total_tests=100,
        passed_tests=98,
        failed_tests=2,
        security_vulnerabilities=1,
        critical_security_vulnerabilities=1,
        pci_dss_violations=1,
        security_findings=[
            {
                "category": "PCI_DSS_EXPOSURE",
                "severity": "CRITICAL",
                "location": "request_payload.card_number",
                "description": "Unmasked Primary Account Number detected in payload.",
                "remediation": "Never store unmasked PANs; mask to last 4 digits.",
            }
        ],
    )
    res = evaluate_policy_gate(inp, PRESET_POLICIES["PRODUCTION_STRICT"])
    md = generate_pr_markdown_report(res)

    assert "BLOCKED" in md
    assert "Security DAST & PCI DSS Audit Findings" in md
    assert "[CRITICAL] PCI_DSS_EXPOSURE" in md
    assert "Remediation" in md


def test_run_cli_with_security_json_clean(tmp_path):
    """Verify CLI returns exit code 0 when given a clean security DAST report."""
    clean_report = {
        "status": "SECURE",
        "total_scans": 5,
        "passed_scans": 5,
        "failed_scans": 0,
        "vulnerabilities_count": 0,
        "critical_vulnerabilities": 0,
        "pci_dss_violations": 0,
        "compliance_rate": 1.0,
        "findings": [],
    }
    sec_file = tmp_path / "sec_clean.json"
    sec_file.write_text(json.dumps(clean_report), encoding="utf-8")

    out_md = tmp_path / "gate_report.md"
    args = [
        "--policy", "PRODUCTION_STRICT",
        "--total", "50",
        "--passed", "50",
        "--failed", "0",
        "--security-json", str(sec_file),
        "--output-markdown", str(out_md),
    ]

    exit_code = run_cli(args)
    assert exit_code == 0
    assert out_md.exists()
    content = out_md.read_text(encoding="utf-8")
    assert "APPROVED" in content
    assert "Masked / Compliant" in content


def test_run_cli_with_security_json_vulnerable(tmp_path):
    """Verify CLI returns exit code 1 when security DAST report has vulnerabilities."""
    vuln_report = {
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
    sec_file.write_text(json.dumps(vuln_report), encoding="utf-8")

    out_md = tmp_path / "gate_report_fail.md"
    args = [
        "--policy", "PRODUCTION_STRICT",
        "--total", "50",
        "--passed", "50",
        "--failed", "0",
        "--security-json", str(sec_file),
        "--output-markdown", str(out_md),
    ]

    exit_code = run_cli(args)
    assert exit_code == 1
    assert out_md.exists()
    content = out_md.read_text(encoding="utf-8")
    assert "BLOCKED" in content


# --- 5. REST API Endpoint Tests ---

def test_api_security_scan_suite_endpoint_gate():
    """Verify POST /ai/security/scan-suite executes baseline gate suite via API."""
    res = client.post("/ai/security/scan-suite", json={"mode": "gate"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SECURE"
    assert data["vulnerabilities_count"] == 0
    assert data["compliance_rate"] == 1.0


def test_api_security_scan_suite_endpoint_attack():
    """Verify POST /ai/security/scan-suite executes attack verification suite via API."""
    res = client.post("/ai/security/scan-suite", json={"mode": "attack"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VULNERABLE"
    assert data["vulnerabilities_count"] > 0
    assert data["critical_vulnerabilities"] > 0


def test_api_quality_gate_evaluate_endpoint_security_signals():
    """Verify POST /quality-gate/evaluate receives security signals and blocks on violation."""
    payload = {
        "policy_name": "PRODUCTION_STRICT",
        "total_tests": 50,
        "passed_tests": 50,
        "failed_tests": 0,
        "security_vulnerabilities": 1,
        "critical_security_vulnerabilities": 1,
        "pci_dss_violations": 1,
    }
    res = client.post("/quality-gate/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["passed"] is False
    assert data["status"] == "FAILED"
    assert any("pci dss" in v.lower() for v in data["violations"])
    assert data["signals"]["pci_dss_violations"] == 1


def test_api_quality_gate_policies_includes_security_fields():
    """Verify GET /quality-gate/policies returns security criteria."""
    res = client.get("/quality-gate/policies")
    assert res.status_code == 200
    policies = res.json()
    assert "PRODUCTION_STRICT" in policies
    strict = policies["PRODUCTION_STRICT"]
    assert "max_critical_security_vulnerabilities" in strict
    assert "max_pci_dss_violations" in strict
    assert "min_security_compliance_rate" in strict
    assert strict["max_pci_dss_violations"] == 0
