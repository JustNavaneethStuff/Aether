"""Integration tests — require running services (docker compose up)."""

import os

import httpx
import pytest

GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{GATEWAY_URL}/health", timeout=5.0)
        except httpx.ConnectError:
            pytest.skip("Services not running")
        assert response.status_code == 200
        assert "status" in response.json()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_orchestration_workflow() -> None:
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            create_resp = await client.post(f"{GATEWAY_URL}/v1/conversations", json={})
        except httpx.ConnectError:
            pytest.skip("Services not running")

        assert create_resp.status_code == 200
        conversation_id = create_resp.json()["id"]

        stream_resp = await client.post(
            f"{GATEWAY_URL}/v1/conversations/{conversation_id}/messages",
            json={"content": "Explain the CAP theorem briefly"},
        )
        assert stream_resp.status_code == 200
        assert "text/event-stream" in stream_resp.headers.get("content-type", "")

        messages_resp = await client.get(
            f"{GATEWAY_URL}/v1/conversations/{conversation_id}/messages"
        )
        assert messages_resp.status_code == 200
        messages = messages_resp.json()
        assert len(messages) >= 2
