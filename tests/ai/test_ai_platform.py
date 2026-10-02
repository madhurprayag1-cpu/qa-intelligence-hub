import pytest
from app.core.ai_provider import (
    ClaudeProvider,
    GeminiProvider,
    MockAIProvider,
    MockEmbeddingProvider,
    OpenAIProvider,
    get_ai_provider,
)
from agents import DefectRCAAgent, RequirementAgent
from evaluation import (
    answer_relevance,
    exact_match,
    groundedness,
    retrieval_metrics,
)
from rag import Chunker, RAGPipeline, VectorIndex


# --- 1. AI Provider Abstraction Tests ---
def test_provider_switching_factory():
    mock_p = get_ai_provider("mock")
    assert isinstance(mock_p, MockAIProvider)

    gemini_p = get_ai_provider("gemini")
    assert isinstance(gemini_p, GeminiProvider)
    assert gemini_p.model == "gemini-2.5-flash"

    claude_p = get_ai_provider("claude")
    assert isinstance(claude_p, ClaudeProvider)
    assert "claude" in claude_p.model

    openai_p = get_ai_provider("openai")
    assert isinstance(openai_p, OpenAIProvider)
    assert "gpt" in openai_p.model


@pytest.mark.anyio
async def test_mock_provider_deterministic_generation():
    provider = MockAIProvider(model_name="test-llm")
    provider.register_response("3DS rules", "Cardholder authentication is mandatory.")

    res = await provider.generate("Tell me about 3DS rules in airline checkout")
    assert res.text == "Cardholder authentication is mandatory."
    assert res.model == "test-llm"
    assert res.provider == "mock"
    assert res.latency_ms is not None and res.latency_ms >= 1


@pytest.mark.anyio
async def test_cloud_providers_safe_offline_fallback():
    # When API keys are unset, cloud adapters safely return deterministic mock responses
    gemini = GeminiProvider(api_key="")
    g_res = await gemini.generate("Explain NDC protocols")
    assert "[Gemini Mock]" in g_res.text
    assert g_res.provider == "gemini"

    claude = ClaudeProvider(api_key="")
    c_res = await claude.generate("Explain booking status")
    assert "[Claude Mock]" in c_res.text
    assert c_res.provider == "claude"

    openai = OpenAIProvider(api_key="")
    o_res = await openai.generate("Explain refund rules")
    assert "[OpenAI Mock]" in o_res.text
    assert o_res.provider == "openai"


# --- 2. RAG Ingestion & Vector Retrieval Tests ---
def test_chunker_sliding_window():
    chunker = Chunker(chunk_size=10, overlap=3)
    text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12 word13"
    chunks = chunker.chunk("DOC-TEST", text, {"source": "manual.md"})

    assert len(chunks) >= 2
    assert chunks[0].document_id == "DOC-TEST"
    assert chunks[0].metadata["source"] == "manual.md"
    assert chunks[0].metadata["total_chunks"] == len(chunks)


def test_vector_index_ranking():
    embedder = MockEmbeddingProvider(dim=32)
    pipeline = RAGPipeline(embedding_provider=embedder)

    pipeline.ingest_document(
        document_id="DOC-BAGGAGE",
        text="Cabin baggage allowance is 8kg. Excess baggage costs 45 EUR per piece.",
        metadata={"category": "ancillaries"},
    )
    pipeline.ingest_document(
        document_id="DOC-REFUNDS",
        text="Tickets can be refunded up to 24 hours prior to flight departure.",
        metadata={"category": "policies"},
    )

    results = pipeline.retrieve("What is the baggage weight limit?", k=2)
    assert len(results) == 2
    top_chunk, score = results[0]
    assert top_chunk.document_id == "DOC-BAGGAGE"
    assert score > 0.0


@pytest.mark.anyio
async def test_rag_query_pipeline_with_citations():
    pipeline = RAGPipeline()
    pipeline.ingest_document(
        document_id="DOC-NDC",
        text="OrderCreate generates an NDC OrderID with status CONFIRMED.",
        metadata={"source": "ndc_spec.pdf"},
    )

    query_res = await pipeline.query("How does OrderCreate behave?", k=1)
    assert query_res.question == "How does OrderCreate behave?"
    assert len(query_res.retrieved_chunks) == 1
    assert "ndc_spec.pdf" in query_res.citations[0]
    assert query_res.latency_ms >= 0


# --- 3. Retrieval & Generation Evaluation Tests ---
def test_retrieval_metrics_calculation():
    expected = {"chunk_1", "chunk_2", "chunk_3"}
    retrieved = ["chunk_1", "chunk_2", "chunk_99"]

    metrics = retrieval_metrics(expected, retrieved)
    assert metrics["recall"] == round(2 / 3, 4)
    assert metrics["precision"] == round(2 / 3, 4)
    assert metrics["hit_rate"] == 1.0
    assert metrics["f1"] == round(2 / 3, 4)


def test_groundedness_supported_claims():
    context = "Passengers may select standard seats for free or extra legroom seats for 25 EUR."
    answer = "Extra legroom seats cost 25 EUR."

    eval_result = groundedness(answer, context)
    assert eval_result.passed is True
    assert eval_result.score >= 0.8
    assert "Grounded" in eval_result.reason


def test_groundedness_detects_hallucination():
    context = "Flights to Thessaloniki operate daily from Athens."
    answer = "Passengers receive free champagne and helicopter transfers to Olympus."

    eval_result = groundedness(answer, context)
    assert eval_result.passed is False
    assert eval_result.score < 0.5
    assert "Hallucination" in eval_result.reason


def test_answer_relevance_evaluation():
    question = "What payment methods are supported?"
    relevant_ans = "Supported payment methods include Credit Card, UPI, and Cash."
    irrelevant_ans = "The weather in Athens is sunny and 22 degrees."

    assert answer_relevance(question, relevant_ans).passed is True
    assert answer_relevance(question, irrelevant_ans).passed is False


# --- 4. Agentic QA & Defect RCA Agent Tests ---
@pytest.mark.anyio
async def test_defect_rca_agent_diagnosis():
    agent = DefectRCAAgent()

    # 3DS Timeout simulation
    run_timeout = await agent.execute(
        task="Diagnose payment failure",
        context={"error_msg": "3DS authentication timed out", "failure_code": "3DS_TIMEOUT", "endpoint": "/payments"},
    )
    assert run_timeout.status == "COMPLETED"
    assert "GATEWAY_OR_3DS_TIMEOUT" in run_timeout.output
    assert "HIGH" in run_timeout.output
    assert len(run_timeout.events) >= 3

    # Overbooking / Conflict simulation
    run_conflict = await agent.execute(
        task="Diagnose booking failure",
        context={"status_code": 409, "error_msg": "Insufficient seat availability", "endpoint": "/bookings"},
    )
    assert "INSUFFICIENT_INVENTORY_OR_DUPLICATE" in run_conflict.output


@pytest.mark.anyio
async def test_requirement_agent_scenario_generation():
    agent = RequirementAgent()
    run = await agent.execute("3DS 2.0 Strong Customer Authentication")
    assert run.status == "COMPLETED"
    assert "Positive:" in run.output
    assert "Negative:" in run.output
    assert "Boundary:" in run.output


# --- 5. FastAPI Endpoints Integration Tests ---
def test_api_list_ai_providers(client):
    resp = client.get("/ai/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "mock" in data["supported_providers"]
    assert "gemini" in data["supported_providers"]


def test_api_check_groundedness(client):
    resp = client.post(
        "/ai/evaluate/groundedness",
        json={
            "answer": "Athens airport code is ATH.",
            "context": "Athens International Airport uses IATA code ATH.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric"] == "groundedness"
    assert data["passed"] is True
    assert data["score"] >= 0.75


def test_api_execute_rag_query(client):
    resp = client.post(
        "/ai/rag/query",
        json={"question": "What happens if 3DS authentication fails?", "k": 2},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert len(data["citations"]) > 0
    assert "evaluation" in data
    assert "groundedness" in data["evaluation"]


def test_api_diagnose_rca_failure(client):
    resp = client.post(
        "/ai/rca",
        json={
            "error_message": "3DS timeout waiting for bank challenge",
            "failure_code": "3DS_TIMEOUT",
            "endpoint": "/payments",
            "status_code": 201,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert "GATEWAY_OR_3DS_TIMEOUT" in data["output"]
    assert len(data["events"]) >= 3
