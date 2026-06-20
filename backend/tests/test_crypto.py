"""
tests/test_crypto.py — TDD tests for CryptoService (AES-256-GCM).

TDD cycle:
  5.1 RED   — written before CryptoService exists; tests must fail at import.
  5.2 GREEN — implement app/core/crypto.py with CryptoService.
  5.3 GREEN — ENCRYPTION_KEY already validated in config.py (64 hex chars).
  5.4 TRIANGULATE — wrong key length in Settings raises ValidationError.

No DB required — pure unit tests.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_crypto(hex_key: str | None = None):
    """Return a CryptoService instance with a valid 64-char hex key."""
    from app.core.crypto import CryptoService  # noqa: PLC0415

    if hex_key is None:
        hex_key = "ab" * 32  # 64 hex chars = 32 bytes
    return CryptoService(key_hex=hex_key)


# ---------------------------------------------------------------------------
# 5.1 RED / 5.2 GREEN — Scenario: decrypt(encrypt(text)) == text
# ---------------------------------------------------------------------------

def test_encrypt_decrypt_round_trip():
    """decrypt(encrypt(plaintext)) must return the original plaintext."""
    svc = _make_crypto()
    plaintext = "Juan García — DNI 12345678"

    ciphertext = svc.encrypt(plaintext)
    recovered = svc.decrypt(ciphertext)

    assert recovered == plaintext


# ---------------------------------------------------------------------------
# 5.2 GREEN — Scenario: two encrypts produce different ciphertexts
# ---------------------------------------------------------------------------

def test_encrypt_produces_different_output_each_time():
    """Two encrypt calls on the same plaintext yield different ciphertexts (random IV)."""
    svc = _make_crypto()
    plaintext = "mismo_valor"

    ct1 = svc.encrypt(plaintext)
    ct2 = svc.encrypt(plaintext)

    assert ct1 != ct2, "Two encrypts of the same value must differ (IV must be random)"


# ---------------------------------------------------------------------------
# 5.2 GREEN — Scenario: tampered ciphertext raises exception
# ---------------------------------------------------------------------------

def test_tampered_ciphertext_raises_exception():
    """decrypt() must raise an exception when the ciphertext is modified."""
    svc = _make_crypto()
    ct = svc.encrypt("sensitive data")

    # Flip one byte in the ciphertext (alter a character in the base64 string)
    # Find a safe position to flip that won't hit padding
    ct_bytes = list(ct.encode())
    flip_idx = min(20, len(ct_bytes) - 1)
    # XOR the character to alter the value
    original = ct_bytes[flip_idx]
    ct_bytes[flip_idx] = ord('A') if chr(original) != 'A' else ord('B')
    tampered = bytes(ct_bytes).decode(errors="replace")

    with pytest.raises(Exception):
        svc.decrypt(tampered)


# ---------------------------------------------------------------------------
# 5.4 TRIANGULATE — Scenario: wrong-length ENCRYPTION_KEY fails at Settings
# ---------------------------------------------------------------------------

def test_settings_encryption_key_too_short_raises_validation_error(monkeypatch):
    """Settings with ENCRYPTION_KEY shorter than 64 hex chars raises ValidationError."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("SECRET_KEY", "s" * 32)
    monkeypatch.setenv("ENCRYPTION_KEY", "ab" * 15)  # 30 hex chars — too short

    from app.core.config import Settings  # noqa: PLC0415

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "ENCRYPTION_KEY" in str(exc_info.value) or "encryption_key" in str(exc_info.value).lower()


def test_settings_encryption_key_non_hex_raises_validation_error(monkeypatch):
    """Settings with non-hex ENCRYPTION_KEY raises ValidationError."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("SECRET_KEY", "s" * 32)
    monkeypatch.setenv("ENCRYPTION_KEY", "z" * 64)  # 64 chars but not hex

    from app.core.config import Settings  # noqa: PLC0415

    with pytest.raises(ValidationError):
        Settings()
