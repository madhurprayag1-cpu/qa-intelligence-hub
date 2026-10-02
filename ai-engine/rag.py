import math
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.ai_provider import (
    AIProvider,
    EmbeddingProvider,
    MockAIProvider,
    MockEmbeddingProvider,
    get_ai_provider,
)


@dataclass
class DocumentChunk:
    document_id: str
    chunk_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None


@dataclass
class RAGQueryResult:
    question: str
    answer: str
    context_text: str
    retrieved_chunks: list[DocumentChunk]
    citations: list[str]
    similarity_scores: list[float]
    model: str
    provider: str
    latency_ms: int
    evidence: list[dict[str, Any]] = field(default_factory=list)
    confidence: str = "HIGH"
    domain: str | None = None
    refusal: bool = False


class Chunker:
    """Configurable text chunker supporting sliding windows and overlap."""

    def __init__(self, chunk_size: int = 300, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(
        self,
        document_id: str,
        text: str,
        base_metadata: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        base_metadata = base_metadata or {}
        words = text.split()
        if not words:
            return []

        chunks: list[DocumentChunk] = []
        start = 0
        chunk_idx = 0
        step = max(1, self.chunk_size - self.overlap)

        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)

            chunk_meta = {
                **base_metadata,
                "document_id": document_id,
                "chunk_index": chunk_idx,
                "word_count": len(chunk_words),
                "created_at": datetime.utcnow().isoformat(),
            }

            chunks.append(
                DocumentChunk(
                    document_id=document_id,
                    chunk_id=f"{document_id}#chunk_{chunk_idx}",
                    text=chunk_text,
                    metadata=chunk_meta,
                )
            )

            start += step
            chunk_idx += 1

        for c in chunks:
            c.metadata["total_chunks"] = len(chunks)

        return chunks


class VectorIndex:
    """In-memory vector store supporting cosine similarity ranking."""

    def __init__(self):
        self._chunks: dict[str, DocumentChunk] = {}

    def add(self, chunks: list[DocumentChunk]):
        for c in chunks:
            if c.embedding is None:
                raise ValueError(f"Chunk {c.chunk_id} missing embedding vector")
            self._chunks[c.chunk_id] = c

    def count(self) -> int:
        return len(self._chunks)

    def search(
        self,
        query_vector: list[float],
        k: int = 5,
        min_score: float = 0.0,
        domain: str | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        scores: list[tuple[DocumentChunk, float]] = []

        for chunk in self._chunks.values():
            if not chunk.embedding:
                continue
            if domain is not None:
                chunk_domain = chunk.metadata.get("domain")
                if chunk_domain and chunk_domain.lower() != domain.lower():
                    continue
            sim = self._cosine_similarity(query_vector, chunk.embedding)
            if sim >= min_score:
                scores.append((chunk, round(sim, 4)))

        # Sort descending by similarity score
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]

    @staticmethod
    def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
        if len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)


class PersistentVectorIndex(VectorIndex):
    """
    PostgreSQL-backed persistent vector index for enterprise RAG scale (AGENTS.md Section 10).
    Persists embeddings and metadata into database while maintaining high-speed in-memory indexing.
    """

    def __init__(self, db_session=None):
        super().__init__()
        self.db = db_session

    def add(self, chunks: list[DocumentChunk]):
        super().add(chunks)
        if self.db is not None:
            from app.models.rag_chunk import RAGChunkModel

            for c in chunks:
                existing = self.db.query(RAGChunkModel).filter_by(chunk_id=c.chunk_id).first()
                if existing:
                    existing.text = c.text
                    existing.metadata_json = c.metadata
                    existing.embedding = c.embedding
                else:
                    item = RAGChunkModel(
                        document_id=c.document_id,
                        chunk_id=c.chunk_id,
                        text=c.text,
                        metadata_json=c.metadata,
                        embedding=c.embedding,
                    )
                    self.db.add(item)
            self.db.commit()

    def sync_from_db(self) -> int:
        """Hydrates vector index with all chunks persisted in PostgreSQL."""
        if self.db is None:
            return 0
        from app.models.rag_chunk import RAGChunkModel

        records = self.db.query(RAGChunkModel).all()
        chunks = [
            DocumentChunk(
                document_id=r.document_id,
                chunk_id=r.chunk_id,
                text=r.text,
                metadata=r.metadata_json or {},
                embedding=r.embedding,
            )
            for r in records
        ]
        if chunks:
            super().add(chunks)
        return len(chunks)


class RAGPipeline:
    """
    Production-grade RAG pipeline adhering to AGENTS.md Section 10:
    - Decoupled Ingestion Plane (chunking, metadata, embeddings, indexing)
    - Decoupled Query Plane (vector retrieval, context construction, answer generation)
    """

    def __init__(
        self,
        ai_provider: AIProvider | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        chunker: Chunker | None = None,
        index: VectorIndex | None = None,
    ):
        self.ai = ai_provider or get_ai_provider()
        self.embedder = embedding_provider or MockEmbeddingProvider()
        self.chunker = chunker or Chunker(chunk_size=150, overlap=30)
        self.index = index or VectorIndex()

    # --- Ingestion Plane ---
    def ingest_document(
        self,
        document_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        domain: str | None = None,
    ) -> list[DocumentChunk]:
        meta = metadata or {}
        if domain is not None:
            meta["domain"] = domain.lower()
        meta["ingested_at"] = datetime.utcnow().isoformat()
        chunks = self.chunker.chunk(document_id, text, meta)

        texts = [c.text for c in chunks]
        vectors = self.embedder.embed(texts)

        for chunk, vec in zip(chunks, vectors):
            chunk.embedding = vec

        self.index.add(chunks)
        return chunks

    def ingest_chunks(self, chunks: list[DocumentChunk]) -> int:
        missing_vecs = [c.text for c in chunks if c.embedding is None]
        if missing_vecs:
            vectors = self.embedder.embed(missing_vecs)
            vec_idx = 0
            for c in chunks:
                if c.embedding is None:
                    c.embedding = vectors[vec_idx]
                    vec_idx += 1

        self.index.add(chunks)
        return len(chunks)

    def ingest(self, chunks: list[DocumentChunk]) -> int:
        return self.ingest_chunks(chunks)

    def load_domain_knowledge(self, pack: Any) -> int:
        """
        Dynamically loads synthetic QA knowledge from a DomainPack.
        Enables domain-scoped partitioning without hardcoding domain business rules in core AI logic.
        """
        provider_fn = getattr(pack, "rag_docs_provider", None)
        if not provider_fn or not callable(provider_fn):
            return 0
        docs = provider_fn()
        count = 0
        for doc in docs:
            doc_id = doc.get("document_id")
            text = doc.get("text")
            if doc_id and text:
                meta = doc.get("metadata", {})
                self.ingest_document(
                    document_id=doc_id,
                    text=text,
                    metadata=meta,
                    domain=getattr(pack, "domain_id", None),
                )
                count += 1
        return count

    def bootstrap_registered_domains(self, registry: Any = None) -> int:
        """
        Discovers and ingests knowledge from all registered domain packs in the domain registry.
        """
        if registry is None:
            try:
                from domain_registry import domain_registry as default_registry
                registry = default_registry
            except ImportError:
                return 0
        total = 0
        list_fn = getattr(registry, "list_domains", None)
        if callable(list_fn):
            for pack in list_fn():
                total += self.load_domain_knowledge(pack)
        return total

    # --- Query Plane ---
    def retrieve(
        self,
        query: str,
        k: int = 5,
        min_score: float = 0.0,
        domain: str | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        query_vec = self.embedder.embed([query])[0]
        return self.index.search(query_vec, k=k, min_score=min_score, domain=domain)

    DEFAULT_MIN_SCORE: float = 0.15

    async def query(
        self,
        question: str,
        k: int = 3,
        system_prompt: str | None = None,
        domain: str | None = None,
        min_score: float = 0.0,
    ) -> RAGQueryResult:
        start_time = time.perf_counter()

        threshold = min_score if min_score > 0.0 else self.DEFAULT_MIN_SCORE
        scored_chunks = self.retrieve(question, k=k, min_score=threshold, domain=domain)
        # Filter for positive similarity relevance meeting threshold
        relevant_scored_chunks = [sc for sc in scored_chunks if sc[1] >= threshold]

        # Non-fabrication check: if no evidence found, refuse gracefully without hallucinating
        if not relevant_scored_chunks:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            model_name = getattr(self.ai, "model_name", "mock-qa-model")
            provider_name = (
                "mock"
                if getattr(self.ai, "is_mock", True)
                else getattr(self.ai, "provider", "mock")
            )
            refusal_msg = (
                f"No relevant domain knowledge was found in the indexed sources to answer this question"
                + (f" for domain '{domain}'." if domain else ".")
            )
            return RAGQueryResult(
                question=question,
                answer=refusal_msg,
                context_text="",
                retrieved_chunks=[],
                citations=[],
                similarity_scores=[],
                model=model_name,
                provider=provider_name,
                latency_ms=latency_ms,
                evidence=[],
                confidence="NO_EVIDENCE",
                domain=domain,
                refusal=True,
            )

        retrieved_chunks = [sc[0] for sc in relevant_scored_chunks]
        similarity_scores = [sc[1] for sc in relevant_scored_chunks]

        # Context construction with citations and separated evidence
        context_parts = []
        citations = []
        evidence = []
        for chunk, score in zip(retrieved_chunks, similarity_scores):
            source = chunk.metadata.get("source", chunk.document_id)
            context_parts.append(f"[{source} / {chunk.chunk_id}]: {chunk.text}")
            citations.append(f"{source}#{chunk.chunk_id}")
            evidence.append(
                {
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.chunk_id,
                    "source": source,
                    "text": chunk.text,
                    "score": score,
                    "domain": chunk.metadata.get("domain"),
                    "metadata": chunk.metadata,
                }
            )

        context_text = "\n\n".join(context_parts)

        # Confidence rating based on retrieval strength
        max_score = max(similarity_scores) if similarity_scores else 0.0
        if max_score >= 0.7:
            confidence = "HIGH"
        elif max_score >= 0.4:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        prompt = (
            f"Context Information:\n{context_text}\n\n"
            f"Question: {question}\n\n"
            f"Answer the question using the context above:"
        )

        response = await self.ai.generate(prompt=prompt, system=system_prompt)
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        return RAGQueryResult(
            question=question,
            answer=response.text,
            context_text=context_text,
            retrieved_chunks=retrieved_chunks,
            citations=citations,
            similarity_scores=similarity_scores,
            model=response.model,
            provider=response.provider,
            latency_ms=latency_ms,
            evidence=evidence,
            confidence=confidence,
            domain=domain,
            refusal=False,
        )
