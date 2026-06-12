"""Configuration management via Pydantic v2 Settings.

Loaded from environment variables / .env file. Validated at boot time.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings — single source of truth for env vars."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL connection string (asyncpg)",
        examples=["postgresql+asyncpg://user:pass@localhost:5432/activia_trace"],
    )

    # ── Security ──────────────────────────────────────────────
    SECRET_KEY: str = Field(
        ...,
        min_length=32,
        description="Secret key for JWT signing (minimum 32 characters)",
    )

    ENCRYPTION_KEY: str = Field(
        ...,
        min_length=32,
        max_length=32,
        description="AES-256 encryption key (exactly 32 characters)",
    )

    # ── Auth ──────────────────────────────────────────────────
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15,
        ge=1,
        description="JWT access token lifetime in minutes",
    )

    # ── OpenTelemetry (optional) ──────────────────────────────
    OTEL_SERVICE_NAME: str | None = Field(
        default=None,
        description="OpenTelemetry service name",
    )

    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = Field(
        default=None,
        description="OpenTelemetry OTLP exporter endpoint",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of Settings.

    Use this function instead of ``Settings()`` directly to avoid
    re-reading ``.env`` on every call and to allow tests to
    override env vars before the first call.
    """
    return Settings()
