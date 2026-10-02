import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Ensure ai-engine and qa-engine directories are resolvable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
for _d in ["ai-engine", "qa-engine"]:
    _p = str(_REPO_ROOT / _d)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import json
from app.core.ai_provider import get_ai_provider
from agents import DefectRCAAgent, SecurityTestingAgent
from domain_registry import domain_registry, UnsupportedDomainError
from evaluation import (
    answer_relevance,
    citation_accuracy,
    context_relevance,
    groundedness,
    truthful_refusal,
)
from rag import RAGPipeline

# Ensure domain packs are registered
import domains.airline.domain_pack  # noqa: F401
import domains.healthcare.domain_pack  # noqa: F401
import domains.fintech.domain_pack  # noqa: F401

router = APIRouter(prefix="/ai", tags=["ai-engine"])

# In-memory shared RAG pipeline bootstrapped dynamically from registered domain packs
_rag_pipeline = RAGPipeline()
_rag_pipeline.bootstrap_registered_domains(domain_registry)


class GroundednessRequest(BaseModel):
    answer: str = Field(min_length=1)
    context: str = Field(min_length=1)


class RAGQueryRequest(BaseModel):
    question: str | None = None
    query: str | None = None
    k: int = Field(default=3, ge=1, le=10)
    domain: Optional[str] = None
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)

    @property
    def effective_question(self) -> str:
        q = self.question or self.query
        if not q or len(q.strip()) < 3:
            raise HTTPException(
                status_code=422,
                detail="Either 'question' or 'query' must be provided with at least 3 characters",
            )
        return q.strip()


class IngestKnowledgeRequest(BaseModel):
    document_id: str = Field(min_length=2, description="Unique synthetic document ID")
    text: str = Field(min_length=5, description="Synthetic document knowledge body")
    domain: Optional[str] = Field(default=None, description="Target domain, defaults to active domain")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional document metadata")


class RCARequest(BaseModel):
    error_message: str | None = None
    logs: str | None = None
    component: str | None = None
    status_code: int | None = None
    endpoint: str | None = None
    failure_code: str | None = None

    @property
    def effective_message(self) -> str:
        msg = self.error_message or self.logs
        if not msg:
            return "Unknown error trace"
        return msg


@router.get("/providers")
async def list_providers():
    p = get_ai_provider()
    m_name = getattr(p, "model_name", "MockAIProvider")
    return {
        "provider": m_name,
        "default_model": m_name,
        "mock_active": getattr(p, "is_mock", True),
        "active_provider": m_name,
        "supported_providers": ["mock", "gemini", "claude", "openai"],
    }


@router.post("/evaluate/groundedness")
async def check_groundedness(payload: GroundednessRequest):
    result = groundedness(payload.answer, payload.context)
    return {
        "metric": result.metric,
        "score": result.score,
        "passed": result.passed,
        "reason": result.reason,
    }


@router.post("/rag/knowledge")
async def ingest_synthetic_knowledge(payload: IngestKnowledgeRequest):
    """
    Ingest synthetic QA knowledge dynamically into the RAG pipeline.
    Adheres to AGENTS.md Section 10: Ingestion Plane decoupled from Query Plane.
    """
    try:
        if payload.domain:
            effective_domain = domain_registry.validate_domain(payload.domain)
        else:
            effective_domain = domain_registry.get_active_domain_id()
    except UnsupportedDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    chunks = _rag_pipeline.ingest_document(
        document_id=payload.document_id,
        text=payload.text,
        metadata=payload.metadata,
        domain=effective_domain,
    )
    return {
        "status": "INGESTED",
        "document_id": payload.document_id,
        "domain": effective_domain,
        "chunks_count": len(chunks),
        "total_indexed_chunks": _rag_pipeline.index.count(),
    }


@router.get("/rag/knowledge")
async def list_rag_knowledge():
    """Returns metadata and statistics on indexed knowledge sources and registered domains."""
    return {
        "total_chunks": _rag_pipeline.index.count(),
        "active_domain": domain_registry.get_active_domain_id(),
        "registered_domains": domain_registry.list_domain_ids(),
    }


@router.post("/rag/query")
async def execute_rag_query(payload: RAGQueryRequest):
    try:
        q = payload.effective_question
        if payload.domain and payload.domain.lower() == "all":
            effective_domain = None
        elif payload.domain:
            effective_domain = domain_registry.validate_domain(payload.domain)
        else:
            effective_domain = domain_registry.get_active_domain_id()

        query_result = await _rag_pipeline.query(
            q, k=payload.k, domain=effective_domain, min_score=payload.min_score
        )
        ans_relevance = answer_relevance(q, query_result.answer)
        grounded = (
            groundedness(query_result.answer, query_result.context_text)
            if query_result.context_text
            else groundedness("refusal", "refusal")
        )
        ctx_relevance = (
            context_relevance(q, query_result.context_text)
            if query_result.context_text
            else context_relevance("refusal", "refusal")
        )

        structured_citations = [
            {
                "chunk_id": chunk.chunk_id,
                "source": chunk.metadata.get("source", chunk.document_id),
                "score": score,
                "document_id": chunk.document_id,
            }
            for chunk, score in zip(query_result.retrieved_chunks, query_result.similarity_scores)
        ]

        citation_eval = citation_accuracy(
            structured_citations, query_result.retrieved_chunks
        )
        refusal_eval = truthful_refusal(
            q, is_refusal=query_result.refusal, should_refuse=query_result.refusal
        )

        return {
            "question": query_result.question,
            "answer": query_result.answer,
            "domain": query_result.domain,
            "citations": structured_citations,
            "evidence": query_result.evidence,
            "context_text": query_result.context_text,
            "similarity_scores": query_result.similarity_scores,
            "groundedness_score": grounded.score if not query_result.refusal else 1.0,
            "context_relevance_score": ctx_relevance.score if not query_result.refusal else 1.0,
            "citation_accuracy_score": citation_eval.score,
            "truthful_refusal_score": refusal_eval.score,
            "confidence": query_result.confidence,
            "model": query_result.model,
            "provider": query_result.provider,
            "latency_ms": query_result.latency_ms,
            "refusal": query_result.refusal,
            "evaluation": {
                "answer_relevance": ans_relevance.score if not query_result.refusal else 1.0,
                "groundedness": grounded.score if not query_result.refusal else 1.0,
                "grounded": grounded.passed if not query_result.refusal else True,
                "context_relevance": ctx_relevance.score if not query_result.refusal else 1.0,
                "citation_accuracy": citation_eval.score,
                "truthful_refusal": refusal_eval.score,
            },
        }
    except UnsupportedDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rca")
async def diagnose_failure(payload: RCARequest):
    rca_agent = DefectRCAAgent()
    effective_component = payload.endpoint or payload.component or "payments"
    context = {
        "error_msg": payload.effective_message,
        "status_code": payload.status_code,
        "endpoint": effective_component,
        "failure_code": payload.failure_code,
    }
    run = await rca_agent.execute(
        task=f"Diagnose failure on {effective_component}",
        context=context,
    )

    last_event = next(
        (e for e in reversed(run.events) if e.event_type == "RCA_DIAGNOSED"),
        None,
    )
    meta = last_event.metadata if last_event and last_event.metadata else {}
    diagnosis = meta.get("diagnosis", "GATEWAY_TIMEOUT" if "timeout" in payload.effective_message.lower() else "SYSTEM_ANOMALY")
    severity = meta.get("severity", "HIGH" if "timeout" in payload.effective_message.lower() else "MEDIUM")

    return {
        "run_id": run.run_id,
        "agent_id": run.agent_id,
        "status": run.status,
        "summary": diagnosis,
        "root_cause": f"Detected {diagnosis} in execution flow for {effective_component}.",
        "severity": severity,
        "affected_component": effective_component,
        "recommended_fix": (
            "Verify upstream gateway connectivity, timeout thresholds, and idempotent retry policies."
            if "timeout" in diagnosis.lower() or "timeout" in payload.effective_message.lower()
            else "Inspect entity lock state, database constraints, and service payload."
        ),
        "output": run.output,
        "provider": "MockAIProvider",
        "events": [
            {"type": e.event_type, "description": e.description, "time": e.timestamp}
            for e in run.events
        ],
    }


class RemediateDefectRequest(BaseModel):
    defect_id: str = "DEF-001"
    run_regression: bool = True
    policy_name: str = "PRODUCTION_STRICT"
    context: Optional[Dict[str, Any]] = None


@router.post("/rca/remediate")
async def remediate_defect_endpoint(payload: RemediateDefectRequest):
    rca_agent = DefectRCAAgent()
    res = rca_agent.remediate(
        defect_id=payload.defect_id,
        context=payload.context,
        run_regression=payload.run_regression,
        policy_name=payload.policy_name,
    )
    return {
        "defect_id": res.defect_id,
        "defect_name": res.defect_name,
        "status": res.status,
        "diagnosis": res.diagnosis,
        "severity": res.severity,
        "defect_resolved": res.defect_resolved,
        "regression_passed": res.regression_passed,
        "quality_gate_passed": res.quality_gate_passed,
        "patch": {
            "target_file": res.patch.target_file,
            "description": res.patch.description,
            "original_snippet": res.patch.original_snippet,
            "patched_snippet": res.patch.patched_snippet,
            "explanation": res.patch.explanation,
            "diff": res.patch.diff,
            "affected_endpoints": res.patch.affected_endpoints,
        },
        "regression_plan": {
            "changed_files": res.regression_plan.changed_files,
            "selected_test_files": res.regression_plan.selected_test_files,
            "selected_tags": res.regression_plan.selected_tags,
            "pytest_command": res.regression_plan.pytest_command,
        },
        "tests_executed": res.tests_executed,
        "tests_passed": res.tests_passed,
        "tests_failed": res.tests_failed,
        "resolution_details": res.resolution_details,
        "execution_time_ms": res.execution_time_ms,
        "violations": res.violations,
    }


class SecurityAuditRequest(BaseModel):
    endpoint: str = "/api"
    method: str = "POST"
    payload: Any = None
    role: str = "passenger"
    user_email: str | None = None
    target_email: str | None = None


@router.post("/security/audit")
async def audit_endpoint_security(payload: SecurityAuditRequest):
    """
    Run automated DAST and payload security analysis using SecurityTestingAgent (AGENTS.md Section 6 & 21).
    """
    agent = SecurityTestingAgent()
    context = {
        "endpoint": payload.endpoint,
        "method": payload.method,
        "payload": payload.payload or {},
        "role": payload.role,
        "user_email": payload.user_email,
        "target_email": payload.target_email,
    }
    run = await agent.execute(f"Audit endpoint {payload.endpoint}", context)
    report = json.loads(run.output or "{}")
    return {
        "run_id": run.run_id,
        "agent_id": run.agent_id,
        "status": run.status,
        "report": report,
        "events": [
            {"type": e.event_type, "description": e.description, "time": e.timestamp}
            for e in run.events
        ],
    }


class SecurityScanSuiteRequest(BaseModel):
    mode: str = "gate"
    suite: Optional[List[Dict[str, Any]]] = None


@router.post("/security/scan-suite")
async def run_security_scan_suite(req: SecurityScanSuiteRequest):
    """
    Run automated DAST batch scan over a suite of attack or baseline cases using SecurityTestingAgent.
    Returns full DAST audit metrics, compliance rate, OWASP and PCI DSS violations.
    """
    agent = SecurityTestingAgent()
    if req.suite:
        report = await agent.scan_suite(req.suite)
    else:
        from security_scanner import ATTACK_VERIFICATION_SUITE, BASELINE_GATE_SUITE
        probes = ATTACK_VERIFICATION_SUITE if req.mode == "attack" else BASELINE_GATE_SUITE
        report = await agent.scan_suite(probes)

    report["scan_mode"] = req.mode
    return report
