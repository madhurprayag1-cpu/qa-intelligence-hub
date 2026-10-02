import sys
from pathlib import Path
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT / "qa-engine") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "qa-engine"))

from cli_gate import generate_pr_markdown_report, run_cli
from quality_gate import PRESET_POLICIES, QualityGateInput, evaluate_policy_gate


def test_generate_pr_markdown_report_passed():
    inp = QualityGateInput(
        total_tests=100,
        passed_tests=100,
        failed_tests=0,
        critical_defects=0,
        contract_failures=0,
        security_vulnerabilities=0,
        rag_groundedness_score=0.96,
    )
    result = evaluate_policy_gate(inp, PRESET_POLICIES["PRODUCTION_STRICT"])
    report = generate_pr_markdown_report(result)

    assert "APPROVED" in report
    assert "Pass Rate" in report
    assert "100.0%" in report
    assert "RAG Groundedness" in report
    assert "All quality gate invariants satisfied" in report


def test_generate_pr_markdown_report_blocked():
    inp = QualityGateInput(
        total_tests=100,
        passed_tests=92,
        failed_tests=8,
        critical_defects=1,
        contract_failures=1,
        security_vulnerabilities=0,
        rag_groundedness_score=0.60,
    )
    result = evaluate_policy_gate(inp, PRESET_POLICIES["PRODUCTION_STRICT"])
    report = generate_pr_markdown_report(result)

    assert "BLOCKED" in report
    assert "Policy Violations Detected" in report
    assert "Pass rate 92.0% is below required minimum" in report
    assert "Found 1 critical defects" in report


def test_run_cli_exit_code_zero(tmp_path):
    report_file = tmp_path / "pr_gate_report.md"
    args = [
        "--policy", "PRODUCTION_STRICT",
        "--total", "50",
        "--passed", "50",
        "--failed", "0",
        "--critical-defects", "0",
        "--contract-failures", "0",
        "--security-findings", "0",
        "--rag-score", "0.95",
        "--output-markdown", str(report_file),
    ]

    exit_code = run_cli(args)
    assert exit_code == 0
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "APPROVED" in content


def test_run_cli_exit_code_one_on_violation(tmp_path):
    report_file = tmp_path / "pr_gate_fail.md"
    args = [
        "--policy", "PRODUCTION_STRICT",
        "--total", "50",
        "--passed", "48",
        "--failed", "2",
        "--critical-defects", "1",
        "--output-markdown", str(report_file),
    ]

    exit_code = run_cli(args)
    assert exit_code == 1
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "BLOCKED" in content


def test_run_cli_with_junit_xml(tmp_path):
    xml_file = tmp_path / "junit_sample.xml"
    xml_file.write_text("""<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="20" errors="0" failures="0" skipped="0">
  </testsuite>
</testsuites>
""", encoding="utf-8")

    args = [
        "--policy", "PRODUCTION_STRICT",
        "--junit-xml", str(xml_file),
    ]

    exit_code = run_cli(args)
    assert exit_code == 0
