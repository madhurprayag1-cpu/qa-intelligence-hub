"""Reporting Specialist Agent Tests.

Adheres to AGENTS.md Section 6 & Section 20:
- Tests ReportingAgent executive report synthesis
- Tests GO decision logic when all gates pass with zero regressions
- Tests NO-GO decision logic when critical defects or policy violations occur
- Tests MCP tool call integration for generate_release_report
"""

import pytest
from agents import ReportingAgent
from mcp_server import call_tool


@pytest.mark.anyio
async def test_reporting_agent_go_decision():
    """ReportingAgent recommends GO when all quality signals pass thresholds."""
    agent = ReportingAgent()
    context = {
        "policy_name": "PRODUCTION_STRICT",
        "total_tests": 143,
        "passed_tests": 143,
        "failed_tests": 0,
        "critical_defects": 0,
        "contract_failures": 0,
        "security_vulnerabilities": 0,
        "rag_groundedness_score": 0.95,
        "quality_gate_status": "PASSED",
        "violations": [],
    }
    run = await agent.execute("Generate release sign-off", context)

    assert run.status == "COMPLETED"
    assert run.run_id.startswith("RUN-")
    assert "GO — APPROVED FOR RELEASE" in run.output
    assert "Deployment to production authorized" in run.output
    assert any(e.event_type == "REPORT_GENERATED" for e in run.events)


@pytest.mark.anyio
async def test_reporting_agent_no_go_on_violations():
    """ReportingAgent recommends NO-GO and actionable remediation when violations occur."""
    agent = ReportingAgent()
    context = {
        "policy_name": "PRODUCTION_STRICT",
        "total_tests": 100,
        "passed_tests": 95,
        "failed_tests": 5,
        "critical_defects": 1,
        "contract_failures": 0,
        "security_vulnerabilities": 1,
        "rag_groundedness_score": 0.70,
        "quality_gate_status": "BLOCKED",
        "violations": [
            "Test pass rate 95.0% < threshold 100.0%",
            "Critical defects 1 > allowed 0",
            "Security vulnerabilities 1 > allowed 0",
        ],
    }
    run = await agent.execute("Generate release sign-off", context)

    assert run.status == "COMPLETED"
    assert "NO-GO — RELEASE BLOCKED" in run.output
    assert "Critical defects 1 > allowed 0" in run.output
    assert "DefectRCAAgent" in run.output
    assert "SecurityTestingAgent" in run.output


def test_mcp_generate_release_report_tool():
    """Verify MCP server executes generate_release_report tool successfully."""
    args = {
        "policy_name": "PRODUCTION_STRICT",
        "total_tests": 50,
        "passed_tests": 50,
        "failed_tests": 0,
        "critical_defects": 0,
        "security_vulnerabilities": 0,
        "rag_groundedness_score": 0.94,
        "quality_gate_status": "PASSED",
    }
    res = call_tool("generate_release_report", args)

    assert res["status"] == "success"
    assert res["tool"] == "generate_release_report"
    assert "report_markdown" in res["result"]
    assert "GO — APPROVED FOR RELEASE" in res["result"]["report_markdown"]
