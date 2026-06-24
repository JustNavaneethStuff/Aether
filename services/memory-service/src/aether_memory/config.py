from aether_common.config.settings import BaseServiceSettings
from pydantic_settings import SettingsConfigDict


class MemorySettings(BaseServiceSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "memory-service"
    postgres_url: str = "postgresql+asyncpg://aether:aether@localhost:5432/aether"
    host: str = "0.0.0.0"
    port: int = 8002
