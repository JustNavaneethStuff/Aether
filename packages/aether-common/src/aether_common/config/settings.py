from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "aether"
    log_level: str = "INFO"
    log_format: str = "json"
    redis_url: str = "redis://localhost:6379/0"
    otel_exporter_otlp_endpoint: str | None = None

    llm_provider: str = "openai"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-5-haiku-latest"
