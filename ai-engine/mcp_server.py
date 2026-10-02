"""Model Context Protocol (MCP) Server for QA Intelligence Hub.

Adheres to AGENTS.md Section 7:
- Standard tool integration independent of AI model providers
- Exposes specialist QA tools over standard MCP JSON-RPC protocol
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure parent directory is in path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "backend"))
if str(_REPO_ROOT / "qa-engine") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "qa-engine"))
if str(_REPO_ROOT / "ai-engine") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "ai-engine"))

from agents import DefectRCAAgent, ReportingAgent, RequirementAgent, SecurityTestingAgent, UIHealingAgent
from quality_gate import PRESET_POLICIES, QualityGateInput, evaluate_policy_gate
from rag import RAGPipeline

MCP_TOOLS = [
    {
        "name": "audit_security_vulnerabilities",
        "description": "Execute automated DAST & SAST security audit on API request payloads, probing for SQLi, XSS, IDOR, PCI DSS data leakage, and prompt injection.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "payload": {"type": "object", "description": "Request payload dictionary or parameters to audit"},
                "endpoint": {"type": "string", "description": "Target API route being audited"},
                "role": {"type": "string", "description": "Caller user role (passenger, admin, anonymous)"},
            },
            "required": ["payload"],
        },
    },
    {
        "name": "diagnose_defect_rca",
        "description": "Analyze an error log, trace, or stack to perform specialist root cause analysis and recommend remediation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "log_text": {"type": "string", "description": "The raw error log or stacktrace"},
                "component": {"type": "string", "description": "Affected subsystem (e.g. payments, booking, search)"},
            },
            "required": ["log_text"],
        },
    },
    {
        "name": "generate_qa_test_cases",
        "description": "Generate comprehensive QA test cases (positive, negative, boundary, security) from a software requirement.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "requirement_text": {"type": "string", "description": "User story, API specification, or acceptance criteria"},
                "focus_area": {"type": "string", "description": "Optional focus area: API, UI, SECURITY, or DATA"},
            },
            "required": ["requirement_text"],
        },
    },
    {
        "name": "evaluate_quality_gate",
        "description": "Evaluate multi-signal telemetry (test results, defects, RAG score) against a release quality gate policy.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "policy_name": {"type": "string", "enum": ["PRODUCTION_STRICT", "STAGING_MODERATE", "CANARY_LENIENT"]},
                "total_tests": {"type": "integer"},
                "passed_tests": {"type": "integer"},
                "failed_tests": {"type": "integer"},
                "critical_defects": {"type": "integer"},
                "rag_groundedness_score": {"type": "number"},
            },
            "required": ["total_tests", "passed_tests", "failed_tests"],
        },
    },
    {
        "name": "query_rag_knowledge",
        "description": "Search grounded airline policy and QA documentation using vector retrieval and citation tracking.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language query about airline rules, NDC, or test policies"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "generate_release_report",
        "description": "Synthesize multi-signal quality gate telemetry into an executive markdown release sign-off report with GO/NO-GO deployment verdict.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "policy_name": {"type": "string", "description": "Gate policy (e.g. PRODUCTION_STRICT, STAGING_STANDARD)"},
                "total_tests": {"type": "integer", "description": "Total tests executed"},
                "passed_tests": {"type": "integer", "description": "Passed tests count"},
                "failed_tests": {"type": "integer", "description": "Failed tests count"},
                "critical_defects": {"type": "integer", "description": "Active critical defects count"},
                "contract_failures": {"type": "integer", "description": "Schema contract failure count"},
                "security_vulnerabilities": {"type": "integer", "description": "Security audit findings count"},
                "rag_groundedness_score": {"type": "number", "description": "RAG groundedness score (0.0 - 1.0)"},
                "quality_gate_status": {"type": "string", "description": "Quality gate status (PASSED/BLOCKED)"},
                "violations": {"type": "array", "items": {"type": "string"}, "description": "Gate policy violations"},
            },
            "required": ["total_tests", "passed_tests"],
        },
    },
    {
        "name": "heal_playwright_selector",
        "description": "Analyze broken Playwright UI test locator and DOM snippet to synthesize resilient, accessible W3C ARIA locators.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "broken_selector": {"type": "string", "description": "The failed selector (e.g. xpath, fragile CSS class)"},
                "dom_snippet": {"type": "string", "description": "HTML snippet surrounding the target element"},
                "failure_message": {"type": "string", "description": "Playwright error message or timeout trace"},
                "target_action": {"type": "string", "description": "Action being performed (click, fill, check)"},
            },
            "required": ["broken_selector", "dom_snippet"],
        },
    },
]


def list_tools() -> List[Dict[str, Any]]:
    """Returns all available MCP tool definitions."""
    return MCP_TOOLS


def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatches a tool call and returns an MCP-compliant structured response."""
    start_time = time.time()

    if name == "audit_security_vulnerabilities":
        agent = SecurityTestingAgent()
        payload = arguments.get("payload", {})
        endpoint = arguments.get("endpoint", "/api")
        role = arguments.get("role", "passenger")

        run = asyncio.run(
            agent.execute(
                f"Audit endpoint {endpoint}",
                {"payload": payload, "endpoint": endpoint, "role": role},
            )
        )
        report_data = json.loads(run.output or "{}")

        return {
            "tool": name,
            "status": "success",
            "result": report_data,
            "latency_ms": int((time.time() - start_time) * 1000),
        }

    elif name == "diagnose_defect_rca":
        agent = DefectRCAAgent()
        log_text = arguments.get("log_text", "")
        component = arguments.get("component", "system")

        context = {"error_msg": log_text, "endpoint": component}
        if "timeout" in log_text.lower() or "3ds" in log_text.lower():
            context["status_code"] = 504
            context["failure_code"] = "3DS_TIMEOUT"
        elif "insufficient" in log_text.lower() or "conflict" in log_text.lower():
            context["status_code"] = 409
        elif "not found" in log_text.lower():
            context["status_code"] = 404

        run = asyncio.run(agent.execute(f"Diagnose failure in {component}", context))
        diag_event = next((e for e in reversed(run.events) if e.event_type == "RCA_DIAGNOSED"), None)
        meta = diag_event.metadata if diag_event else {}

        return {
            "tool": name,
            "status": "success",
            "result": {
                "category": meta.get("diagnosis", "UNKNOWN_FAILURE"),
                "severity": meta.get("severity", "MEDIUM"),
                "output": run.output,
                "recommended_fix": "Verify service logs and request payload.",
            },
            "latency_ms": int((time.time() - start_time) * 1000),
        }

    elif name == "generate_qa_test_cases":
        agent = RequirementAgent()
        req_text = arguments.get("requirement_text", "")
        focus_area = arguments.get("focus_area", "API")

        run = asyncio.run(agent.execute(req_text, {"focus_area": focus_area}))
        scenarios = [s.strip() for s in (run.output or "").split("\n") if s.strip()]

        return {
            "tool": name,
            "status": "success",
            "result": {
                "requirement": req_text,
                "test_count": len(scenarios),
                "test_cases": scenarios,
                "status": run.status,
            },
            "latency_ms": int((time.time() - start_time) * 1000),
        }

    elif name == "evaluate_quality_gate":
        policy_name = arguments.get("policy_name", "PRODUCTION_STRICT")
        policy = PRESET_POLICIES.get(policy_name, PRESET_POLICIES["PRODUCTION_STRICT"])

        gate_input = QualityGateInput(
            total_tests=arguments.get("total_tests", 0),
            passed_tests=arguments.get("passed_tests", 0),
            failed_tests=arguments.get("failed_tests", 0),
            critical_defects=arguments.get("critical_defects", 0),
            rag_groundedness_score=arguments.get("rag_groundedness_score"),
        )
        gate_res = evaluate_policy_gate(gate_input, policy)
        return {
            "tool": name,
            "status": "success",
            "result": {
                "passed": gate_res.passed,
                "status": gate_res.status,
                "pass_rate": gate_res.pass_rate,
                "violations": gate_res.violations,
            },
            "latency_ms": int((time.time() - start_time) * 1000),
        }

    elif name == "query_rag_knowledge":
        pipeline = RAGPipeline()
        pipeline.ingest_document(
            document_id="airline_handbook",
            text="Baggage allowance permits 1 carry-on up to 8kg free. Standard checked bags are 23kg at 35 EUR. Extra legroom exit row seats cost 45 EUR. Refunds are issued on cancelled tickets within 48 hours.",
        )
        rag_res = pipeline.query(arguments.get("query", ""))
        return {
            "tool": name,
            "status": "success",
            "result": {
                "answer": rag_res.answer,
                "citations": rag_res.citations,
                "retrieved_count": len(rag_res.retrieved_chunks),
            },
            "latency_ms": int((time.time() - start_time) * 1000),
        }

    elif name == "generate_release_report":
        agent = ReportingAgent()
        run = asyncio.run(
            agent.execute(
                task="Synthesize quality signals into executive release report",
                context=arguments,
            )
        )
        return {
            "tool": name,
            "status": "success",
            "result": {
                "run_id": run.run_id,
                "report_markdown": run.output,
                "events_count": len(run.events),
            },
            "latency_ms": int((time.time() - start_time) * 1000),
        }

    elif name == "heal_playwright_selector":
        agent = UIHealingAgent()
        run = asyncio.run(
            agent.execute(
                task="Synthesize resilient Playwright locator",
                context=arguments,
            )
        )
        report_data = json.loads(run.output or "{}")
        return {
            "tool": name,
            "status": "success",
            "result": report_data,
            "latency_ms": int((time.time() - start_time) * 1000),
        }

    else:
        raise ValueError(f"Unknown tool: '{name}'. Supported: {[t['name'] for t in MCP_TOOLS]}")


def handle_jsonrpc(request: Dict[str, Any]) -> Dict[str, Any]:
    """Processes an incoming JSON-RPC 2.0 MCP request."""
    method = request.get("method")
    req_id = request.get("id")

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": list_tools()},
        }
    elif method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})
        try:
            res = call_tool(tool_name, args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]},
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(e)},
            }
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method '{method}' not found"},
        }


if __name__ == "__main__":
    # Simple stdio JSON-RPC loop for testing
    print(f"QA Intelligence Hub MCP Server ready. Exposed tools: {len(MCP_TOOLS)}", file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            response = handle_jsonrpc(req)
            print(json.dumps(response))
            sys.stdout.flush()
        except Exception as err:
            err_resp = {"jsonrpc": "2.0", "error": {"code": -32700, "message": str(err)}}
            print(json.dumps(err_resp))
            sys.stdout.flush()
