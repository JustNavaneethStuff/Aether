import pytest
from aether_common.contracts.agent import CompletionMessage, CompletionRequest
from aether_common.infrastructure.llm import MockLLMProvider


@pytest.mark.asyncio
async def test_mock_llm_complete() -> None:
    provider = MockLLMProvider()
    response = await provider.complete(
        CompletionRequest(messages=[CompletionMessage(role="user", content="Hello world")])
    )
    assert "Hello world" in response.content
    assert response.usage["total_tokens"] > 0
