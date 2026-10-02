from agents import QAAgent
from evaluation import exact_match
from rag import DocumentChunk, RAGPipeline


def test_ai_evaluation_exact_match():
    res_pass = exact_match("Booking confirmed", "Booking confirmed")
    assert res_pass.passed is True
    assert res_pass.score == 1.0

    res_fail = exact_match("CONFIRMED", "CANCELLED")
    assert res_fail.passed is False
    assert res_fail.score == 0.0


def test_qa_agent_planning():
    agent = QAAgent("agent-sdet-01")
    run = agent.plan("Verify 3DS timeout edge cases")
    assert run.agent_id == "agent-sdet-01"
    assert run.task == "Verify 3DS timeout edge cases"
    assert run.status == "PLANNED"


def test_rag_pipeline_ingest():
    pipeline = RAGPipeline()
    chunks = [
        DocumentChunk(
            document_id="DOC-01",
            chunk_id="CHK-01",
            text="3D Secure 2.0 provides frictionless and challenge flows.",
            metadata={"source": "compliance_guide.md"},
        )
    ]
    ingested_count = pipeline.ingest(chunks)
    assert ingested_count == 1
