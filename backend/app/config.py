from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Stock Research Agent API"
    app_env: Literal["development", "testing", "staging", "production"] = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, ge=1, le=65535)
    api_v1_prefix: str = "/api/v1"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cors_origins: str = "http://localhost:3000"

    # AI
    ai_provider: Literal["openai", "groq", "huggingface"] = "groq"
    ai_request_timeout_seconds: float = Field(default=45.0, gt=0, le=300)
    ai_max_tool_calls: int = Field(default=5, ge=1, le=20)
    ai_store_responses: bool = False

    openai_api_key: SecretStr | None = None
    openai_model: str = ""

    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-20b"

    hf_token: SecretStr | None = None
    huggingface_model: str = "openai/gpt-oss-120b"
    huggingface_inference_provider: str = "auto"

    # Market data
    market_data_provider: Literal["mock", "upstox", "kite"] = "mock"
    market_data_status: Literal["mock", "end_of_day", "delayed", "real_time"] = "mock"
    market_exchange: str = "NSE"
    market_timezone: str = "Asia/Kolkata"
    market_default_interval: str = "1d"
    market_data_cache_ttl_seconds: int = Field(default=900, ge=0)

    upstox_api_key: SecretStr | None = None
    upstox_api_secret: SecretStr | None = None
    upstox_access_token: SecretStr | None = None
    upstox_redirect_uri: str = "http://localhost:8000/api/v1/auth/upstox/callback"

    kite_api_key: SecretStr | None = None
    kite_api_secret: SecretStr | None = None
    kite_access_token: SecretStr | None = None

    # Database
    database_url: SecretStr = SecretStr(
        "postgresql+asyncpg://stock_agent:stock_agent@localhost:5432/stock_agent"
    )
    database_pool_size: int = Field(default=5, ge=1, le=100)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_echo: bool = False

    # Authentication and request boundaries
    jwt_secret_key: SecretStr = SecretStr("replace_with_at_least_32_random_characters")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=1)
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = Field(default=30, ge=1)
    max_request_characters: int = Field(default=2000, ge=1, le=100_000)

    # Jobs and monitoring
    enable_scheduler: bool = False
    daily_price_job_hour: int = Field(default=18, ge=0, le=23)
    daily_price_job_minute: int = Field(default=0, ge=0, le=59)
    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    testing: bool = False

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if not value.startswith("/"):
            value = f"/{value}"
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        """Return normalized origins from the comma-separated setting."""

        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

    def require_ai_api_key(self) -> str:
        """Return the active provider key or raise a configuration error."""

        key_by_provider = {
            "openai": self.openai_api_key,
            "groq": self.groq_api_key,
            "huggingface": self.hf_token,
        }
        secret = key_by_provider[self.ai_provider]
        if secret is None or not secret.get_secret_value().strip():
            variable = {
                "openai": "OPENAI_API_KEY",
                "groq": "GROQ_API_KEY",
                "huggingface": "HF_TOKEN",
            }[self.ai_provider]
            raise RuntimeError(
                f"{variable} must be configured when AI_PROVIDER={self.ai_provider}."
            )
        return secret.get_secret_value()

    def active_ai_model(self) -> str:
        model_by_provider = {
            "openai": self.openai_model,
            "groq": self.groq_model,
            "huggingface": self.huggingface_model,
        }
        model = model_by_provider[self.ai_provider].strip()
        if not model:
            raise RuntimeError(
                f"A model must be configured for AI_PROVIDER={self.ai_provider}."
            )
        return model


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide, cached settings instance."""

    return Settings()
