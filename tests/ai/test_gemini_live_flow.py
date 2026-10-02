import pytest
import httpx
from app.core.ai_provider import GeminiProvider, AIResponse
from agents import DefectRCAAgent, RequirementAgent
from rag import RAGPipeline


@pytest.mark.anyio
async def test_gemini_provider_live_flow_mock_transport():
    """Verify GeminiProvider parses Google Generative Language API response format correctly."""
    def mock_handler(request: httpx.Request):
        assert "generativelanguage.googleapis.com" in str(request.url)
        assert "key=fake-live-gemini-key" in str(request.url)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "3DS 2.0 requires step-up authentication challenge for high-risk transactions."}
                            ]
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(mock_handler)
    provider = GeminiProvider(api_key="fake-live-gemini-key", model="gemini-1.5-flash")

    # Patch httpx.AsyncClient to use mock transport for live Google API contract simulation
    original_client = httpx.AsyncClient
    try:
        def custom_client(**kwargs):
            kwargs["transport"] = transport
            return original_client(**kwargs)

        httpx.AsyncClient = custom_client

        res = await provider.generate("Explain 3DS 2.0 in airline checkout")
        assert "step-up authentication challenge" in res.text
        assert res.provider == "gemini"
        assert res.model == "gemini-1.5-flash"
        assert res.latency_ms >= 0
    finally:
        httpx.AsyncClient = original_client


@pytest.mark.anyio
async def test_gemini_provider_handles_quota_gracefully():
    """Verify GeminiProvider catches HTTP 429 quota errors gracefully without crashing."""
    def mock_handler(request: httpx.Request):
        return httpx.Response(429, text='{"error": {"message": "Resource has been exhausted (e.g. check quota)."}}')

    transport = httpx.MockTransport(mock_handler)
    provider = GeminiProvider(api_key="exhausted-key", model="gemini-1.5-flash")

    original_client = httpx.AsyncClient
    try:
        def custom_client(**kwargs):
            kwargs["transport"] = transport
            return original_client(**kwargs)

        httpx.AsyncClient = custom_client

        res = await provider.generate("Generate test cases")
        assert "[Gemini API Error 429]" in res.text
        assert res.provider == "gemini"
    finally:
        httpx.AsyncClient = original_client


@pytest.mark.anyio
async def test_rag_and_agent_integrate_with_live_provider():
    """Verify RAGPipeline and DefectRCAAgent execute seamlessly through the live provider abstraction."""
    provider = GeminiProvider(api_key="")  # Uses deterministic hermetic mock
    pipeline = RAGPipeline(ai_provider=provider)
    pipeline.ingest_document("TEST-DOC", "Refunds require 24 hours notice.")

    rag_res = await pipeline.query("How do refunds work?", k=1)
    assert rag_res.provider == "gemini"
    assert rag_res.answer != ""

    agent = DefectRCAAgent(ai_provider=provider)
    run = await agent.execute("Diagnose payment timeout", context={"failure_code": "3DS_TIMEOUT"})
    assert run.status == "COMPLETED"
