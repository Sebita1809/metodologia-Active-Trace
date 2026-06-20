"""
Tests for core/config.py — Settings (Pydantic v2 / pydantic-settings).

TDD cycle:
  2.1 RED    — these tests run before implementation exists; they must fail.
  2.2 GREEN  — implement Settings; all pass.
  2.3 TRIANGULATE — extra edge cases added here.
"""
import os
import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_env(overrides: dict | None = None) -> dict:
    """Return a minimal valid env dict, with optional overrides."""
    base = {
        "DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/db",
        "SECRET_KEY": "a" * 32,
        "ENCRYPTION_KEY": "ab" * 32,  # 64 hex chars = 32 bytes for AES-256
        "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
        "APP_ENV": "development",
        "LOG_LEVEL": "INFO",
        "OTEL_ENABLED": "false",
    }
    if overrides:
        base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 2.1 — Scenario: Carga válida desde el entorno
# ---------------------------------------------------------------------------

def test_settings_instantiates_with_valid_env(monkeypatch):
    """Settings instantiates successfully when all required vars are present."""
    env = _make_env()
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    # Unset any .env file loading so we rely purely on the env
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("ENCRYPTION_KEY", env["ENCRYPTION_KEY"])

    from app.core.config import Settings  # noqa: PLC0415

    settings = Settings()
    assert settings.database_url == env["DATABASE_URL"]
    assert settings.access_token_expire_minutes == 15


def test_access_token_expire_minutes_default(monkeypatch):
    """ACCESS_TOKEN_EXPIRE_MINUTES defaults to 15 when not provided."""
    env = _make_env()
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)

    from app.core.config import Settings  # noqa: PLC0415

    settings = Settings()
    assert settings.access_token_expire_minutes == 15


# ---------------------------------------------------------------------------
# 2.2 — Scenario: Configuración inválida o incompleta
# ---------------------------------------------------------------------------

def test_settings_fails_when_database_url_missing(monkeypatch):
    """Settings raises ValidationError if DATABASE_URL is absent."""
    env = _make_env()
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from app.core.config import Settings  # noqa: PLC0415

    with pytest.raises((ValidationError, Exception)):
        Settings(_env_file=None)


# ---------------------------------------------------------------------------
# 2.3 TRIANGULATE — edge cases
# ---------------------------------------------------------------------------

def test_settings_fails_when_secret_key_too_short(monkeypatch):
    """SECRET_KEY shorter than 32 chars must fail validation."""
    env = _make_env({"SECRET_KEY": "tooshort"})
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    from app.core.config import Settings  # noqa: PLC0415

    with pytest.raises((ValidationError, ValueError)):
        Settings()


def test_settings_fails_when_encryption_key_wrong_length(monkeypatch):
    """ENCRYPTION_KEY that is not exactly 32 chars must fail validation."""
    env = _make_env({"ENCRYPTION_KEY": "tooshort"})
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    from app.core.config import Settings  # noqa: PLC0415

    with pytest.raises((ValidationError, ValueError)):
        Settings()


def test_settings_fails_when_expire_minutes_is_not_integer(monkeypatch):
    """ACCESS_TOKEN_EXPIRE_MINUTES with non-integer value must fail."""
    env = _make_env({"ACCESS_TOKEN_EXPIRE_MINUTES": "not_a_number"})
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    from app.core.config import Settings  # noqa: PLC0415

    with pytest.raises((ValidationError, ValueError)):
        Settings()
