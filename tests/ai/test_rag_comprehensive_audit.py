"""Automated Audit Suite for 10-Dimensional RAG Evaluation Dataset.

Adheres strictly to MASTER PROMPT Section 10, AGENTS.md Sections 10, 18, 19:
- Validates RAG across all 10 critical dimensions:
    1. Standard questions
    2. Domain-specific questions across all 5 domains
    3. Paraphrased questions
    4. Multi-step reasoning
    5. Ambiguous questions
    6. Unsupported questions
    7. Adversarial injection attacks
    8. Hallucination probes
    9. Citation tests
    10. Truthful refusal tests
- Enforces quantitative groundedness, citation correctness, and zero fabrication.
"""

import asyncio
import pytest
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
for _d in ["", "backend", "ai-engine", "qa-engine"]:
    _p = str(_REPO_ROOT / _d) if _d else str(_REPO_ROOT)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.core.ai_provider import MockAIProvider, MockEmbeddingProvider
from domain_registry import domain_registry
from evaluation import groundedness
from rag import RAGPipeline, VectorIndex
from rag_dataset import RAGBenchmarkCase, get_evaluation_dataset


@pytest.fixture(scope="module")
def multi_domain_rag_pipeline():
    """Initializes a hermetic RAG pipeline loaded with knowledge across all 5 domains."""
    pipeline = RAGPipeline(
        ai_provider=MockAIProvider(),
        embedding_provider=MockEmbeddingProvider(),
        index=VectorIndex()
    )
    pipeline.bootstrap_registered_domains(domain_registry)
    return pipeline


@pytest.mark.parametrize("case", get_evaluation_dataset(), ids=lambda c: f"{c.id}-{c.dimension}")
def test_rag_evaluation_case(multi_domain_rag_pipeline, case: RAGBenchmarkCase):
    """Evaluates an individual benchmark case from the 10-dimensional dataset."""
    domain = case.domain if case.domain not in ["cross_domain", "unsupported"] else None
    result = asyncio.run(
        multi_domain_rag_pipeline.query(
            question=case.query,
            k=3,
            min_score=0.25,
            domain=domain
        )
    )

    # 1. Verification of Refusal Expectations
    if case.expected_refusal:
        refusal_phrases = ["cannot", "not found", "unable", "unsupported", "refuse", "do not have", "no relevant"]
        is_refusal = (
            result.refusal
            or len(result.retrieved_chunks) == 0
            or any(p in result.answer.lower() for p in refusal_phrases)
        )
        assert is_refusal, (
            f"Case {case.id} ({case.dimension}) expected refusal, but received answer: {result.answer}"
        )

        for forbidden in case.forbidden_keywords:
            assert forbidden.lower() not in result.answer.lower(), (
                f"Case {case.id} leaked forbidden keyword '{forbidden}': {result.answer}"
            )
    else:
        # 2. Verification of Supported Queries
        assert not result.refusal, (
            f"Case {case.id} unexpectedly refused query: {case.query}"
        )
        assert len(result.retrieved_chunks) > 0, (
            f"Case {case.id} retrieved 0 chunks for valid query: {case.query}"
        )

        if case.expected_doc_citation:
            assert any(case.expected_doc_citation in c for c in result.citations), (
                f"Case {case.id} missing expected citation '{case.expected_doc_citation}' in {result.citations}"
            )

        eval_res = groundedness(result.answer, result.context_text)
        assert eval_res.score >= case.min_groundedness, (
            f"Case {case.id} groundedness {eval_res.score:.2f} fell below required {case.min_groundedness}"
        )


def test_rag_audit_summary_metrics(multi_domain_rag_pipeline):
    """Aggregates multi-dimensional evaluation metrics across the entire dataset."""
    dataset = get_evaluation_dataset()
    refusal_cases = [c for c in dataset if c.expected_refusal]
    supported_cases = [c for c in dataset if not c.expected_refusal]

    refusal_success = 0
    groundedness_scores = []
    citation_correct = 0

    for c in dataset:
        domain = c.domain if c.domain not in ["cross_domain", "unsupported"] else None
        res = asyncio.run(
            multi_domain_rag_pipeline.query(
                c.query, k=3, min_score=0.25, domain=domain
            )
        )
        if c.expected_refusal:
            refusal_phrases = ["cannot", "not found", "unable", "unsupported", "refuse", "do not have", "no relevant"]
            if res.refusal or len(res.retrieved_chunks) == 0 or any(p in res.answer.lower() for p in refusal_phrases):
                refusal_success += 1
        else:
            eval_res = groundedness(res.answer, res.context_text)
            groundedness_scores.append(eval_res.score)
            if c.expected_doc_citation and any(c.expected_doc_citation in cit for cit in res.citations):
                citation_correct += 1

    truthful_refusal_rate = refusal_success / len(refusal_cases) if refusal_cases else 1.0
    avg_groundedness = sum(groundedness_scores) / len(groundedness_scores) if groundedness_scores else 1.0
    citation_accuracy = citation_correct / len(supported_cases) if supported_cases else 1.0

    assert truthful_refusal_rate >= 0.85, f"Truthful refusal rate {truthful_refusal_rate:.2f} < 0.85"
    assert avg_groundedness >= 0.70, f"Average groundedness {avg_groundedness:.2f} < 0.70"
    assert citation_accuracy >= 0.85, f"Citation accuracy {citation_accuracy:.2f} < 0.85"
