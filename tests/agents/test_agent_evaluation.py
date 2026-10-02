import pytest
from agent_evaluation import (
    STANDARD_RCA_BENCHMARK,
    AgentBenchmarkCase,
    evaluate_rca_agent,
)
from agents import DefectRCAAgent


@pytest.mark.anyio
async def test_defect_rca_agent_benchmark_accuracy():
    """
    Evaluate DefectRCAAgent across accuracy, task completion, and latency benchmarks.
    Enforces minimum 100% completion rate and > 90% diagnostic accuracy.
    """
    report = await evaluate_rca_agent()

    assert report.total_cases == len(STANDARD_RCA_BENCHMARK)
    assert report.completion_rate == 1.0, "All benchmark tasks must complete successfully"
    assert report.diagnostic_accuracy == 1.0, "RCA diagnosis must match ground truth"
    assert report.severity_accuracy == 1.0, "Severity classification must be accurate"
    assert report.mean_latency_ms < 100.0, f"Mean latency exceeded: {report.mean_latency_ms}ms"


@pytest.mark.anyio
async def test_defect_rca_agent_custom_benchmark_case():
    """
    Verify agent evaluation with a novel custom test case.
    """
    custom_case = AgentBenchmarkCase(
        id="CUSTOM-01",
        task="Diagnose payment timeout",
        context={
            "error_msg": "Timeout while waiting for 3DS challenge authentication",
            "status_code": 504,
            "endpoint": "payments",
        },
        expected_diagnosis="GATEWAY_OR_3DS_TIMEOUT",
        expected_severity="HIGH",
    )
    report = await evaluate_rca_agent(dataset=[custom_case])
    assert report.total_cases == 1
    assert report.passed_cases == 1
    assert report.details[0]["diagnosis"] == "GATEWAY_OR_3DS_TIMEOUT"
