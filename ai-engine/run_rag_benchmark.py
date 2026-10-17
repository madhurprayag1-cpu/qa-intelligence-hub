"""Run the deterministic multi-domain RAG benchmark and emit release-gate evidence.

This uses the same hermetic mock providers and registered domain knowledge as the
RAG integration tests. It never calls a live external model or production service.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for entry in (ROOT, ROOT / "backend", ROOT / "ai-engine", ROOT / "qa-engine"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from app.core.ai_provider import MockAIProvider, MockEmbeddingProvider
from domain_registry import domain_registry
from evaluation import aggregate_rag_benchmark, context_relevance, evaluate_rag_result
from rag import RAGPipeline, VectorIndex
from rag_dataset import get_evaluation_dataset

STRICT_THRESHOLDS = {
    "groundedness": 0.85,
    "context_relevance": 0.80,
    "citation_accuracy": 0.85,
    "truthful_refusal": 0.90,
}
REFUSAL_PHRASES = (
    "cannot", "not found", "unable", "unsupported", "refuse",
    "do not have", "no relevant",
)


async def run_benchmark() -> dict:
    pipeline = RAGPipeline(
        ai_provider=MockAIProvider(),
        embedding_provider=MockEmbeddingProvider(),
        index=VectorIndex(),
    )
    pipeline.bootstrap_registered_domains(domain_registry)

    dataset = get_evaluation_dataset()
    results = []
    case_reports = []

    for case in dataset:
        domain = case.domain if case.domain not in ("cross_domain", "unsupported") else None
        result = await pipeline.query(
            question=case.query,
            k=3,
            min_score=0.25,
            domain=domain,
        )
        answer_lower = result.answer.lower()
        is_refusal = bool(
            result.refusal
            or not result.retrieved_chunks
            or any(phrase in answer_lower for phrase in REFUSAL_PHRASES)
        )

        checks = []
        if case.expected_refusal:
            checks.append(is_refusal)
            checks.extend(word.lower() not in answer_lower for word in case.forbidden_keywords)
        else:
            checks.append(not is_refusal)
            checks.append(bool(result.retrieved_chunks))
            if case.expected_doc_citation:
                checks.append(
                    any(case.expected_doc_citation in citation for citation in result.citations)
                )

        expected_documents = {case.expected_doc_citation} if case.expected_doc_citation else None
        evaluations = evaluate_rag_result(
            question=case.query,
            answer=result.answer,
            context_text=result.context_text,
            retrieved_chunks=result.retrieved_chunks,
            citations=result.citations,
            is_refusal=is_refusal,
            should_refuse=case.expected_refusal,
            expected_document_ids=expected_documents,
        )
        # Use the dataset's explicit gold relevance keywords for supported queries.
        # Raw-query lexical overlap penalizes valid paraphrases and is not a semantic
        # relevance metric. Refusal cases retain the evaluator's truthful-refusal path.
        if not case.expected_refusal:
            relevance_query = " ".join(case.required_keywords) or case.query
            evaluations["context_relevance"] = context_relevance(
                relevance_query, result.context_text
            )
        scores = {name: evaluation.score for name, evaluation in evaluations.items()}

        # Keep per-case behavior aligned with the existing RAG audit tests.
        # The strict policy thresholds apply to the aggregate benchmark scores below.
        if not case.expected_refusal:
            checks.append(scores["groundedness"] >= case.min_groundedness)
        passed = all(checks)
        results.append(evaluations)
        case_reports.append({
            "id": case.id,
            "dimension": case.dimension,
            "domain": case.domain,
            "passed": passed,
            "scores": scores,
            "checks_passed": sum(checks),
            "checks_total": len(checks),
        })

    metrics = aggregate_rag_benchmark(results)
    failed = sum(1 for case in case_reports if not case["passed"])
    total = len(case_reports)
    passed = total - failed
    aggregate_pass = all(
        metrics[name] >= threshold for name, threshold in STRICT_THRESHOLDS.items()
    )
    return {
        "total_queries": total,
        "passed_queries": passed,
        "failed_queries": failed,
        "skipped_queries": 0,
        "metrics": metrics,
        "thresholds": STRICT_THRESHOLDS,
        "aggregate_gate_passed": aggregate_pass,
        "metadata": {
            "mode": "HERMETIC_OFFLINE_MOCK",
            "dataset": "RAG_EVALUATION_DATASET",
            "revision": os.environ.get("GITHUB_SHA", "local-unresolved"),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "external_provider_calls": False,
            "context_relevance_method": "annotated_required_keywords_overlap_for_supported_queries",
        },
        "cases": case_reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-json",
        default="test-results/rag-eval-report.json",
        help="Path for the machine-readable RAG benchmark report",
    )
    args = parser.parse_args()

    report = asyncio.run(run_benchmark())
    output = Path(args.output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"RAG benchmark report written to: {output}")
    print(json.dumps({
        "revision": report["metadata"]["revision"],
        "total_queries": report["total_queries"],
        "passed_queries": report["passed_queries"],
        "failed_queries": report["failed_queries"],
        "metrics": report["metrics"],
        "thresholds": report["thresholds"],
        "aggregate_gate_passed": report["aggregate_gate_passed"],
        "cases": report["cases"],
    }, indent=2))

    return 0 if (
        report["failed_queries"] == 0
        and report["aggregate_gate_passed"]
        and all(
            report["metrics"][name] >= threshold
            for name, threshold in STRICT_THRESHOLDS.items()
        )
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
