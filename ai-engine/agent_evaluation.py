import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from agents import BaseAgent, DefectRCAAgent


@dataclass
class AgentBenchmarkCase:
    id: str
    task: str
    context: Dict[str, Any]
    expected_diagnosis: str
    expected_severity: str
    allowed_tools: List[str] = field(default_factory=list)


@dataclass
class AgentEvaluationReport:
    total_cases: int
    passed_cases: int
    completion_rate: float
    diagnostic_accuracy: float
    severity_accuracy: float
    mean_latency_ms: float
    details: List[Dict[str, Any]] = field(default_factory=list)


STANDARD_RCA_BENCHMARK: List[AgentBenchmarkCase] = [
    AgentBenchmarkCase(
        id="BENCH-RCA-01",
        task="Diagnose payment 3DS timeout",
        context={
            "error_msg": "ACS Bank Timeout: 3DS challenge exceeded 30s threshold on /payments",
            "status_code": 504,
            "failure_code": "3DS_TIMEOUT",
            "endpoint": "payments",
        },
        expected_diagnosis="GATEWAY_OR_3DS_TIMEOUT",
        expected_severity="HIGH",
    ),
    AgentBenchmarkCase(
        id="BENCH-RCA-02",
        task="Diagnose flight overbooking conflict",
        context={
            "error_msg": "Insufficient seat availability for flight ID 42",
            "status_code": 409,
            "endpoint": "bookings",
        },
        expected_diagnosis="INSUFFICIENT_INVENTORY_OR_DUPLICATE",
        expected_severity="HIGH",
    ),
    AgentBenchmarkCase(
        id="BENCH-RCA-03",
        task="Diagnose missing booking entity",
        context={
            "error_msg": "Booking with reference QAH-9999 not found",
            "status_code": 404,
            "endpoint": "bookings",
        },
        expected_diagnosis="ENTITY_NOT_FOUND",
        expected_severity="LOW",
    ),
    AgentBenchmarkCase(
        id="BENCH-RCA-04",
        task="Diagnose schema contract mismatch",
        context={
            "error_msg": "Field passenger_email required but missing",
            "status_code": 422,
            "endpoint": "bookings",
        },
        expected_diagnosis="CONTRACT_VALIDATION_ERROR",
        expected_severity="LOW",
    ),
]


async def evaluate_rca_agent(
    agent: Optional[DefectRCAAgent] = None,
    dataset: Optional[List[AgentBenchmarkCase]] = None,
) -> AgentEvaluationReport:
    """Evaluates DefectRCAAgent across reasoning, accuracy, and latency dimensions (AGENTS.md Section 20)."""
    target_agent = agent or DefectRCAAgent()
    cases = dataset or STANDARD_RCA_BENCHMARK

    total = len(cases)
    completed = 0
    correct_diag = 0
    correct_sev = 0
    latencies = []
    details = []

    for case in cases:
        start = time.perf_counter()
        run = await target_agent.execute(case.task, case.context)
        latency = (time.perf_counter() - start) * 1000.0
        latencies.append(latency)

        is_completed = run.status == "COMPLETED"
        if is_completed:
            completed += 1

        # Extract diagnosis from events or output
        diag_event = next(
            (e for e in reversed(run.events) if e.event_type == "RCA_DIAGNOSED"),
            None,
        )
        meta = diag_event.metadata if diag_event else {}
        diag = meta.get("diagnosis", "")
        sev = meta.get("severity", "")

        diag_match = diag == case.expected_diagnosis
        sev_match = sev == case.expected_severity

        if diag_match:
            correct_diag += 1
        if sev_match:
            correct_sev += 1

        passed = is_completed and diag_match and sev_match

        details.append(
            {
                "case_id": case.id,
                "passed": passed,
                "diagnosis": diag,
                "expected_diagnosis": case.expected_diagnosis,
                "severity": sev,
                "expected_severity": case.expected_severity,
                "latency_ms": round(latency, 2),
            }
        )

    mean_latency = sum(latencies) / len(latencies) if latencies else 0.0

    return AgentEvaluationReport(
        total_cases=total,
        passed_cases=sum(1 for d in details if d["passed"]),
        completion_rate=completed / total if total else 0.0,
        diagnostic_accuracy=correct_diag / total if total else 0.0,
        severity_accuracy=correct_sev / total if total else 0.0,
        mean_latency_ms=round(mean_latency, 2),
        details=details,
    )
