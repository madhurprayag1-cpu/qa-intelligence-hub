"""Deterministic Automated Test Suite for Phase 6 Task 6.2:
Automated RAG Evaluation Quality Gate Integration.

Adheres strictly to AGENTS.md Sections 18, 19, 20, 24 and docs/ROADMAP.md:
- Deterministic verification of 4 core RAG evaluation signals:
  1. Groundedness
  2. Context Relevance
  3. Citation Accuracy
  4. Truthful Refusal
- Multi-signal release quality gate policy enforcement (PRODUCTION_STRICT, STAGING_STANDARD, DEV_PR_FAST)
- Backward compatibility invariant: Non-RAG test runs (where RAG scores are None) continue passing
- JSON report parsing (parse_rag_eval_json)
- CLI execution and Markdown PR report formatting
- REST API /quality-gate/evaluate and /ai/rag/query evaluation contracts
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from evaluation import (
    aggregate_rag_benchmark,
    citation_accuracy,
    context_relevance,
    evaluate_rag_result,
    groundedness,
    truthful_refusal,
)
from quality_gate import (
    PRESET_POLICIES,
    QualityGateInput,
    QualityGatePolicy,
    evaluate_policy_gate,
    parse_rag_eval_json,
)
from cli_gate import generate_pr_markdown_report, run_cli


client = TestClient(app)


# --- 1. RAG Evaluation Metrics Unit Tests ---
def test_groundedness_evaluation():
    """Verify groundedness detects supported claims vs unsupported hallucinations."""
    context = (
        "Economy class passengers are allowed 1 carry-on bag up to 8kg free of charge. "
        "Checked baggage requires a fee unless flying Business Class."
    )
    supported_answer = "Economy class passengers can bring 1 carry-on bag up to 8kg."
    eval_supported = groundedness(supported_answer, context, threshold=0.75)
    assert eval_supported.passed is True
    assert eval_supported.score >= 0.75
    assert "Grounded" in eval_supported.reason

    hallucinated_answer = (
        "Passengers receive unlimited free champagne, caviar room service, "
        "and complimentary helicopter shuttle transfers."
    )
    eval_hallucinated = groundedness(hallucinated_answer, context, threshold=0.75)
    assert eval_hallucinated.passed is False
    assert eval_hallucinated.score < 0.30
    assert "Hallucination" in eval_hallucinated.reason


def test_context_relevance_evaluation():
    """Verify context relevance checks question term representation in retrieved text."""
    query = "What is the refund policy for cancelled flights?"
    relevant_context = (
        "Under Airline Regulation AIR-REF-01, refunds for cancelled flights are processed "
        "to the original payment method within 7 to 10 business days."
    )
    eval_rel = context_relevance(query, relevant_context, threshold=0.50)
    assert eval_rel.passed is True
    assert eval_rel.score >= 0.50
    assert "Relevant" in eval_rel.reason

    noisy_irrelevant_context = (
        "The airline operates Boeing 787 and Airbus A350 aircraft with Rolls-Royce Trent engines."
    )
    eval_irrel = context_relevance(query, noisy_irrelevant_context, threshold=0.50)
    assert eval_irrel.passed is False
    assert eval_irrel.score < 0.50
    assert "Low relevance" in eval_irrel.reason


def test_citation_accuracy_evaluation():
    """Verify citation accuracy verifies references against retrieved evidence."""
    mock_chunks = [
        {"document_id": "AIRLINE-BAGGAGE-01", "chunk_id": "AIRLINE-BAGGAGE-01#chunk_0"},
        {"document_id": "AIRLINE-POLICY-01", "chunk_id": "AIRLINE-POLICY-01#chunk_1"},
    ]

    # Valid citations matching retrieved evidence
    valid_citations = [
        "AIRLINE-BAGGAGE-01#chunk_0",
        "AIRLINE-POLICY-01#chunk_1",
    ]
    eval_valid = citation_accuracy(valid_citations, mock_chunks, threshold=0.85)
    assert eval_valid.passed is True
    assert eval_valid.score == 1.0

    # Fabricated citations not in retrieved evidence
    hallucinated_citations = [
        "UNKNOWN-DOC-99#chunk_99",
        "FABRICATED-CITATION-404#chunk_0",
    ]
    eval_bad = citation_accuracy(hallucinated_citations, mock_chunks, threshold=0.85)
    assert eval_bad.passed is False
    assert eval_bad.score == 0.0

    # Clean non-citation when both citations and retrieved chunks are empty
    eval_clean_empty = citation_accuracy([], [], threshold=0.85)
    assert eval_clean_empty.passed is True
    assert eval_clean_empty.score == 1.0

    # Missing citations when context is retrieved
    eval_missing = citation_accuracy([], mock_chunks, threshold=0.85)
    assert eval_missing.passed is False
    assert eval_missing.score == 0.0


def test_truthful_refusal_evaluation():
    """Verify truthful refusal enforces rejection of unindexed queries and accepts in-domain answers."""
    # 1. Truthful refusal when evidence is absent (expected rejection)
    eval_good_refusal = truthful_refusal(
        query="warp speed quantum graviton flux",
        is_refusal=True,
        should_refuse=True,
    )
    assert eval_good_refusal.passed is True
    assert eval_good_refusal.score == 1.0
    assert "safely rejected" in eval_good_refusal.reason

    # 2. Confabulation failure when pipeline answers without evidence
    eval_confabulation = truthful_refusal(
        query="warp speed quantum graviton flux",
        is_refusal=False,
        should_refuse=True,
    )
    assert eval_confabulation.passed is False
    assert eval_confabulation.score == 0.0
    assert "Safety failure" in eval_confabulation.reason

    # 3. Truthful generation when evidence is present
    eval_good_answer = truthful_refusal(
        query="flight baggage allowance",
        is_refusal=False,
        should_refuse=False,
    )
    assert eval_good_answer.passed is True
    assert eval_good_answer.score == 1.0

    # 4. False refusal failure when pipeline rejects valid indexed question
    eval_false_refusal = truthful_refusal(
        query="flight baggage allowance",
        is_refusal=True,
        should_refuse=False,
    )
    assert eval_false_refusal.passed is False
    assert eval_false_refusal.score == 0.0


def test_evaluate_rag_result_and_benchmark_aggregation():
    """Verify composite RAG result evaluation and batch benchmark score aggregation."""
    res1 = evaluate_rag_result(
        question="What is the baggage limit?",
        answer="The carry-on limit is 8kg.",
        context_text="Carry-on baggage limit is 8kg per passenger.",
        retrieved_chunks=[{"chunk_id": "BAGGAGE-01#chunk_0", "document_id": "BAGGAGE-01"}],
        citations=["BAGGAGE-01#chunk_0"],
        is_refusal=False,
        should_refuse=False,
    )
    assert res1["groundedness"].passed is True
    assert res1["context_relevance"].passed is True
    assert res1["citation_accuracy"].passed is True
    assert res1["truthful_refusal"].passed is True

    res2_refusal = evaluate_rag_result(
        question="How do I travel through time?",
        answer="No relevant domain knowledge was found in indexed sources.",
        context_text="",
        retrieved_chunks=[],
        citations=[],
        is_refusal=True,
        should_refuse=True,
    )
    assert res2_refusal["truthful_refusal"].passed is True
    assert res2_refusal["citation_accuracy"].score == 1.0

    aggregated = aggregate_rag_benchmark([res1, res2_refusal])
    assert aggregated["groundedness"] >= 0.85
    assert aggregated["context_relevance"] >= 0.80
    assert aggregated["citation_accuracy"] == 1.0
    assert aggregated["truthful_refusal"] == 1.0


# --- 2. Quality Gate Policy & Multi-Signal Rules Tests ---
def test_quality_gate_passes_when_all_rag_signals_exceed_thresholds():
    """Verify Quality Gate passes with all 4 RAG signals meeting PRODUCTION_STRICT."""
    inp = QualityGateInput(
        total_tests=60,
        passed_tests=60,
        failed_tests=0,
        critical_defects=0,
        contract_failures=0,
        security_vulnerabilities=0,
        rag_groundedness_score=0.92,
        rag_context_relevance_score=0.88,
        rag_citation_accuracy_score=0.95,
        rag_truthful_refusal_score=1.00,
    )
    res = evaluate_policy_gate(inp, PRESET_POLICIES["PRODUCTION_STRICT"])
    assert res.passed is True
    assert res.status == "PASSED"
    assert len(res.violations) == 0
    assert res.signals["rag_groundedness_score"] == 0.92
    assert res.signals["rag_context_relevance_score"] == 0.88
    assert res.signals["rag_citation_accuracy_score"] == 0.95
    assert res.signals["rag_truthful_refusal_score"] == 1.00


def test_quality_gate_blocks_on_each_rag_signal_violation():
    """Verify each RAG signal independently fails the quality gate when below threshold."""
    policy = PRESET_POLICIES["PRODUCTION_STRICT"]

    # 1. Groundedness violation
    inp_grounded = QualityGateInput(
        total_tests=50,
        passed_tests=50,
        rag_groundedness_score=0.72,  # < 0.85
    )
    res_g = evaluate_policy_gate(inp_grounded, policy)
    assert res_g.passed is False
    assert any("groundedness" in v.lower() for v in res_g.violations)

    # 2. Context relevance violation
    inp_relevance = QualityGateInput(
        total_tests=50,
        passed_tests=50,
        rag_context_relevance_score=0.65,  # < 0.80
    )
    res_r = evaluate_policy_gate(inp_relevance, policy)
    assert res_r.passed is False
    assert any("context relevance" in v.lower() for v in res_r.violations)

    # 3. Citation accuracy violation
    inp_citation = QualityGateInput(
        total_tests=50,
        passed_tests=50,
        rag_citation_accuracy_score=0.70,  # < 0.85
    )
    res_c = evaluate_policy_gate(inp_citation, policy)
    assert res_c.passed is False
    assert any("citation accuracy" in v.lower() for v in res_c.violations)

    # 4. Truthful refusal violation
    inp_refusal = QualityGateInput(
        total_tests=50,
        passed_tests=50,
        rag_truthful_refusal_score=0.80,  # < 0.90
    )
    res_ref = evaluate_policy_gate(inp_refusal, policy)
    assert res_ref.passed is False
    assert any("truthful refusal" in v.lower() for v in res_ref.violations)


def test_quality_gate_policy_tiers_differentiation():
    """Verify policy tiers (PRODUCTION_STRICT vs STAGING_STANDARD vs DEV_PR_FAST) apply tiered thresholds."""
    # A score of 0.78 fails PRODUCTION_STRICT (0.80/0.85) but passes STAGING_STANDARD (0.70/0.75)
    borderline_input = QualityGateInput(
        total_tests=50,
        passed_tests=49,
        failed_tests=1,
        rag_groundedness_score=0.78,
        rag_context_relevance_score=0.75,
        rag_citation_accuracy_score=0.78,
        rag_truthful_refusal_score=0.85,
    )

    strict_res = evaluate_policy_gate(borderline_input, PRESET_POLICIES["PRODUCTION_STRICT"])
    assert strict_res.passed is False

    staging_res = evaluate_policy_gate(borderline_input, PRESET_POLICIES["STAGING_STANDARD"])
    assert staging_res.passed is True

    fast_res = evaluate_policy_gate(borderline_input, PRESET_POLICIES["DEV_PR_FAST"])
    assert fast_res.passed is True


def test_non_rag_test_run_backward_compatibility():
    """Verify non-RAG test suites (where RAG scores are None) pass without false violations."""
    inp = QualityGateInput(
        total_tests=188,
        passed_tests=188,
        failed_tests=0,
        rag_groundedness_score=None,
        rag_context_relevance_score=None,
        rag_citation_accuracy_score=None,
        rag_truthful_refusal_score=None,
    )
    res = evaluate_policy_gate(inp, PRESET_POLICIES["PRODUCTION_STRICT"])
    assert res.passed is True
    assert len(res.violations) == 0


# --- 3. JSON Parsing & CLI Tests ---
def test_parse_rag_eval_json_flat():
    """Verify parse_rag_eval_json parses standard flat benchmark report."""
    report_json = json.dumps({
        "total_queries": 15,
        "passed_queries": 15,
        "groundedness": 0.94,
        "context_relevance": 0.89,
        "citation_accuracy": 0.96,
        "truthful_refusal": 1.0,
        "metadata": {"domain": "airline", "provider": "mock"},
    })
    parsed = parse_rag_eval_json(report_json)
    assert parsed.total_tests == 15
    assert parsed.passed_tests == 15
    assert parsed.rag_groundedness_score == 0.94
    assert parsed.rag_context_relevance_score == 0.89
    assert parsed.rag_citation_accuracy_score == 0.96
    assert parsed.rag_truthful_refusal_score == 1.0
    assert parsed.metadata.get("domain") == "airline"


def test_parse_rag_eval_json_nested():
    """Verify parse_rag_eval_json parses nested metrics benchmark report."""
    report_json = json.dumps({
        "summary": {"total_tests": 8, "passed_tests": 8},
        "metrics": {
            "rag_groundedness_score": 0.87,
            "rag_context_relevance_score": 0.82,
            "rag_citation_accuracy_score": 0.90,
            "rag_truthful_refusal_score": 0.95,
        },
    })
    parsed = parse_rag_eval_json(report_json)
    assert parsed.rag_groundedness_score == 0.87
    assert parsed.rag_context_relevance_score == 0.82
    assert parsed.rag_citation_accuracy_score == 0.90
    assert parsed.rag_truthful_refusal_score == 0.95


def test_cli_gate_markdown_report_formatting():
    """Verify Markdown report formats all 4 RAG signals and status badges."""
    inp = QualityGateInput(
        total_tests=50,
        passed_tests=50,
        failed_tests=0,
        rag_groundedness_score=0.91,
        rag_context_relevance_score=0.86,
        rag_citation_accuracy_score=0.94,
        rag_truthful_refusal_score=1.00,
    )
    res = evaluate_policy_gate(inp, PRESET_POLICIES["PRODUCTION_STRICT"])
    report = generate_pr_markdown_report(res)

    assert "APPROVED" in report
    assert "RAG Groundedness" in report
    assert "Context Relevance" in report
    assert "Citation Accuracy" in report
    assert "Truthful Refusal" in report
    assert "0.91" in report
    assert "0.86" in report
    assert "0.94" in report
    assert "1.00" in report


def test_cli_gate_with_rag_flags(tmp_path):
    """Verify CLI gate runs with explicit RAG flags and outputs markdown."""
    report_file = tmp_path / "rag_cli_report.md"
    args = [
        "--policy", "PRODUCTION_STRICT",
        "--total", "20",
        "--passed", "20",
        "--failed", "0",
        "--rag-groundedness", "0.93",
        "--rag-context-relevance", "0.87",
        "--rag-citation-accuracy", "0.92",
        "--rag-truthful-refusal", "1.00",
        "--output-markdown", str(report_file),
    ]
    exit_code = run_cli(args)
    assert exit_code == 0
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "APPROVED" in content
    assert "0.93" in content


def test_cli_gate_with_rag_json_file(tmp_path):
    """Verify CLI gate ingests RAG report JSON file and blocks on violation."""
    bad_rag_file = tmp_path / "rag_bad.json"
    bad_rag_file.write_text(
        json.dumps({
            "total_queries": 10,
            "passed_queries": 10,
            "groundedness": 0.50,  # Below 0.85
            "context_relevance": 0.85,
            "citation_accuracy": 0.90,
            "truthful_refusal": 1.0,
        }),
        encoding="utf-8",
    )

    report_file = tmp_path / "rag_fail_report.md"
    args = [
        "--policy", "PRODUCTION_STRICT",
        "--rag-json", str(bad_rag_file),
        "--output-markdown", str(report_file),
    ]
    exit_code = run_cli(args)
    assert exit_code == 1
    content = report_file.read_text(encoding="utf-8")
    assert "BLOCKED" in content
    assert "groundedness" in content.lower()


# --- 4. API Endpoints Integration Tests ---
def test_quality_gate_api_evaluate_with_rag_signals():
    """Verify POST /quality-gate/evaluate receives and evaluates all 4 RAG signals."""
    payload = {
        "policy_name": "PRODUCTION_STRICT",
        "total_tests": 40,
        "passed_tests": 40,
        "failed_tests": 0,
        "rag_groundedness_score": 0.95,
        "rag_context_relevance_score": 0.88,
        "rag_citation_accuracy_score": 0.92,
        "rag_truthful_refusal_score": 1.0,
    }
    resp = client.post("/quality-gate/evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is True
    assert data["status"] == "PASSED"
    assert data["signals"]["rag_groundedness_score"] == 0.95
    assert data["signals"]["rag_context_relevance_score"] == 0.88
    assert data["signals"]["rag_citation_accuracy_score"] == 0.92
    assert data["signals"]["rag_truthful_refusal_score"] == 1.0


def test_api_rag_query_includes_all_four_evaluation_signals():
    """Verify POST /ai/rag/query returns all 4 RAG signals in evaluation payload."""
    resp = client.post(
        "/ai/rag/query",
        json={"question": "What are the cabin baggage regulations and fees?", "domain": "airline"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["refusal"] is False
    assert "evaluation" in data
    eval_data = data["evaluation"]
    assert "groundedness" in eval_data
    assert "context_relevance" in eval_data
    assert "citation_accuracy" in eval_data
    assert "truthful_refusal" in eval_data
    assert eval_data["groundedness"] >= 0.70
    assert eval_data["context_relevance"] >= 0.50
    assert eval_data["citation_accuracy"] >= 0.80
    assert eval_data["truthful_refusal"] == 1.0
