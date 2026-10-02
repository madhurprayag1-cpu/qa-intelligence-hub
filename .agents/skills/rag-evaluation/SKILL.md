---
name: rag-evaluation
description: Evaluating retrieval augmented generation quality, groundedness, hallucination rates, and citation accuracy.
---

# Skill: RAG Evaluation

## Purpose
Enforces quantitative evaluation standards for AI knowledge retrieval and generation pipelines. A successful HTTP response is not a successful RAG response (AGENTS.md Section 19).

## Metrics
1. **Context Relevance**: Measures whether retrieved chunks match semantic intent of query vector.
2. **Groundedness**: Verifies that 100% of claims in generated answers are backed by retrieved passages.
3. **Hallucination Detection**: Penalizes fabricated flight numbers, unverified pricing tiers, or unauthorized policies.
4. **Citation Correctness**: Ensures document ID, chunk offsets, and timestamps are accurately linked.
