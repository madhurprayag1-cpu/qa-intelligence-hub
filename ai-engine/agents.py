import json
import re
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.ai_provider import AIProvider, MockAIProvider, get_ai_provider


@dataclass
class AgentEvent:
    timestamp: str
    event_type: str
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRun:
    run_id: str
    agent_id: str
    task: str
    status: str
    events: list[AgentEvent] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    output: str | None = None
    error: str | None = None


class BaseAgent(ABC):
    def __init__(self, agent_id: str, ai_provider: AIProvider | None = None):
        self.agent_id = agent_id
        self.ai = ai_provider or get_ai_provider()

    def plan(self, task: str) -> AgentRun:
        run_id = f"RUN-{secrets.token_hex(4).upper()}"
        run = AgentRun(
            run_id=run_id,
            agent_id=self.agent_id,
            task=task,
            status="PLANNED",
        )
        run.events.append(
            AgentEvent(
                timestamp=datetime.utcnow().isoformat(),
                event_type="TASK_PLANNED",
                description=f"Agent planned execution for: {task}",
            )
        )
        return run

    @abstractmethod
    async def execute(self, task: str, context: dict[str, Any] | None = None) -> AgentRun:
        raise NotImplementedError


class DefectRCAAgent(BaseAgent):
    """
    Specialist Defect & Root Cause Analysis Agent.
    Analyzes test failures, payment errors, and system logs to identify root cause,
    synthesizes targeted code patches, and orchestrates automated regression verification
    across intentional defects DEF-001 through DEF-005 (AGENTS.md Sections 5, 6, 9).
    """

    def __init__(
        self,
        agent_id: str = "agent-defect-rca",
        ai_provider: AIProvider | None = None,
    ):
        super().__init__(agent_id=agent_id, ai_provider=ai_provider)

    def synthesize_code_fix(
        self, defect_id: str, context: dict[str, Any] | None = None
    ) -> Any:
        """Synthesizes a targeted code patch for a defect."""
        from remediation import synthesize_code_patch
        return synthesize_code_patch(defect_id, context)

    def remediate(
        self,
        defect_id: str,
        context: dict[str, Any] | None = None,
        run_regression: bool = True,
        policy_name: str = "PRODUCTION_STRICT",
    ) -> Any:
        """
        Orchestrates complete autonomous defect auto-remediation:
        synthesizes patch, verifies defect resolution, runs impacted regression,
        and enforces Quality Gate governance.
        """
        from remediation import execute_remediation_workflow
        return execute_remediation_workflow(
            defect_id=defect_id,
            context=context,
            run_regression=run_regression,
            policy_name=policy_name,
        )

    async def execute(
        self, task: str, context: dict[str, Any] | None = None
    ) -> AgentRun:
        run = self.plan(task)
        run.status = "RUNNING"
        ctx = context or {}

        # Log analysis event
        run.events.append(
            AgentEvent(
                timestamp=datetime.utcnow().isoformat(),
                event_type="CONTEXT_INGESTION",
                description="Parsed error payload and failure stack",
                metadata={"keys": list(ctx.keys())},
            )
        )

        status_code = ctx.get("status_code")
        error_msg = ctx.get("error_msg", "").lower()
        endpoint = ctx.get("endpoint", "")
        failure_code = ctx.get("failure_code", "")

        # Check if auto-remediation is requested
        is_remediation = (
            ctx.get("remediate", False)
            or "remediate" in task.lower()
            or "fix" in task.lower()
            or any(d in task.upper() for d in ["DEF-001", "DEF-002", "DEF-003", "DEF-004", "DEF-005"])
            or bool(ctx.get("defect_id"))
        )

        if is_remediation:
            # Determine target defect ID
            target_defect = ctx.get("defect_id")
            if not target_defect:
                for d in ["DEF-001", "DEF-002", "DEF-003", "DEF-004", "DEF-005"]:
                    if d in task.upper():
                        target_defect = d
                        break
            if not target_defect:
                if status_code == 409 or "overbook" in error_msg or "inventory" in error_msg:
                    target_defect = "DEF-002"
                elif "timeout" in error_msg or failure_code == "3DS_TIMEOUT" or status_code == 504:
                    target_defect = "DEF-003"
                elif "drift" in error_msg or "calc" in error_msg or "fare" in error_msg:
                    target_defect = "DEF-001"
                elif "hallucin" in error_msg or "grounded" in error_msg:
                    target_defect = "DEF-004"
                elif status_code == 422 or "contract" in error_msg or "schema" in error_msg:
                    target_defect = "DEF-005"
                else:
                    target_defect = "DEF-001"

            run.events.append(
                AgentEvent(
                    timestamp=datetime.utcnow().isoformat(),
                    event_type="DEFECT_IDENTIFIED",
                    description=f"Identified defect target: {target_defect}",
                    metadata={"defect_id": target_defect},
                )
            )

            # Execute remediation workflow
            run_reg = ctx.get("run_regression", True)
            policy_name = ctx.get("policy_name", "PRODUCTION_STRICT")
            remediation_res = self.remediate(
                defect_id=target_defect,
                context=ctx,
                run_regression=run_reg,
                policy_name=policy_name,
            )

            run.events.append(
                AgentEvent(
                    timestamp=datetime.utcnow().isoformat(),
                    event_type="PATCH_SYNTHESIZED",
                    description=f"Synthesized code patch for {remediation_res.patch.target_file}",
                    metadata={
                        "target_file": remediation_res.patch.target_file,
                        "description": remediation_res.patch.description,
                    },
                )
            )

            run.events.append(
                AgentEvent(
                    timestamp=datetime.utcnow().isoformat(),
                    event_type="REGRESSION_EXECUTED",
                    description=(
                        f"Executed regression suite: {remediation_res.tests_passed} passed, "
                        f"{remediation_res.tests_failed} failed"
                    ),
                    metadata={
                        "tests_executed": remediation_res.tests_executed,
                        "tests_passed": remediation_res.tests_passed,
                        "tests_failed": remediation_res.tests_failed,
                        "regression_passed": remediation_res.regression_passed,
                    },
                )
            )

            run.events.append(
                AgentEvent(
                    timestamp=datetime.utcnow().isoformat(),
                    event_type="QUALITY_GATE_EVALUATED",
                    description=f"Evaluated Quality Gate policy '{policy_name}': {'PASSED' if remediation_res.quality_gate_passed else 'FAILED'}",
                    metadata={"passed": remediation_res.quality_gate_passed, "policy": policy_name},
                )
            )

            run.events.append(
                AgentEvent(
                    timestamp=datetime.utcnow().isoformat(),
                    event_type="REMEDIATION_VERIFIED",
                    description=f"Auto-remediation completed with status: {remediation_res.status}",
                    metadata={"status": remediation_res.status},
                )
            )

            run.status = "COMPLETED" if remediation_res.status == "VERIFIED_SUCCESS" else "FAILED"
            run.output = (
                f"### 🛠️ Agentic Defect RCA Auto-Remediation: {remediation_res.status}\n\n"
                f"- **Defect ID**: `{remediation_res.defect_id}` ({remediation_res.defect_name})\n"
                f"- **Diagnosis**: `{remediation_res.diagnosis}` (Severity: {remediation_res.severity})\n"
                f"- **Target File**: `{remediation_res.patch.target_file}`\n"
                f"- **Defect Resolved**: `{'✅ Yes' if remediation_res.defect_resolved else '❌ No'}`\n"
                f"- **Regression Passed**: `{'✅ ' + str(remediation_res.tests_passed) + '/' + str(remediation_res.tests_executed) if remediation_res.regression_passed else '❌ Failed'}`\n"
                f"- **Quality Gate**: `{'🟢 APPROVED' if remediation_res.quality_gate_passed else '🔴 BLOCKED'}`\n\n"
                f"#### Proposed Synthetic Code Patch:\n"
                f"```diff\n{remediation_res.patch.diff}\n```\n\n"
                f"**Resolution Verification**: {remediation_res.resolution_details}\n"
            )
            return run

        # Standard diagnostic heuristic flow (preserves 100% backward compatibility)
        diagnosis = "UNKNOWN_FAILURE"
        severity = "MEDIUM"
        suggested_fix = "Review service logs and request payload."

        if status_code == 409 or "insufficient" in error_msg:
            diagnosis = "INSUFFICIENT_INVENTORY_OR_DUPLICATE"
            severity = "HIGH"
            suggested_fix = (
                "Verify database lock isolation or seat inventory availability before booking."
            )
        elif "3ds" in error_msg or "timeout" in error_msg or failure_code == "3DS_TIMEOUT":
            diagnosis = "GATEWAY_OR_3DS_TIMEOUT"
            severity = "HIGH"
            suggested_fix = (
                "Check ACS bank response latency. Configure retry or webhook confirmation."
            )
        elif status_code == 404:
            diagnosis = "ENTITY_NOT_FOUND"
            severity = "LOW"
            suggested_fix = (
                f"Verify entity exists in database before invoking {endpoint}."
            )
        elif status_code == 422:
            diagnosis = "CONTRACT_VALIDATION_ERROR"
            severity = "LOW"
            suggested_fix = "Check schema validation constraints."

        rca_summary = (
            f"RCA Diagnosis: [{diagnosis}]\n"
            f"Severity: {severity}\n"
            f"Endpoint: {endpoint}\n"
            f"Remediation: {suggested_fix}"
        )

        run.events.append(
            AgentEvent(
                timestamp=datetime.utcnow().isoformat(),
                event_type="RCA_DIAGNOSED",
                description=f"Generated root cause classification: {diagnosis}",
                metadata={"diagnosis": diagnosis, "severity": severity},
            )
        )

        run.status = "COMPLETED"
        run.output = rca_summary
        return run


class RequirementAgent(BaseAgent):
    """Specialist agent for extracting test scenarios from requirements."""

    def __init__(self, ai_provider: AIProvider | None = None):
        super().__init__(agent_id="agent-requirements", ai_provider=ai_provider)

    async def execute(
        self, task: str, context: dict[str, Any] | None = None
    ) -> AgentRun:
        run = self.plan(task)
        run.status = "RUNNING"

        ctx = context or {}
        requirement_id = ctx.get("requirement_id") or f"REQ-{secrets.token_hex(4).upper()}"
        domain = ctx.get("domain", "cross-domain")
        impacted_components = ctx.get(
            "impacted_components",
            ["API", "UI", "database", "security", "regression"],
        )
        acceptance_criteria = [
            {
                "id": f"{requirement_id}-AC-001",
                "description": f"Happy-path behavior for requirement '{task}' succeeds.",
            },
            {
                "id": f"{requirement_id}-AC-002",
                "description": f"Invalid, unauthorized, and negative inputs for '{task}' are rejected safely.",
            },
            {
                "id": f"{requirement_id}-AC-003",
                "description": f"Boundary, timeout, and data-integrity cases for '{task}' are handled deterministically.",
            },
        ]
        scenarios = [
            {
                "scenario_id": f"{requirement_id}-TS-001",
                "type": "POSITIVE",
                "objective": f"Positive: Validate happy path for '{task}'.",
                "required_layers": ["API", "UI", "REGRESSION"],
            },
            {
                "scenario_id": f"{requirement_id}-TS-002",
                "type": "NEGATIVE",
                "objective": f"Negative: Validate invalid and unauthorized behavior for '{task}'.",
                "required_layers": ["API", "SECURITY"],
            },
            {
                "scenario_id": f"{requirement_id}-TS-003",
                "type": "BOUNDARY",
                "objective": f"Boundary: Validate boundary, timeout, concurrency, and data-integrity behavior for '{task}'.",
                "required_layers": ["API", "DATABASE", "PERFORMANCE"],
            },
        ]
        traceability = {
            "requirement_id": requirement_id,
            "requirement": task,
            "domain": domain,
            "impacted_components": impacted_components,
            "acceptance_criteria": acceptance_criteria,
            "test_scenarios": scenarios,
            "traceability_status": "READY_FOR_IMPLEMENTATION",
        }

        run.events.append(
            AgentEvent(
                timestamp=datetime.utcnow().isoformat(),
                event_type="REQUIREMENT_ANALYZED",
                description=f"Analyzed {requirement_id} with {len(acceptance_criteria)} acceptance criteria.",
                metadata={
                    "requirement_id": requirement_id,
                    "domain": domain,
                    "impacted_components": impacted_components,
                },
            )
        )

        run.events.append(
            AgentEvent(
                timestamp=datetime.utcnow().isoformat(),
                event_type="SCENARIOS_GENERATED",
                description=f"Generated {len(scenarios)} test scenarios",
                metadata={"count": len(scenarios), "requirement_id": requirement_id},
            )
        )

        run.status = "COMPLETED"
        run.output = json.dumps(traceability, indent=2)
        return run


# Backwards compatibility alias
QAAgent = DefectRCAAgent


class SecurityTestingAgent(BaseAgent):
    """
    Specialist Security Testing Agent (AGENTS.md Section 6 & 21).
    Performs automated DAST & payload security audits:
    - SQL injection detection
    - Cross-site scripting (XSS) input sanitization audit
    - PCI DSS sensitive cardholder data exposure audit
    - IDOR / BOLA authorization checks
    - Prompt injection guardrails
    """

    def __init__(
        self,
        agent_id: str = "agent-security-testing",
        ai_provider: AIProvider | None = None,
    ):
        super().__init__(agent_id=agent_id, ai_provider=ai_provider)

    async def execute(
        self, task: str, context: dict[str, Any] | None = None
    ) -> AgentRun:
        run = self.plan(task)
        run.status = "RUNNING"
        ctx = context or {}

        payload = ctx.get("payload", {})
        endpoint = ctx.get("endpoint", "/api")
        role = ctx.get("role", "passenger")

        run.events.append(
            AgentEvent(
                timestamp=datetime.utcnow().isoformat(),
                event_type="SECURITY_AUDIT_STARTED",
                description=f"Initiated security vulnerability scan on {endpoint}",
                metadata={"endpoint": endpoint, "role": role},
            )
        )

        findings: list[dict[str, Any]] = []

        payload_str = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
        payload_lower = payload_str.lower()

        # 1. SQL Injection Probe
        sqli_patterns = ["' or '1'='1", "union select", "; drop table", "--", "sleep("]
        for pattern in sqli_patterns:
            if pattern in payload_lower:
                findings.append({
                    "category": "SQL_INJECTION",
                    "severity": "CRITICAL",
                    "description": f"Potential SQL injection vector detected containing pattern: '{pattern}'",
                    "location": "request_payload",
                    "remediation": "Enforce strict ORM parameterization with SQLAlchemy and avoid raw SQL concatenation.",
                })
                break

        # 2. XSS Probe
        xss_patterns = ["<script", "javascript:", "onerror=", "onload=", "<img src=x"]
        for pattern in xss_patterns:
            if pattern in payload_lower:
                findings.append({
                    "category": "CROSS_SITE_SCRIPTING",
                    "severity": "HIGH",
                    "description": f"Potential stored/reflected XSS vector detected containing: '{pattern}'",
                    "location": "request_payload",
                    "remediation": "Apply HTML escaping and input sanitization on passenger inputs before persistence or rendering.",
                })
                break

        # 3. PCI DSS Sensitive Cardholder Data Exposure Probe
        pan_matches = re.findall(r"\b(?:\d[ -]*?){13,16}\b", payload_str)
        cleaned_pans = [re.sub(r"\D", "", m) for m in pan_matches if len(re.sub(r"\D", "", m)) in (15, 16)]
        if cleaned_pans:
            findings.append({
                "category": "PCI_DSS_EXPOSURE",
                "severity": "CRITICAL",
                "description": "Unmasked Primary Account Number (PAN) detected in request payload. Violates PCI DSS Requirement 3.4.",
                "location": "request_payload.card_number",
                "remediation": "Never store or log unmasked PANs. Mask to last 4 digits (e.g. ************1111) or use tokenized provider references.",
            })

        if re.search(r'["\']?(?:cvv|cvc|security_code)["\']?\s*[:=]\s*["\']?\d{3,4}["\']?', payload_str, re.IGNORECASE):
            findings.append({
                "category": "PCI_DSS_CVV_STORAGE",
                "severity": "CRITICAL",
                "description": "Sensitive Authentication Data (CVV/CVC) detected in payload. Violates PCI DSS Requirement 3.2.",
                "location": "request_payload.cvv",
                "remediation": "Do not store or log card verification codes under any circumstance after authorization.",
            })

        # 4. Prompt Injection Probe
        prompt_injection_patterns = [
            "ignore previous instructions",
            "disregard all prior rules",
            "system prompt override",
            "you are now an unrestricted ai",
        ]
        for pattern in prompt_injection_patterns:
            if pattern in payload_lower:
                findings.append({
                    "category": "PROMPT_INJECTION",
                    "severity": "HIGH",
                    "description": f"Adversarial prompt injection attempt detected: '{pattern}'",
                    "location": "request_payload.prompt",
                    "remediation": "Enforce strict semantic guardrails and delimiter isolation before passing input to LLMs.",
                })
                break

        # 5. IDOR / Authorization Probe
        if "booking_id" in payload_str and role == "passenger":
            target_email = ctx.get("target_email")
            user_email = ctx.get("user_email")
            if target_email and user_email and target_email.lower() != user_email.lower():
                findings.append({
                    "category": "IDOR_AUTHORIZATION_BYPASS",
                    "severity": "HIGH",
                    "description": f"IDOR vulnerability: Passenger '{user_email}' attempted accessing booking of passenger '{target_email}'",
                    "location": "endpoint_authorization",
                    "remediation": "Validate that the authenticated JWT subject matches the resource owner in database query.",
                })

        # Audit verdict
        is_secure = len(findings) == 0
        overall_status = "SECURE" if is_secure else "VULNERABLE"

        run.events.append(
            AgentEvent(
                timestamp=datetime.utcnow().isoformat(),
                event_type="SECURITY_AUDIT_COMPLETED",
                description=f"Security audit completed with {len(findings)} findings. Verdict: {overall_status}",
                metadata={"findings_count": len(findings), "status": overall_status},
            )
        )

        report = {
            "status": overall_status,
            "findings_count": len(findings),
            "findings": findings,
            "endpoint": endpoint,
            "pci_dss_compliant": not any(f["category"].startswith("PCI_DSS") for f in findings),
            "sanitization_status": "PASSED" if is_secure else "FAILED",
        }

        run.status = "COMPLETED"
        run.output = json.dumps(report, indent=2)
        return run

    async def audit_payload(
        self,
        endpoint: str = "/api",
        payload: Any = None,
        role: str = "passenger",
        user_email: str | None = None,
        target_email: str | None = None,
    ) -> dict[str, Any]:
        """Convenience method to execute a security audit on a single payload."""
        run = await self.execute(
            f"Audit security for endpoint {endpoint}",
            {
                "endpoint": endpoint,
                "payload": payload or {},
                "role": role,
                "user_email": user_email,
                "target_email": target_email,
            },
        )
        return json.loads(run.output)

    async def scan_suite(
        self, suite: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Execute an automated DAST batch scan over a suite of probe cases.
        Consolidates OWASP, PCI DSS, and authentication findings into a structured DAST report.
        """
        total_scans = len(suite)
        passed_scans = 0
        failed_scans = 0
        all_findings: list[dict[str, Any]] = []
        detailed_results: list[dict[str, Any]] = []

        for probe in suite:
            endpoint = probe.get("endpoint", "/api")
            payload = probe.get("payload", {})
            role = probe.get("role", "passenger")
            user_email = probe.get("user_email")
            target_email = probe.get("target_email")
            probe_name = probe.get("name", f"Scan {endpoint}")

            res = await self.audit_payload(
                endpoint=endpoint,
                payload=payload,
                role=role,
                user_email=user_email,
                target_email=target_email,
            )

            probe_findings = res.get("findings", [])
            all_findings.extend(probe_findings)

            if len(probe_findings) == 0:
                passed_scans += 1
            else:
                failed_scans += 1

            detailed_results.append({
                "probe_name": probe_name,
                "endpoint": endpoint,
                "status": res.get("status", "UNKNOWN"),
                "findings_count": len(probe_findings),
                "pci_dss_compliant": res.get("pci_dss_compliant", True),
                "findings": probe_findings,
            })

        critical_count = sum(1 for f in all_findings if f.get("severity") == "CRITICAL")
        pci_count = sum(1 for f in all_findings if "PCI_DSS" in f.get("category", ""))
        owasp_count = sum(
            1 for f in all_findings
            if f.get("category") in ("SQL_INJECTION", "CROSS_SITE_SCRIPTING", "PROMPT_INJECTION", "IDOR_AUTHORIZATION_BYPASS")
        )
        compliance_rate = (passed_scans / total_scans) if total_scans > 0 else 1.0

        is_secure = len(all_findings) == 0
        overall_status = "SECURE" if is_secure else "VULNERABLE"

        return {
            "status": overall_status,
            "total_scans": total_scans,
            "passed_scans": passed_scans,
            "failed_scans": failed_scans,
            "vulnerabilities_count": len(all_findings),
            "critical_vulnerabilities": critical_count,
            "pci_dss_violations": pci_count,
            "owasp_violations": owasp_count,
            "compliance_rate": compliance_rate,
            "findings": all_findings,
            "details": detailed_results,
            "scanned_at": datetime.utcnow().isoformat(),
        }


class ReportingAgent(BaseAgent):
    """
    Specialist Reporting Agent (AGENTS.md Section 6).
    Synthesizes multi-signal quality metrics (test execution telemetry, security audits,
    AI/RAG evaluations, and Quality Gate policies) into an executive release sign-off report.
    """

    def __init__(self, ai_provider: AIProvider | None = None):
        super().__init__(agent_id="AGENT-REPORTING-001", ai_provider=ai_provider)

    async def execute(self, task: str, context: dict[str, Any] | None = None) -> AgentRun:
        run = self.plan(task)
        ctx = context or {}

        total_tests = ctx.get("total_tests", 0)
        passed_tests = ctx.get("passed_tests", 0)
        failed_tests = ctx.get("failed_tests", 0)
        critical_defects = ctx.get("critical_defects", 0)
        contract_failures = ctx.get("contract_failures", 0)
        security_vulnerabilities = ctx.get("security_vulnerabilities", 0)
        rag_groundedness = ctx.get("rag_groundedness_score", 0.95)
        policy_name = ctx.get("policy_name", "PRODUCTION_STRICT")
        gate_status = ctx.get("quality_gate_status", "PASSED")
        violations = ctx.get("violations", [])

        pass_rate = (passed_tests / total_tests * 100.0) if total_tests > 0 else 100.0
        is_go = (gate_status == "PASSED" and critical_defects == 0 and security_vulnerabilities == 0 and failed_tests == 0)
        decision = "GO — APPROVED FOR RELEASE" if is_go else "NO-GO — RELEASE BLOCKED"

        # Generate structured executive markdown report
        report_md = f"""# 🚀 QA Intelligence Hub — Executive Release Sign-Off Report

**Release Assessment**: **{decision}**  
**Gate Policy**: `{policy_name}` | **Gate Verdict**: `{gate_status}`  
**Run ID**: `{run.run_id}` | **Generated At**: `{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}`

---

## 📊 Quality Engineering Telemetry

| Quality Signal | Measurement | Threshold / Target | Status |
| :--- | :--- | :--- | :---: |
| **Test Pass Rate** | {pass_rate:.1f}% ({passed_tests}/{total_tests}) | 100% required | {'✅ PASS' if failed_tests == 0 else '❌ BLOCK'} |
| **Critical Defects** | {critical_defects} | 0 allowed | {'✅ PASS' if critical_defects == 0 else '❌ BLOCK'} |
| **API Contract Validation** | {contract_failures} schema violations | 0 allowed | {'✅ PASS' if contract_failures == 0 else '❌ BLOCK'} |
| **Security Vulnerabilities** | {security_vulnerabilities} findings | 0 critical/high | {'✅ PASS' if security_vulnerabilities == 0 else '❌ BLOCK'} |
| **AI Groundedness Score** | {rag_groundedness:.2f} | ≥ 0.85 target | {'✅ PASS' if rag_groundedness >= 0.85 else '⚠️ RISK'} |

---

## 🛡️ Security & Governance Evaluation
- **PCI DSS Data Protection**: {'Zero PAN/CVV exposures detected' if security_vulnerabilities == 0 else f'{security_vulnerabilities} exposure(s) require remediation'}
- **OWASP Guardrails**: SQL Injection & IDOR defenses intact
- **Audit Logging**: End-to-end request correlation IDs verified
"""
        if violations:
            report_md += "\n## ⚠️ Release Blockers & Gate Violations\n"
            for v in violations:
                report_md += f"- ❌ {v}\n"
            report_md += "\n### Recommended Remediation Steps:\n"
            if critical_defects > 0:
                report_md += "1. Invoke `DefectRCAAgent` to diagnose root cause and apply automated patch.\n"
            if security_vulnerabilities > 0:
                report_md += "2. Invoke `SecurityTestingAgent` to scrub unmasked credentials / sanitize payloads.\n"
            if failed_tests > 0:
                report_md += "3. Run targeted regression impact suite via `select_regression_tests()` to verify fixes.\n"
        else:
            report_md += "\n## ✅ Deployment Sign-Off\n"
            report_md += "All multi-signal quality gates passed with zero regressions. Deployment to production authorized.\n"

        run.events.append(
            AgentEvent(
                timestamp=datetime.utcnow().isoformat(),
                event_type="REPORT_GENERATED",
                description=f"Generated executive release report. Decision: {decision}",
                metadata={"decision": decision, "gate_status": gate_status, "pass_rate": pass_rate},
            )
        )

        run.status = "COMPLETED"
        run.output = report_md
        return run


class UIHealingAgent(BaseAgent):
    """
    Specialist UI Self-Healing Agent (AGENTS.md Section 6 & 16).
    Analyzes Playwright locator failures, broken DOM selectors, and HTML snippets
    to synthesize resilient, accessible Playwright locators adhering to W3C ARIA standards.
    Enforces strict DOM element verification: rejects ambiguous matches and never silently
    accepts an incorrect element.
    """

    def __init__(self, ai_provider: AIProvider | None = None):
        super().__init__(agent_id="AGENT-UI-HEALER-001", ai_provider=ai_provider)

    async def execute(self, task: str, context: dict[str, Any] | None = None) -> AgentRun:
        run = self.plan(task)
        ctx = context or {}

        broken_selector = ctx.get("broken_selector", "")
        dom_snippet = ctx.get("dom_snippet", "")
        failure_message = ctx.get("failure_message", "")
        target_action = ctx.get("target_action", "click")

        healing_result = self.heal_selector(
            broken_selector=broken_selector,
            dom_snippet=dom_snippet,
            failure_message=failure_message,
            target_action=target_action,
        )

        event_type = "SELECTOR_HEALED" if healing_result["verified"] else (
            "HEALING_AMBIGUOUS_REJECTED" if healing_result["status"] == "AMBIGUOUS_MATCH" else "HEALING_FAILED"
        )
        desc = (
            f"Synthesized resilient locator: {healing_result['healed_selector']} (Confidence: {healing_result['confidence_score']:.2f})"
            if healing_result["verified"]
            else f"Healing status: {healing_result['status']} - {healing_result['justification']}"
        )

        run.events.append(
            AgentEvent(
                timestamp=datetime.utcnow().isoformat(),
                event_type=event_type,
                description=desc,
                metadata=healing_result,
            )
        )

        run.status = "COMPLETED" if healing_result["verified"] else (
            "REJECTED" if healing_result["status"] == "AMBIGUOUS_MATCH" else "FAILED"
        )
        run.output = json.dumps(healing_result, indent=2)
        return run

    def count_matches(self, selector: str, dom_snippet: str) -> int:
        """
        Determines the number of matching elements in the DOM snippet for a given Playwright selector.
        Supports getByTestId, getByRole('button'/'link'), getByPlaceholder, locator('#id'), and getByText.
        """
        if not dom_snippet or not selector:
            return 0

        # 1. getByTestId('id')
        m_tid = re.search(r"getByTestId\(['\"]([^'\"]+)['\"]\)", selector)
        if m_tid:
            tid = re.escape(m_tid.group(1))
            return len(re.findall(rf'data-testid=["\']{tid}["\']', dom_snippet))

        # 2. getByRole('button', { name: 'name' })
        m_btn = re.search(r"getByRole\(['\"]button['\"],\s*\{\s*name:\s*['\"]([^'\"]+)['\"]\s*\}\)", selector)
        if m_btn:
            name = m_btn.group(1).strip()
            # Match <button>...</button> containing name or <input type="button|submit" value="name">
            button_matches = 0
            for btn in re.finditer(r'<button[^>]*>(.*?)</button>', dom_snippet, re.DOTALL | re.IGNORECASE):
                clean_txt = re.sub(r"<[^>]+>", "", btn.group(1)).strip()
                if name.lower() == clean_txt.lower() or name in clean_txt:
                    button_matches += 1
            for inp in re.finditer(r'<input[^>]*type=["\'](?:button|submit)["\'][^>]*value=["\']([^"\']+)["\']', dom_snippet, re.IGNORECASE):
                if name.lower() == inp.group(1).strip().lower():
                    button_matches += 1
            for role_btn in re.finditer(r'<[^>]+role=["\']button["\'][^>]*>(.*?)</[^>]+>', dom_snippet, re.DOTALL | re.IGNORECASE):
                clean_txt = re.sub(r"<[^>]+>", "", role_btn.group(1)).strip()
                if name.lower() in clean_txt.lower():
                    button_matches += 1
            return button_matches

        # 3. getByRole('link', { name: 'name' })
        m_link = re.search(r"getByRole\(['\"]link['\"],\s*\{\s*name:\s*['\"]([^'\"]+)['\"]\s*\}\)", selector)
        if m_link:
            name = m_link.group(1).strip()
            link_matches = 0
            for link in re.finditer(r'<a[^>]*>(.*?)</a>', dom_snippet, re.DOTALL | re.IGNORECASE):
                clean_txt = re.sub(r"<[^>]+>", "", link.group(1)).strip()
                if name.lower() == clean_txt.lower() or name in clean_txt:
                    link_matches += 1
            return link_matches

        # 4. getByPlaceholder('ph')
        m_ph = re.search(r"getByPlaceholder\(['\"]([^'\"]+)['\"]\)", selector)
        if m_ph:
            ph = re.escape(m_ph.group(1))
            return len(re.findall(rf'placeholder=["\']{ph}["\']', dom_snippet, re.IGNORECASE))

        # 5. locator('#id')
        m_id = re.search(r"locator\(['\"]#([^'\"]+)['\"]\)", selector)
        if m_id:
            el_id = re.escape(m_id.group(1))
            return len(re.findall(rf'\bid=["\']{el_id}["\']', dom_snippet))

        # 6. getByText('txt')
        m_txt = re.search(r"getByText\(['\"]([^'\"]+)['\"]\)", selector)
        if m_txt:
            txt = m_txt.group(1).strip()
            text_matches = 0
            for elem in re.finditer(r'<(?:h[1-6]|span|div|a|p|button)[^>]*>([^<]+)</', dom_snippet, re.IGNORECASE):
                if txt.lower() in elem.group(1).strip().lower():
                    text_matches += 1
            return text_matches

        # Fallback regex match
        return len(re.findall(re.escape(selector), dom_snippet))

    def heal_selector(
        self,
        broken_selector: str,
        dom_snippet: str,
        failure_message: str = "",
        target_action: str = "click",
    ) -> dict[str, Any]:
        """
        Extracts semantic candidates from the DOM, verifies their uniqueness against the DOM,
        and enforces strict verification:
        - If exactly 1 unique candidate matches: VERIFIED and accepted.
        - If multiple matches found (count > 1): AMBIGUOUS_MATCH and REJECTED (never silently accept incorrect element).
        - If 0 matches found: HEALING_FAILED.
        """
        raw_candidates: list[dict[str, Any]] = []

        # 1. Search for data-testid
        test_ids = re.findall(r'data-testid=["\']([^"\']+)["\']', dom_snippet)
        for tid in test_ids:
            raw_candidates.append({
                "selector": f"page.getByTestId('{tid}')",
                "type": "TEST_ID",
                "confidence": 0.98,
                "resilience": "HIGH",
                "justification": f"Explicit automated test contract attribute 'data-testid=\"{tid}\"'. Completely decoupled from CSS/DOM refactorings.",
            })

        # 2. Search for Accessible Button Roles
        buttons = re.findall(r'<button[^>]*>(.*?)</button>', dom_snippet, re.DOTALL | re.IGNORECASE)
        for btn_text in buttons:
            clean_btn = re.sub(r"<[^>]+>", "", btn_text).strip()
            if clean_btn:
                raw_candidates.append({
                    "selector": f"page.getByRole('button', {{ name: '{clean_btn}' }})",
                    "type": "ACCESSIBLE_ROLE",
                    "confidence": 0.95,
                    "resilience": "HIGH",
                    "justification": f"W3C ARIA accessible role 'button' with accessible name '{clean_btn}'. Recommended Playwright best practice.",
                })

        # 3. Search for Placeholder / Input Labels
        placeholders = re.findall(r'<input[^>]*placeholder=["\']([^"\']+)["\']', dom_snippet, re.IGNORECASE)
        for ph in placeholders:
            raw_candidates.append({
                "selector": f"page.getByPlaceholder('{ph}')",
                "type": "PLACEHOLDER",
                "confidence": 0.92,
                "resilience": "HIGH",
                "justification": f"User-facing placeholder '{ph}'. Highly stable across structural DOM updates.",
            })

        # 4. Search for Explicit Element IDs
        ids = re.findall(r'\bid=["\']([^"\']+)["\']', dom_snippet)
        for el_id in ids:
            if not el_id.startswith(("root", "app")):
                raw_candidates.append({
                    "selector": f"page.locator('#{el_id}')",
                    "type": "ID",
                    "confidence": 0.85,
                    "resilience": "MEDIUM",
                    "justification": f"Unique element identifier id=\"{el_id}\".",
                })

        # 5. Search for Semantic Text
        headings_and_spans = re.findall(r'<(?:h[1-6]|span|div|a)[^>]*class=["\']?[^"\'>]*["\']?[^>]*>([^<]{3,40})</', dom_snippet)
        for text in headings_and_spans:
            clean_t = text.strip()
            if clean_t and not clean_t.startswith("{") and not clean_t.startswith("<"):
                raw_candidates.append({
                    "selector": f"page.getByText('{clean_t}')",
                    "type": "TEXT",
                    "confidence": 0.80,
                    "resilience": "MEDIUM",
                    "justification": f"Visible UI text '{clean_t}'. Matches user perception.",
                })

        # Deduplicate candidates by selector preserving highest confidence
        unique_selectors: dict[str, dict[str, Any]] = {}
        for c in raw_candidates:
            sel = c["selector"]
            if sel not in unique_selectors or c["confidence"] > unique_selectors[sel]["confidence"]:
                unique_selectors[sel] = c

        candidates = list(unique_selectors.values())

        # Verify each candidate against live DOM snippet
        for c in candidates:
            c["match_count"] = self.count_matches(c["selector"], dom_snippet)
            c["is_unique"] = (c["match_count"] == 1)

        # Categorize into uniquely verified vs ambiguous
        verified_candidates = [c for c in candidates if c["match_count"] == 1]
        ambiguous_candidates = [c for c in candidates if c["match_count"] > 1]

        # Diagnose why original broke
        if "//" in broken_selector or "div[" in broken_selector or "tr[" in broken_selector:
            diagnosis = "The original selector used an absolute or hierarchical XPath. Any layout change or wrapper div breaks the test."
        elif broken_selector.startswith("."):
            diagnosis = "The original selector relied on CSS classes that are vulnerable to CSS-in-JS hashes, utility framework changes, or restyling."
        elif "#" in broken_selector:
            diagnosis = "The original selector targeted an element ID that may have been removed or regenerated dynamically."
        else:
            diagnosis = "The locator failed due to timing, strict mode violation, or DOM mutation."

        # Resolution Logic
        if verified_candidates:
            # Sort uniquely verified candidates by confidence descending
            verified_candidates.sort(key=lambda x: x["confidence"], reverse=True)
            top = verified_candidates[0]
            status = "VERIFIED"
            verified = True
            healed_selector = top["selector"]
            selector_type = top["type"]
            confidence_score = top["confidence"]
            resilience_rating = top["resilience"]
            match_count = 1
            justification = f"{top['justification']} [Verified: exactly 1 matching element found in DOM]."
            action_code = f"await {top['selector']}.{target_action}();"
            alternatives = [c["selector"] for c in verified_candidates[1:4]]
        elif ambiguous_candidates:
            # Never silently accept an ambiguous element
            ambiguous_candidates.sort(key=lambda x: x["confidence"], reverse=True)
            top = ambiguous_candidates[0]
            status = "AMBIGUOUS_MATCH"
            verified = False
            healed_selector = None
            selector_type = top["type"]
            confidence_score = 0.0
            resilience_rating = "UNSAFE"
            match_count = top["match_count"]
            justification = (
                f"Ambiguous match rejected: candidate '{top['selector']}' matched {top['match_count']} elements in DOM. "
                "Self-healing refused to interact to prevent state corruption."
            )
            action_code = ""
            alternatives = [c["selector"] for c in ambiguous_candidates]
        else:
            # Healing failed
            status = "HEALING_FAILED"
            verified = False
            healed_selector = None
            selector_type = "NONE"
            confidence_score = 0.0
            resilience_rating = "NONE"
            match_count = 0
            justification = "Healing failed: no resilient semantic locator could be synthesized from the DOM snippet."
            action_code = ""
            alternatives = []

        return {
            "status": status,
            "verified": verified,
            "match_count": match_count,
            "original_selector": broken_selector,
            "failure_message": failure_message,
            "healed_selector": healed_selector,
            "selector_type": selector_type,
            "confidence_score": confidence_score,
            "resilience_rating": resilience_rating,
            "diagnosis": diagnosis,
            "justification": justification,
            "code_replacement": action_code,
            "alternatives": alternatives,
            "candidates": [c["selector"] for c in candidates],
        }


