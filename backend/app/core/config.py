from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


AIProviderMode = Literal["none", "openai_compatible", "local"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Café Aramesh Smart Menu API"
    environment: str = "development"
    database_url: str = (
        "postgresql+psycopg://aramesh:aramesh-local-only@localhost:5432/aramesh"
    )
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    ai_provider: AIProviderMode = "none"
    ai_base_url: str | None = None
    ai_model: str | None = None
    ai_api_key: str | None = None
    ai_timeout_seconds: float = 8.0
    feature_online_ordering_enabled: bool = False
    feature_ai_agent_enabled: bool = False
    feature_ai_support_enabled: bool = False


settings = Settings()
