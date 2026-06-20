"""
app/core/crypto.py — AES-256-GCM encryption utility for PII at rest.

CryptoService encrypts/decrypts strings using AES-256-GCM with a random
12-byte IV per operation. The output format is:

    base64url(iv[12] || ciphertext[N] || tag[16])

This format allows decrypt() to recover the IV and tag without any
additional metadata stored alongside the ciphertext.

Decision reference: D4 — AES-256-GCM, IV aleatorio 12 bytes, base64url.
Library: cryptography (PyCA) — https://cryptography.io/

Security properties:
  - Authenticated encryption: any tampering of ciphertext, IV or tag
    raises cryptography.exceptions.InvalidTag (not silent data corruption).
  - Random IV per encrypt: encrypting the same plaintext twice produces
    different ciphertexts (semantic security).
  - Key never logged: the class does not expose the key via __repr__ or __str__.

Implemented: C-02 (core-models-y-tenancy)
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_IV_LENGTH = 12   # bytes — standard for AES-GCM
_TAG_LENGTH = 16  # bytes — AES-GCM authentication tag (appended by AESGCM)


class CryptoService:
    """AES-256-GCM encryption / decryption for PII strings.

    Parameters:
        key_hex — 64 lowercase hex characters (= 32 bytes / 256 bits).
                  Validated by Settings.encryption_key at startup.

    Raises:
        ValueError — if key_hex length or format is invalid.
        cryptography.exceptions.InvalidTag — if decrypt() receives a tampered
                                             or corrupt ciphertext.
    """

    def __init__(self, key_hex: str) -> None:
        if len(key_hex) != 64:
            raise ValueError(
                "CryptoService requires a 64-character hex string (32 bytes / AES-256)"
            )
        self._key: bytes = bytes.fromhex(key_hex)
        self._aesgcm = AESGCM(self._key)

    # Hide the raw key from accidental logging / repr
    def __repr__(self) -> str:
        return "CryptoService(<key hidden>)"

    def __str__(self) -> str:
        return "CryptoService(<key hidden>)"

    def encrypt(self, plaintext: str) -> str:
        """Encrypt *plaintext* and return a base64url-encoded token.

        The token encodes: IV (12 bytes) || ciphertext (N bytes) || GCM tag (16 bytes).
        A fresh random IV is generated for every call.

        Returns:
            str — base64url token (URL-safe, no padding).
        """
        iv: bytes = os.urandom(_IV_LENGTH)
        # AESGCM.encrypt returns ciphertext + tag concatenated
        ct_and_tag: bytes = self._aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
        token: bytes = iv + ct_and_tag
        return base64.urlsafe_b64encode(token).decode("ascii")

    def decrypt(self, token: str) -> str:
        """Decrypt a base64url token produced by encrypt().

        Raises:
            cryptography.exceptions.InvalidTag — if the token has been tampered
                with or is corrupt (authenticated encryption guarantee).
            ValueError — if the token is too short or malformed base64.
        """
        try:
            raw: bytes = base64.urlsafe_b64decode(token + "==")  # add padding tolerance
        except Exception as exc:
            raise ValueError(f"Invalid base64url token: {exc}") from exc

        if len(raw) < _IV_LENGTH + _TAG_LENGTH + 1:
            raise ValueError(
                f"Token too short: expected at least {_IV_LENGTH + _TAG_LENGTH + 1} bytes, "
                f"got {len(raw)}"
            )

        iv: bytes = raw[:_IV_LENGTH]
        ct_and_tag: bytes = raw[_IV_LENGTH:]

        # AESGCM.decrypt raises InvalidTag on any tamper
        plaintext_bytes: bytes = self._aesgcm.decrypt(iv, ct_and_tag, None)
        return plaintext_bytes.decode("utf-8")

    def hash_deterministic(self, value: str) -> str:
        """Return a deterministic HMAC-SHA256 hex digest of *value*.

        The value is normalized (strip + lowercase) before hashing so that
        equivalent email addresses produce the same hash regardless of
        whitespace or case variations.

        Used to enforce email uniqueness per tenant via a plain index without
        storing the plaintext email. The resulting hash is a 64-character
        lowercase hex string.

        Parameters:
            value — plaintext string to hash (e.g. an email address)

        Returns:
            str — 64-character lowercase hex string (HMAC-SHA256 digest)
        """
        normalized: str = value.strip().lower()
        digest: bytes = hmac.new(
            key=self._key,
            msg=normalized.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        return digest.hex()
