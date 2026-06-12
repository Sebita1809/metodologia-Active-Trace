"""Tests for core.config — Settings validation (C-01)."""

import os
from typing import AsyncGenerator
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all known env vars that Settings reads."""
    for key in [
        "DATABASE_URL",
        "SECRET_KEY",
        "ENCRYPTION_KEY",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "OTEL_SERVICE_NAME",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
    ]:
        monkeypatch.delenv(key, raising=False)


class TestSettingsValidEnv:
    """2.1 (RED) — Settings instantiates correctly with valid env."""

    def test_valid_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """WHEN required env vars are present and valid THEN Settings instantiates."""
        _clean_env(monkeypatch)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/test")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("ENCRYPTION_KEY", "b" * 32)

        settings = Settings()  # type: ignore[call-arg]

        assert settings.DATABASE_URL == "postgresql+asyncpg://u:p@localhost:5432/test"
        assert settings.SECRET_KEY == "a" * 32
        assert settings.ENCRYPTION_KEY == "b" * 32
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 15

    def test_custom_access_token_expire(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """WHEN ACCESS_TOKEN_EXPIRE_MINUTES is provided THEN it overrides default."""
        _clean_env(monkeypatch)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/test")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("ENCRYPTION_KEY", "b" * 32)
        monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

        settings = Settings()

        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30


class TestSettingsInvalidEnv:
    """2.3 (TRIANGULATE) — Settings fails with invalid or missing env."""

    def test_missing_required_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """WHEN a required var is missing THEN Settings raises ValidationError."""
        _clean_env(monkeypatch)
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("ENCRYPTION_KEY", "b" * 32)
        # DATABASE_URL is NOT set

        with pytest.raises(ValidationError):
            Settings()

    def test_invalid_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """WHEN a var has invalid type THEN Settings raises ValidationError."""
        _clean_env(monkeypatch)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/test")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("ENCRYPTION_KEY", "b" * 32)
        monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "not-a-number")

        with pytest.raises(ValidationError):
            Settings()
