from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class Evaluation:
    metric: str
    score: float
    passed: bool
    reason: str


def exact_match(expected: str, actual: str) -> Evaluation:
    """Deterministic exact string comparison."""
    passed = expected.strip() == actual.strip()
    return Evaluation(
        metric="exact_match",
        score=1.0 if passed else 0.0,
        passed=passed,
        reason="Exact string match" if passed else "Strings differ",
    )


def groundedness(answer: str, context: str, threshold: float = 0.75) -> Evaluation:
    """
    Evaluates whether claims and informative keywords in the answer are supported
    by the retrieved context (detects hallucinations / unsupported claims).
    """
    if not answer.strip():
        return Evaluation("groundedness", 0.0, False, "Answer is empty")
    if not context.strip():
        return Evaluation("groundedness", 0.0, False, "Context is empty")

    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "and", "or", "in", "on", "at",
        "to", "for", "with", "by", "from", "of", "about", "it", "this", "that", "be",
    }

    answer_words = [
        w.lower()
        for w in re.findall(r"\b[A-Za-z0-9_-]+\b", answer)
        if len(w) > 2 and w.lower() not in stop_words
    ]
    if not answer_words:
        return Evaluation("groundedness", 1.0, True, "No claim keywords to evaluate")

    context_lower = context.lower()
    supported_count = sum(1 for w in answer_words if w in context_lower)
    score = round(supported_count / len(answer_words), 4)
    passed = score >= threshold

    reason = (
        f"Grounded: {supported_count}/{len(answer_words)} claim terms verified in context"
        if passed
        else f"Hallucination warning: only {supported_count}/{len(answer_words)} terms found in context"
    )
    return Evaluation("groundedness", score, passed, reason)


def answer_relevance(question: str, answer: str, threshold: float = 0.5) -> Evaluation:
    """Evaluates whether the generated answer directly addresses terms in the question."""
    q_words = [
        w.lower()
        for w in re.findall(r"\b[A-Za-z0-9_-]+\b", question)
        if len(w) > 2
    ]
    if not q_words:
        return Evaluation("answer_relevance", 1.0, True, "Query contains no key terms")

    answer_lower = answer.lower()
    matched = sum(1 for w in q_words if w in answer_lower)
    score = round(matched / len(q_words), 4)
    passed = score >= threshold

    return Evaluation(
        "answer_relevance",
        score,
        passed,
        f"Matched {matched}/{len(q_words)} question keywords in answer",
    )


def retrieval_metrics(
    expected_chunk_ids: set[str], retrieved_chunk_ids: list[str]
) -> dict[str, float]:
    """
    Computes standard IR retrieval evaluation metrics:
    - Recall: proportion of relevant chunks retrieved
    - Precision: proportion of retrieved chunks that are relevant
    - Hit Rate: 1.0 if at least one relevant chunk is retrieved, else 0.0
    - F1 Score: Harmonic mean of precision and recall
    """
    if not expected_chunk_ids:
        return {"recall": 1.0, "precision": 1.0, "hit_rate": 1.0, "f1": 1.0}
    if not retrieved_chunk_ids:
        return {"recall": 0.0, "precision": 0.0, "hit_rate": 0.0, "f1": 0.0}

    retrieved_set = set(retrieved_chunk_ids)
    intersection = expected_chunk_ids.intersection(retrieved_set)

    recall = len(intersection) / len(expected_chunk_ids)
    precision = len(intersection) / len(retrieved_set)
    hit_rate = 1.0 if len(intersection) > 0 else 0.0
    f1 = (
        (2 * precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return {
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "hit_rate": hit_rate,
        "f1": round(f1, 4),
    }


def context_relevance(
    query: str,
    context: str,
    threshold: float = 0.5,
) -> Evaluation:
    """
    Evaluates whether the retrieved context contains relevant information and keywords
    directly pertaining to the user's question, penalizing noisy or irrelevant retrieval.
    """
    if not query.strip():
        return Evaluation("context_relevance", 1.0, True, "Empty query")
    if not context.strip():
        return Evaluation("context_relevance", 0.0, False, "Context is empty")

    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "and", "or", "in", "on", "at",
        "to", "for", "with", "by", "from", "of", "about", "it", "this", "that", "be",
        "what", "where", "when", "how", "who", "which", "can", "do", "does", "did",
    }
    q_words = [
        w.lower()
        for w in re.findall(r"\b[A-Za-z0-9]+\b", query)
        if len(w) > 2 and w.lower() not in stop_words
    ]
    if not q_words:
        return Evaluation("context_relevance", 1.0, True, "No salient query terms")

    context_lower = context.lower()
    matched = sum(1 for w in q_words if w in context_lower)
    score = round(matched / len(q_words), 4)
    passed = score >= threshold

    reason = (
        f"Relevant: {matched}/{len(q_words)} question terms matched in retrieved context"
        if passed
        else f"Low relevance: only {matched}/{len(q_words)} question terms found in context"
    )
    return Evaluation("context_relevance", score, passed, reason)


def citation_accuracy(
    citations: list[Any],
    retrieved_chunks: list[Any] | None = None,
    expected_document_ids: set[str] | None = None,
    threshold: float = 0.8,
) -> Evaluation:
    """
    Evaluates citation accuracy: verifies that citations correspond to actual retrieved
    document chunks and not hallucinated/fabricated references.
    """
    chunks = retrieved_chunks or []
    if not citations and not chunks:
        return Evaluation(
            "citation_accuracy",
            1.0,
            True,
            "Clean non-citation: zero citations expected for empty context/refusal",
        )

    if not citations and chunks:
        return Evaluation(
            "citation_accuracy",
            0.0,
            False,
            "Missing citations: context was retrieved but zero citations provided",
        )

    # Build lookup sets for valid chunk IDs and document IDs
    valid_chunk_ids: set[str] = set()
    valid_doc_ids: set[str] = set()

    for c in chunks:
        cid = getattr(c, "chunk_id", None) or (c.get("chunk_id") if isinstance(c, dict) else None)
        did = getattr(c, "document_id", None) or (c.get("document_id") if isinstance(c, dict) else None)
        if cid:
            valid_chunk_ids.add(str(cid))
        if did:
            valid_doc_ids.add(str(did))

    valid_count = 0
    for cit in citations:
        if isinstance(cit, dict):
            c_chunk = str(cit.get("chunk_id", ""))
            c_doc = str(cit.get("document_id", ""))
            is_valid = (c_chunk in valid_chunk_ids) or (c_doc in valid_doc_ids)
            if expected_document_ids and c_doc:
                is_valid = is_valid and (c_doc in expected_document_ids)
            if is_valid:
                valid_count += 1
        else:
            cit_str = str(cit)
            is_valid = False
            # Check direct match with chunk_id or document_id
            if cit_str in valid_chunk_ids or cit_str in valid_doc_ids:
                is_valid = True
            else:
                # Check formatted reference like 'AIRLINE-POLICY-01#chunk_0'
                for v_cid in valid_chunk_ids:
                    if v_cid in cit_str:
                        is_valid = True
                        break
                if not is_valid:
                    for v_did in valid_doc_ids:
                        if v_did in cit_str:
                            is_valid = True
                            break

            if expected_document_ids:
                matches_expected = any(ed in cit_str for ed in expected_document_ids)
                is_valid = is_valid and matches_expected

            if is_valid:
                valid_count += 1

    score = round(valid_count / len(citations), 4) if citations else 1.0
    passed = score >= threshold

    reason = (
        f"Accurate: {valid_count}/{len(citations)} citations verified against retrieved evidence"
        if passed
        else f"Citation mismatch: only {valid_count}/{len(citations)} citations verified (threshold: {threshold})"
    )
    return Evaluation("citation_accuracy", score, passed, reason)


def truthful_refusal(
    query: str,
    is_refusal: bool,
    should_refuse: bool,
    reason_text: str = "",
) -> Evaluation:
    """
    Evaluates whether the RAG pipeline truthfully refuses to answer when evidence is absent
    (preventing confabulation/hallucination) and answers when valid evidence is present.
    """
    if is_refusal == should_refuse:
        score = 1.0
        passed = True
        reason = (
            "Truthful refusal verified: unindexed/out-of-domain query safely rejected"
            if should_refuse
            else "Truthful generation verified: in-domain query answered with evidence"
        )
    else:
        score = 0.0
        passed = False
        reason = (
            "Hallucination / Safety failure: pipeline failed to refuse out-of-domain query without evidence"
            if should_refuse
            else "False refusal failure: pipeline incorrectly refused query with valid indexed evidence"
        )

    if reason_text:
        reason += f" ({reason_text})"

    return Evaluation("truthful_refusal", score, passed, reason)


def evaluate_rag_result(
    question: str,
    answer: str,
    context_text: str,
    retrieved_chunks: list[Any],
    citations: list[Any],
    is_refusal: bool,
    should_refuse: bool = False,
    expected_document_ids: set[str] | None = None,
) -> dict[str, Evaluation]:
    """Evaluates all 4 RAG signals on a single RAG query result."""
    if is_refusal and should_refuse:
        # Refusal is truthful and expected
        g_eval = Evaluation(
            "groundedness", 1.0, True, "Truthful refusal contains no unsupported claims"
        )
        c_eval = Evaluation(
            "context_relevance", 1.0, True, "Refusal correctly identified absence of context"
        )
        cit_eval = Evaluation(
            "citation_accuracy", 1.0, True, "Refusal correctly emitted zero spurious citations"
        )
        ref_eval = truthful_refusal(question, is_refusal=True, should_refuse=True)
    else:
        g_eval = groundedness(answer, context_text)
        c_eval = context_relevance(question, context_text)
        cit_eval = citation_accuracy(citations, retrieved_chunks, expected_document_ids)
        ref_eval = truthful_refusal(question, is_refusal=is_refusal, should_refuse=should_refuse)

    return {
        "groundedness": g_eval,
        "context_relevance": c_eval,
        "citation_accuracy": cit_eval,
        "truthful_refusal": ref_eval,
    }


def aggregate_rag_benchmark(eval_results: list[dict[str, Evaluation]]) -> dict[str, float]:
    """Aggregates a batch of RAG evaluation results into mean scores for the Quality Gate."""
    if not eval_results:
        return {
            "groundedness": 1.0,
            "context_relevance": 1.0,
            "citation_accuracy": 1.0,
            "truthful_refusal": 1.0,
        }

    keys = ["groundedness", "context_relevance", "citation_accuracy", "truthful_refusal"]
    aggregated = {}
    for k in keys:
        scores = [res[k].score for res in eval_results if k in res]
        aggregated[k] = round(sum(scores) / len(scores), 4) if scores else 1.0

    return aggregated
