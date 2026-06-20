"""
core/config.py — Typed application settings via Pydantic v2 + pydantic-settings.

Loaded from environment variables and/or a .env file.
Validated at startup: missing or invalid vars prevent the app from starting.

Implemented: C-01 (foundation-setup)
"""
from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unknown env vars (compose injects many extras)
        case_sensitive=False,
    )

    # --- Database ---
    database_url: str = Field(..., description="PostgreSQL async connection string (asyncpg)")
    test_database_url: str | None = Field(
        default=None,
        description="Separate PostgreSQL DB for pytest (optional at runtime)",
    )

    # --- Security (slots — logic implemented in C-03) ---
    secret_key: str = Field(..., description="JWT signing key (min 32 chars)")
    encryption_key: str = Field(
        ...,
        description="AES-256 key for PII at rest (exactly 64 hex chars = 32 bytes)",
    )
    access_token_expire_minutes: int = Field(
        default=15,
        ge=1,
        description="Access token TTL in minutes",
    )

    # --- Observability ---
    otel_enabled: bool = Field(default=False, description="Enable OpenTelemetry instrumentation")
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None,
        description="OTLP exporter endpoint (optional)",
    )

    # --- Application ---
    app_env: str = Field(default="development", description="Environment name")
    log_level: str = Field(default="INFO", description="Root log level")

    # --- CORS ---
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="Comma-separated list of allowed CORS origins",
    )

    # --- Moodle Web Services (C-09) ---
    moodle_base_url: str = Field(
        default="",
        description="Moodle site base URL (e.g. https://moodle.example.com)",
    )
    moodle_token: str = Field(
        default="",
        description="Moodle Web Services token",
    )

    # -------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------

    @field_validator("secret_key")
    @classmethod
    def secret_key_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("encryption_key")
    @classmethod
    def encryption_key_exact_length(cls, v: str) -> str:
        """Validate ENCRYPTION_KEY is exactly 64 lowercase hex chars (= 32 bytes / AES-256)."""
        import re  # noqa: PLC0415
        if len(v) != 64 or not re.fullmatch(r"[0-9a-fA-F]{64}", v):
            raise ValueError(
                "ENCRYPTION_KEY must be exactly 64 hexadecimal characters (= 32 bytes for AES-256)"
            )
        return v.lower()


# ---------------------------------------------------------------------------
# Module-level singleton — resolved lazily on first access.
#
# Production code (main.py lifespan) accesses `settings` after env vars are set.
# Tests that need a fresh instance should instantiate Settings() directly;
# the module-level singleton is NOT created until first access to avoid
# ValidationError when the module is imported in a bare test environment.
# ---------------------------------------------------------------------------
_settings: "Settings | None" = None


def get_settings() -> "Settings":
    """Return the module-level Settings singleton (created on first call)."""
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenience alias — import `settings` from this module in production code.
# Accessing this at module import time in tests WITHOUT env vars will raise.
# Use get_settings() in tests or override via dependency injection.
class _LazySettings:
    """Proxy that creates the Settings singleton on first attribute access."""

    def __getattr__(self, name: str):  # noqa: ANN001, ANN204
        return getattr(get_settings(), name)


settings: Settings = _LazySettings()  # type: ignore[assignment]
