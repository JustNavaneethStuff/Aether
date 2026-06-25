from typing import Protocol

from pydantic import BaseModel


class AuthUser(BaseModel):
    user_id: str
    roles: list[str] = []


class AuthProvider(Protocol):
    async def authenticate(self, token: str) -> AuthUser | None: ...
    async def create_token(self, user_id: str, roles: list[str] | None = None) -> str: ...
