from quality_gate import evaluate_gate
from test_registry import TestCase, TestRegistry


def test_quality_gate_passes_with_zero_failures():
    result = evaluate_gate(total=29, passed=29, failed=0, max_failure_rate=0.0)
    assert result.passed is True
    assert result.failure_rate == 0.0
    assert result.total == 29
    assert result.passed_tests == 29
    assert result.failed_tests == 0


def test_quality_gate_fails_when_threshold_exceeded():
    result = evaluate_gate(total=10, passed=8, failed=2, max_failure_rate=0.1)
    assert result.passed is False
    assert result.failure_rate == 0.2


def test_quality_gate_handles_empty_suite():
    result = evaluate_gate(total=0, passed=0, failed=0)
    assert result.passed is False
    assert result.failure_rate == 1.0


def test_test_registry_registration_and_filtering():
    registry = TestRegistry()
    case1 = TestCase(id="TC-01", name="3DS Success", layer="api", tags=("payment", "regression"))
    case2 = TestCase(id="TC-02", name="Search Routes", layer="ui", tags=("flight", "smoke"))

    registry.register(case1)
    registry.register(case2)

    assert len(registry.list()) == 2
    payment_tests = registry.by_tag("payment")
    assert len(payment_tests) == 1
    assert payment_tests[0].id == "TC-01"

    smoke_tests = registry.by_tag("smoke")
    assert len(smoke_tests) == 1
    assert smoke_tests[0].id == "TC-02"


def test_multi_signal_quality_gate_policy_evaluation():
    from quality_gate import PRESET_POLICIES, QualityGateInput, evaluate_policy_gate

    policy = PRESET_POLICIES["PRODUCTION_STRICT"]

    # Valid pristine input passes
    valid_input = QualityGateInput(
        total_tests=50,
        passed_tests=50,
        failed_tests=0,
        critical_defects=0,
        contract_failures=0,
        rag_groundedness_score=0.92,
    )
    result = evaluate_policy_gate(valid_input, policy)
    assert result.passed is True
    assert result.status == "PASSED"
    assert len(result.violations) == 0

    # RAG groundedness failure blocks production release
    low_rag_input = QualityGateInput(
        total_tests=50,
        passed_tests=50,
        failed_tests=0,
        rag_groundedness_score=0.68,  # Below 0.85
    )
    rag_result = evaluate_policy_gate(low_rag_input, policy)
    assert rag_result.passed is False
    assert any("groundedness" in v.lower() for v in rag_result.violations)

    # Critical defect blocks release
    defect_input = QualityGateInput(
        total_tests=50,
        passed_tests=50,
        failed_tests=0,
        critical_defects=1,
    )
    defect_result = evaluate_policy_gate(defect_input, policy)
    assert defect_result.passed is False
    assert any("critical defect" in v.lower() for v in defect_result.violations)


def test_junit_xml_parser():
    from quality_gate import parse_junit_xml

    sample_xml = """<?xml version="1.0" encoding="utf-8"?>
    <testsuites>
        <testsuite name="pytest" tests="20" errors="0" failures="1" skipped="2">
        </testsuite>
    </testsuites>
    """
    parsed = parse_junit_xml(sample_xml)
    assert parsed.total_tests == 20
    assert parsed.failed_tests == 1
    assert parsed.skipped_tests == 2
    assert parsed.passed_tests == 17


def test_playwright_json_parser():
    from quality_gate import parse_playwright_json

    sample_json = """{
        "stats": {
            "startTime": "2026-09-27T10:00:00Z",
            "duration": 12500,
            "expected": 8,
            "unexpected": 0,
            "flaky": 1,
            "skipped": 0
        }
    }"""
    parsed = parse_playwright_json(sample_json)
    assert parsed.total_tests == 9
    assert parsed.passed_tests == 8
    assert parsed.failed_tests == 0
    assert parsed.flaky_tests == 1

