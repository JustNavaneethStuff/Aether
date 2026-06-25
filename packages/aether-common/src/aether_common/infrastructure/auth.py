from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from aether_common.contracts.auth import AuthUser


class JWTAuthProvider:
    def __init__(self, secret: str, algorithm: str = "HS256", expiry_hours: int = 24) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._expiry_hours = expiry_hours

    async def authenticate(self, token: str) -> AuthUser | None:
        try:
            payload: dict[str, Any] = jwt.decode(token, self._secret, algorithms=[self._algorithm])
            return AuthUser(user_id=payload["sub"], roles=payload.get("roles", []))
        except jwt.PyJWTError:
            return None

    async def create_token(self, user_id: str, roles: list[str] | None = None) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": user_id,
            "roles": roles or ["user"],
            "iat": now,
            "exp": now + timedelta(hours=self._expiry_hours),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)
