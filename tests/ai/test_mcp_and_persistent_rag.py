import json
import pytest
from app.models.rag_chunk import RAGChunkModel
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT / "ai-engine") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "ai-engine"))

from mcp_server import call_tool, handle_jsonrpc, list_tools
from rag import DocumentChunk, PersistentVectorIndex, RAGPipeline


def test_mcp_list_tools():
    tools = list_tools()
    tool_names = [t["name"] for t in tools]
    assert "diagnose_defect_rca" in tool_names
    assert "generate_qa_test_cases" in tool_names
    assert "evaluate_quality_gate" in tool_names
    assert "query_rag_knowledge" in tool_names
    assert "audit_security_vulnerabilities" in tool_names


def test_mcp_jsonrpc_tools_list_dispatch():
    req = {"jsonrpc": "2.0", "method": "tools/list", "id": 100}
    res = handle_jsonrpc(req)
    assert res["jsonrpc"] == "2.0"
    assert res["id"] == 100
    assert "tools" in res["result"]
    assert len(res["result"]["tools"]) >= 5



def test_mcp_call_diagnose_defect():
    args = {
        "log_text": "Transaction failed: 3DS_AUTH_FAILED for booking QAH-9912. Bank ACS rejected challenge.",
        "component": "payments",
    }
    res = call_tool("diagnose_defect_rca", args)
    assert res["status"] == "success"
    assert res["result"]["category"] == "GATEWAY_OR_3DS_TIMEOUT"
    assert "recommended_fix" in res["result"]
    assert res["latency_ms"] >= 0


def test_mcp_call_generate_test_cases():
    args = {
        "requirement_text": "System must release reserved flight seats and process full refund when a confirmed booking is cancelled.",
        "focus_area": "API",
    }
    res = call_tool("generate_qa_test_cases", args)
    assert res["status"] == "success"
    assert res["result"]["test_count"] >= 3
    assert len(res["result"]["test_cases"]) >= 3


def test_mcp_call_evaluate_quality_gate():
    args = {
        "policy_name": "PRODUCTION_STRICT",
        "total_tests": 100,
        "passed_tests": 100,
        "failed_tests": 0,
        "critical_defects": 0,
        "rag_groundedness_score": 0.96,
    }
    res = call_tool("evaluate_quality_gate", args)
    assert res["status"] == "success"
    assert res["result"]["passed"] is True
    assert res["result"]["pass_rate"] == 1.0


@pytest.fixture
def sqlite_rag_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.database import Base

    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    TestingSessionLocal = sessionmaker(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_persistent_vector_index_db_storage_and_sync(sqlite_rag_db):
    # 1. Initialize persistent vector index with SQLite test DB session
    index = PersistentVectorIndex(db_session=sqlite_rag_db)

    chunk_a = DocumentChunk(
        document_id="ndc_pricing_policy",
        chunk_id="chk_ancillary_001",
        text="Checked baggage fees are 35 EUR per standard 23kg bag. Extra legroom exit row seats cost 45 EUR.",
        metadata={"category": "pricing", "author": "Airline Product"},
        embedding=[0.12, 0.45, 0.88, 0.05],
    )
    chunk_b = DocumentChunk(
        document_id="ndc_refund_policy",
        chunk_id="chk_refund_002",
        text="All cancellations on paid tickets trigger automated refunds within 48 business hours.",
        metadata={"category": "refunds", "author": "Finance Ops"},
        embedding=[0.02, 0.15, 0.22, 0.91],
    )

    index.add([chunk_a, chunk_b])

    # 2. Verify rows written to database
    db_records = sqlite_rag_db.query(RAGChunkModel).filter(
        RAGChunkModel.chunk_id.in_(["chk_ancillary_001", "chk_refund_002"])
    ).all()
    assert len(db_records) == 2
    assert any(r.document_id == "ndc_pricing_policy" for r in db_records)

    # 3. Create a clean empty index and sync from database
    fresh_index = PersistentVectorIndex(db_session=sqlite_rag_db)
    synced_count = fresh_index.sync_from_db()
    assert synced_count >= 2

    # 4. Search hydrated index
    search_res = fresh_index.search([0.12, 0.45, 0.88, 0.05], k=1)
    assert len(search_res) == 1
    top_chunk, score = search_res[0]
    assert top_chunk.chunk_id == "chk_ancillary_001"
    assert score > 0.99

