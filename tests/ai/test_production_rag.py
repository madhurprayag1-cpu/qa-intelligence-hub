"""Production-grade AI/RAG Architecture Tests.

Adheres strictly to AGENTS.md Sections 3, 4, 10, 18, 19:
- Provider-independent AI/RAG abstraction (Mock, Gemini, Claude, OpenAI).
- Decoupled Ingestion Plane vs Query Plane.
- Domain-scoped knowledge partitioning (airline knowledge in domain pack, extensible to any industry).
- Dynamic knowledge ingestion and source/chunk attribution.
- Clear separation between retrieved evidence and synthesized response.
- Truthful refusal when evidence is unavailable (no silent fabrication).
- Deterministic, hermetic automated tests.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.ai_provider import (
    ClaudeProvider,
    GeminiProvider,
    MockAIProvider,
    MockEmbeddingProvider,
    OpenAIProvider,
)
from app.main import app
from domain_registry import DomainCapability, DomainPack, DomainRegistry
from domains.airline.domain_pack import airline_domain_pack
from domains.airline.knowledge import AIRLINE_KNOWLEDGE_DOCS, get_airline_knowledge_docs
from rag import DocumentChunk, RAGPipeline, VectorIndex


client = TestClient(app)


# --- 1. Domain Pack Knowledge Provider Tests ---
def test_airline_knowledge_docs_provider():
    """Verify synthetic airline knowledge provider adheres to clean contract."""
    docs = get_airline_knowledge_docs()
    assert len(docs) >= 5

    doc_ids = [d["document_id"] for d in docs]
    assert "AIRLINE-POLICY-01" in doc_ids
    assert "AIRLINE-BAGGAGE-01" in doc_ids
    assert "AIRLINE-REFUND-01" in doc_ids
    assert "AIRLINE-NDC-01" in doc_ids
    assert "AIRLINE-ANCILLARIES-01" in doc_ids

    for doc in docs:
        assert len(doc["document_id"]) > 3
        assert len(doc["text"]) > 20
        assert "metadata" in doc
        meta = doc["metadata"]
        assert meta["domain"] == "airline"
        assert "category" in meta
        assert "title" in meta
        # Verify only public-safe synthetic terms are present
        assert "password" not in doc["text"].lower()
        assert "secret" not in doc["text"].lower()


def test_airline_domain_pack_rag_attachment():
    """Verify airline domain pack registers its knowledge provider."""
    assert airline_domain_pack.rag_docs_provider is not None
    assert callable(airline_domain_pack.rag_docs_provider)
    assert len(airline_domain_pack.rag_sources) >= 5
    assert airline_domain_pack.has_capability(DomainCapability.RAG_AI)


# --- 2. Dynamic Domain Loading & Cross-Domain Partitioning ---
def test_rag_pipeline_load_domain_knowledge():
    """Verify RAG pipeline loads knowledge dynamically from a DomainPack."""
    embedder = MockEmbeddingProvider()
    pipeline = RAGPipeline(embedding_provider=embedder)

    loaded_count = pipeline.load_domain_knowledge(airline_domain_pack)
    assert loaded_count == len(AIRLINE_KNOWLEDGE_DOCS)
    assert pipeline.index.count() >= loaded_count


@pytest.mark.anyio
async def test_cross_domain_rag_isolation():
    """
    Verify multi-domain isolation:
    Airline knowledge is NEVER retrieved when querying a Healthcare or FinTech domain,
    preventing cross-tenant/cross-domain knowledge leakage.
    """
    embedder = MockEmbeddingProvider()
    pipeline = RAGPipeline(
        ai_provider=MockAIProvider(),
        embedding_provider=embedder,
    )

    # Ingest Airline knowledge
    pipeline.load_domain_knowledge(airline_domain_pack)

    # Create & Ingest a hypothetical Healthcare domain pack
    healthcare_docs = [
        {
            "document_id": "HLTH-HIPAA-01",
            "text": "Protected Health Information (PHI) must be encrypted in transit and at rest under HIPAA Security Rule.",
            "metadata": {"title": "HIPAA Compliance", "domain": "healthcare", "source": "HLTH-HIPAA-01"},
        },
        {
            "document_id": "HLTH-FHIR-01",
            "text": "HL7 FHIR R4 standardizes patient observation, condition, and medication resource serialization in JSON.",
            "metadata": {"title": "FHIR Standards", "domain": "healthcare", "source": "HLTH-FHIR-01"},
        },
    ]
    healthcare_pack = DomainPack(
        domain_id="healthcare",
        name="Healthcare EHR",
        capabilities=[DomainCapability.RAG_AI],
        rag_docs_provider=lambda: healthcare_docs,
    )
    pipeline.load_domain_knowledge(healthcare_pack)

    # 1. Scoped query to airline domain
    airline_res = await pipeline.query("baggage allowance rules", domain="airline")
    assert airline_res.refusal is False
    assert len(airline_res.retrieved_chunks) > 0
    for chunk in airline_res.retrieved_chunks:
        assert chunk.metadata.get("domain") == "airline"

    # 2. Querying airline concept within healthcare domain returns truthful refusal
    hlth_refusal = await pipeline.query("baggage allowance rules", domain="healthcare")
    assert hlth_refusal.refusal is True
    assert hlth_refusal.confidence == "NO_EVIDENCE"
    assert len(hlth_refusal.retrieved_chunks) == 0
    assert "No relevant domain knowledge was found" in hlth_refusal.answer

    # 3. Scoped query to healthcare domain
    hlth_res = await pipeline.query("HIPAA patient PHI encryption", domain="healthcare")
    assert hlth_res.refusal is False
    assert len(hlth_res.retrieved_chunks) > 0
    for chunk in hlth_res.retrieved_chunks:
        assert chunk.metadata.get("domain") == "healthcare"


# --- 3. Non-Fabrication & Evidence Separation Tests ---
@pytest.mark.anyio
async def test_rag_refusal_on_unavailable_knowledge():
    """Verify the pipeline refuses to hallucinate when knowledge is absent."""
    embedder = MockEmbeddingProvider()
    pipeline = RAGPipeline(
        ai_provider=MockAIProvider(),
        embedding_provider=embedder,
    )
    pipeline.load_domain_knowledge(airline_domain_pack)

    # Query concept entirely outside the knowledge base
    unrelated_query = "quantum superconductor topological qubit coherence time"
    res = await pipeline.query(unrelated_query, domain="airline")

    assert res.refusal is True
    assert res.confidence == "NO_EVIDENCE"
    assert len(res.retrieved_chunks) == 0
    assert len(res.citations) == 0
    assert len(res.evidence) == 0
    assert "No relevant domain knowledge was found" in res.answer


@pytest.mark.anyio
async def test_rag_evidence_and_citation_separation():
    """Verify retrieved evidence is cleanly separated from synthesized answer."""
    embedder = MockEmbeddingProvider()
    pipeline = RAGPipeline(
        ai_provider=MockAIProvider(),
        embedding_provider=embedder,
    )
    pipeline.load_domain_knowledge(airline_domain_pack)

    res = await pipeline.query("What are the cancellation refund rules?", domain="airline", k=2)

    assert res.refusal is False
    assert len(res.answer) > 10
    # Evidence must be a structured list with full chunk provenance
    assert len(res.evidence) > 0
    for ev in res.evidence:
        assert "document_id" in ev
        assert "chunk_id" in ev
        assert "source" in ev
        assert "text" in ev
        assert "score" in ev
        assert ev["domain"] == "airline"

    # Citations must provide clean references
    assert len(res.citations) > 0
    assert "AIRLINE-REFUND-01" in res.citations[0]


# --- 4. Provider Independence Tests ---
@pytest.mark.anyio
async def test_rag_provider_independence():
    """Verify RAG query pipeline operates with all standard providers."""
    embedder = MockEmbeddingProvider()

    providers = [
        MockAIProvider(),
        GeminiProvider(api_key=""),
        ClaudeProvider(api_key=""),
        OpenAIProvider(api_key=""),
    ]

    for prov in providers:
        pipeline = RAGPipeline(ai_provider=prov, embedding_provider=embedder)
        pipeline.ingest_document(
            document_id="DOC-PROV-TEST",
            text="Payment authorizations require multi-factor 3DS verification.",
            domain="airline",
        )
        res = await pipeline.query("3DS verification", domain="airline")
        assert res.refusal is False
        assert len(res.retrieved_chunks) > 0
        assert len(res.citations) > 0
        assert res.provider in ["mock", "gemini", "claude", "openai"]


# --- 5. FastAPI Endpoints Integration Tests ---
def test_api_rag_knowledge_list():
    """Verify GET /ai/rag/knowledge returns registry and index status."""
    resp = client.get("/ai/rag/knowledge")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_chunks"] >= 5
    assert data["active_domain"] == "airline"
    assert "airline" in data["registered_domains"]


def test_api_rag_knowledge_ingest_and_query():
    """Verify POST /ai/rag/knowledge accepts dynamic synthetic knowledge and queries it."""
    payload = {
        "document_id": "AIRLINE-VIP-LOUNGE-01",
        "text": "First class passengers have complimentary access to the Aegean Star Lounge in Athens.",
        "domain": "airline",
        "metadata": {"title": "Lounge Access Rules", "category": "ancillaries"},
    }

    # 1. Ingest new synthetic QA document
    ingest_resp = client.post("/ai/rag/knowledge", json=payload)
    assert ingest_resp.status_code == 200
    ingest_data = ingest_resp.json()
    assert ingest_data["status"] == "INGESTED"
    assert ingest_data["document_id"] == "AIRLINE-VIP-LOUNGE-01"
    assert ingest_data["domain"] == "airline"
    assert ingest_data["chunks_count"] >= 1

    # 2. Query newly ingested knowledge
    query_resp = client.post(
        "/ai/rag/query",
        json={"question": "Where is the Aegean Star Lounge in Athens?", "domain": "airline"},
    )
    assert query_resp.status_code == 200
    query_data = query_resp.json()

    assert query_data["refusal"] is False
    assert len(query_data["citations"]) > 0
    assert query_data["citations"][0]["document_id"] == "AIRLINE-VIP-LOUNGE-01"
    assert len(query_data["evidence"]) > 0
    assert "Aegean Star Lounge" in query_data["evidence"][0]["text"]
    assert query_data["evaluation"]["grounded"] is True


def test_api_rag_query_refusal_on_nonexistent_knowledge():
    """Verify POST /ai/rag/query refuses gracefully when no evidence exists."""
    query_resp = client.post(
        "/ai/rag/query",
        json={
            "question": "suborbital hypersonic hyperdrive warp coils",
            "domain": "airline",
        },
    )
    assert query_resp.status_code == 200
    query_data = query_resp.json()

    assert query_data["refusal"] is True
    assert query_data["confidence"] == "NO_EVIDENCE"
    assert len(query_data["citations"]) == 0
    assert len(query_data["evidence"]) == 0
    assert "No relevant domain knowledge was found" in query_data["answer"]
