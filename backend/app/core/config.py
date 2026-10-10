from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AIProviderMode = Literal["none", "openai_compatible", "local"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Café Aramesh Smart Menu API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://aramesh:aramesh-local-only@localhost:5432/aramesh"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    default_cafe_slug: str = "cafe-aramesh"
    ai_provider: AIProviderMode = "none"
    ai_base_url: str | None = None
    ai_model: str | None = None
    ai_api_key: str | None = None
    ai_timeout_seconds: float = 8.0
    jwt_secret_key: str = "dev-jwt-secret-change-before-production"
    order_code_hmac_secret: str = "dev-order-code-secret-change-before-production"
    jwt_access_minutes: int = 15
    jwt_refresh_days: int = 14
    order_code_digits: int = 4
    order_code_ttl_minutes: int = 15
    order_code_max_attempts: int = 5
    customer_session_days: int = 7
    cookie_secure: bool = False
    demo_staff_email: str = "staff@aramesh.local"
    demo_staff_password: str = "StaffDemo!2026"
    demo_merchant_email: str = "merchant@aramesh.local"
    demo_merchant_password: str = "MerchantDemo!2026"
    feature_online_ordering_enabled: bool = False
    feature_ai_agent_enabled: bool = False
    feature_ai_support_enabled: bool = False

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.order_code_digits not in (3, 4):
            raise ValueError("ORDER_CODE_DIGITS must be 3 or 4")
        if self.order_code_ttl_minutes < 1:
            raise ValueError("ORDER_CODE_TTL_MINUTES must be positive")
        if self.order_code_max_attempts < 1:
            raise ValueError("ORDER_CODE_MAX_ATTEMPTS must be positive")
        if self.environment.lower() == "production":
            if self.jwt_secret_key == "dev-jwt-secret-change-before-production" or len(self.jwt_secret_key) < 32:
                raise ValueError("JWT_SECRET_KEY must be a strong production secret of at least 32 characters")
            if self.order_code_hmac_secret == "dev-order-code-secret-change-before-production" or len(self.order_code_hmac_secret) < 32:
                raise ValueError("ORDER_CODE_HMAC_SECRET must be a strong production secret of at least 32 characters")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production")
        return self


settings = Settings()
