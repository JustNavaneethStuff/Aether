import pytest
from aether_common.infrastructure.embeddings import embedding_cosine, simple_embed
from aether_common.plugins.registry import BuiltinTools


def test_simple_embed_cosine_self() -> None:
    vec = simple_embed("hello world")
    assert embedding_cosine(vec, vec) == pytest.approx(1.0, abs=1e-6)


def test_calculator_tool() -> None:
    result = BuiltinTools.calculator({"expression": "2 + 2", "call_id": "1"}, {})
    assert result.success
    assert result.output == 4


@pytest.mark.asyncio
async def test_jwt_auth_roundtrip() -> None:
    from aether_common.infrastructure.auth import JWTAuthProvider

    provider = JWTAuthProvider("test-secret")
    token = await provider.create_token("user-1", ["admin"])
    user = await provider.authenticate(token)
    assert user is not None
    assert user.user_id == "user-1"
    assert "admin" in user.roles
