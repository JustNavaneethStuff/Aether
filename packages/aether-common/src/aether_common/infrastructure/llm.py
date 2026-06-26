import time
from collections.abc import AsyncIterator

from aether_common.config.settings import BaseServiceSettings
from aether_common.contracts.agent import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
    StreamChunk,
)


class MockLLMProvider:
    """Fallback LLM for development without API keys."""

    def __init__(self, model: str = "mock") -> None:
        self._model = model

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        start = time.perf_counter()
        user_content = next(
            (m.content for m in reversed(request.messages) if m.role == "user"),
            "",
        )
        content = f"[mock response] Processed: {user_content[:500]}"
        latency_ms = int((time.perf_counter() - start) * 1000)
        return CompletionResponse(
            content=content,
            model=self._model,
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            latency_ms=latency_ms,
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        response = await self.complete(request)
        words = response.content.split()
        for i, word in enumerate(words):
            yield StreamChunk(content=word + " ", done=i == len(words) - 1)


class OpenAIAdapter:
    def __init__(self, api_key: str, model: str) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        start = time.perf_counter()
        response = await self._client.chat.completions.create(
            model=request.model or self._model,
            messages=[{"role": m.role, "content": m.content} for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        choice = response.choices[0].message
        usage = response.usage
        latency_ms = int((time.perf_counter() - start) * 1000)
        return CompletionResponse(
            content=choice.content or "",
            model=response.model,
            usage={
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            },
            latency_ms=latency_ms,
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        stream = await self._client.chat.completions.create(
            model=request.model or self._model,
            messages=[{"role": m.role, "content": m.content} for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield StreamChunk(content=delta, done=False)
        yield StreamChunk(content="", done=True)


class AnthropicAdapter:
    def __init__(self, api_key: str, model: str) -> None:
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        start = time.perf_counter()
        system = next((m.content for m in request.messages if m.role == "system"), None)
        messages = [{"role": m.role, "content": m.content} for m in request.messages if m.role != "system"]
        kwargs: dict = {
            "model": request.model or self._model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if system:
            kwargs["system"] = system

        response = await self._client.messages.create(**kwargs)
        content = response.content[0].text if response.content else ""
        latency_ms = int((time.perf_counter() - start) * 1000)
        return CompletionResponse(
            content=content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            latency_ms=latency_ms,
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        response = await self.complete(request)
        yield StreamChunk(content=response.content, done=True)


def create_llm_provider(settings: BaseServiceSettings) -> LLMProvider:
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return OpenAIAdapter(settings.openai_api_key, settings.openai_model)
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        return AnthropicAdapter(settings.anthropic_api_key, settings.anthropic_model)
    return MockLLMProvider()
