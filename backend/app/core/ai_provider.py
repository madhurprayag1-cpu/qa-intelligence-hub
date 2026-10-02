import math
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx


@dataclass
class AIResponse:
    text: str
    model: str
    provider: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None


class AIProvider(ABC):
    @abstractmethod
    async def generate(
        self, prompt: str, system: str | None = None, temperature: float = 0.0
    ) -> AIResponse:
        raise NotImplementedError


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


import zlib


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic, offline embedding generator using uniform term hashing and L2 normalization."""

    _STOPWORDS = {
        "a", "an", "the", "is", "are", "was", "were", "in", "on", "at",
        "to", "for", "of", "and", "or", "by", "with", "be", "all", "as", "it",
    }

    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vectorize(t) for t in texts]

    def _vectorize(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        words = re.findall(r"\w+", text.lower())
        if not words:
            return vec
        for word in words:
            if word in self._STOPWORDS:
                continue
            h = zlib.crc32(word.encode("utf-8")) % self.dim
            vec[h] += 1.0
            if len(word) >= 4:
                hp = zlib.crc32((word[:4] + "*").encode("utf-8")) % self.dim
                vec[hp] += 0.8
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [round(v / norm, 6) for v in vec]
        return vec


class MockAIProvider(AIProvider):
    """Deterministic, provider-independent mock for unit testing and offline evaluation."""

    def __init__(self, model_name: str = "mock-qa-model"):
        self.model_name = model_name
        self.custom_responses: dict[str, str] = {}

    def register_response(self, prompt_substring: str, response_text: str):
        self.custom_responses[prompt_substring] = response_text

    async def generate(
        self, prompt: str, system: str | None = None, temperature: float = 0.0
    ) -> AIResponse:
        start_time = time.perf_counter()

        text = None
        for key, resp in self.custom_responses.items():
            if key.lower() in prompt.lower():
                text = resp
                break

        if text is None:
            if "Context Information:\n" in prompt:
                ctx_start = prompt.find("Context Information:\n") + len("Context Information:\n")
                ctx_end = prompt.find("\n\nQuestion:", ctx_start)
                context_block = (
                    prompt[ctx_start:ctx_end].strip()
                    if ctx_end != -1
                    else prompt[ctx_start:].strip()
                )
                if context_block:
                    lines = [l.strip() for l in context_block.splitlines() if l.strip()]
                    clean_lines = [re.sub(r"^\[.*?\]:\s*", "", l) for l in lines]
                    first_evidence = clean_lines[0] if clean_lines else context_block
                    text = f"Based on the provided documentation: {first_evidence}"
                else:
                    text = "No relevant domain knowledge was found in the indexed sources to answer this question."

            if text is None:
                text = f"Mock response for prompt: {prompt[:80]}"

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return AIResponse(
            text=text,
            model=self.model_name,
            provider="mock",
            input_tokens=len(prompt.split()),
            output_tokens=len(text.split()),
            latency_ms=max(latency_ms, 1),
        )


class GeminiProvider(AIProvider):
    """Google Gemini AI Provider implementation."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-2.5-flash",
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = os.getenv("GEMINI_MODEL", model)

    async def generate(
        self, prompt: str, system: str | None = None, temperature: float = 0.0
    ) -> AIResponse:
        if not self.api_key:
            return AIResponse(
                text="[Gemini Mock]: API key not configured. Returning deterministic response.",
                model=self.model,
                provider="gemini",
                input_tokens=len(prompt.split()),
                output_tokens=10,
                latency_ms=5,
            )

        start = time.perf_counter()
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                latency_ms = int((time.perf_counter() - start) * 1000)

                return AIResponse(
                    text=text,
                    model=self.model,
                    provider="gemini",
                    input_tokens=len(prompt.split()),
                    output_tokens=len(text.split()),
                    latency_ms=latency_ms,
                )
            except httpx.HTTPStatusError as e:
                latency_ms = int((time.perf_counter() - start) * 1000)
                error_body = e.response.text
                return AIResponse(
                    text=f"[Gemini API Error {e.response.status_code}]: {error_body[:200]}",
                    model=self.model,
                    provider="gemini",
                    input_tokens=len(prompt.split()),
                    output_tokens=10,
                    latency_ms=latency_ms,
                )
            except Exception as e:
                latency_ms = int((time.perf_counter() - start) * 1000)
                return AIResponse(
                    text=f"[Gemini Error]: {str(e)}",
                    model=self.model,
                    provider="gemini",
                    input_tokens=len(prompt.split()),
                    output_tokens=10,
                    latency_ms=latency_ms,
                )


class ClaudeProvider(AIProvider):
    """Anthropic Claude AI Provider implementation."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-3-5-sonnet-20241022",
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model

    async def generate(
        self, prompt: str, system: str | None = None, temperature: float = 0.0
    ) -> AIResponse:
        if not self.api_key:
            return AIResponse(
                text="[Claude Mock]: API key not configured. Returning deterministic response.",
                model=self.model,
                provider="claude",
                input_tokens=len(prompt.split()),
                output_tokens=10,
                latency_ms=5,
            )

        start = time.perf_counter()
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data["content"][0]["text"]
            latency_ms = int((time.perf_counter() - start) * 1000)

            return AIResponse(
                text=text,
                model=self.model,
                provider="claude",
                latency_ms=latency_ms,
            )


class OpenAIProvider(AIProvider):
    """OpenAI AI Provider implementation."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model

    async def generate(
        self, prompt: str, system: str | None = None, temperature: float = 0.0
    ) -> AIResponse:
        if not self.api_key:
            return AIResponse(
                text="[OpenAI Mock]: API key not configured. Returning deterministic response.",
                model=self.model,
                provider="openai",
                input_tokens=len(prompt.split()),
                output_tokens=10,
                latency_ms=5,
            )

        start = time.perf_counter()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            latency_ms = int((time.perf_counter() - start) * 1000)

            return AIResponse(
                text=text,
                model=self.model,
                provider="openai",
                latency_ms=latency_ms,
            )


def get_ai_provider(name: str | None = None) -> AIProvider:
    """Factory function for provider-independent model acquisition."""
    provider_name = (name or os.getenv("AI_PROVIDER", "mock")).lower()

    if provider_name == "gemini":
        return GeminiProvider()
    elif provider_name == "claude":
        return ClaudeProvider()
    elif provider_name == "openai":
        return OpenAIProvider()
    else:
        return MockAIProvider()
