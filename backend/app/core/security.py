"""Cryptographic utilities: AES-256-GCM encryption for PII at rest."""

import base64
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException
from jose import jwt

from app.core.config import get_settings


class AESCipher:
    """AES-256-GCM encrypt/decrypt for sensitive attributes.

    Output format (encrypt): base64(nonce + ciphertext + tag)
    Key: ENCRYPTION_KEY from settings (exactly 32 bytes)
    """

    @staticmethod
    def encrypt(plaintext: str) -> str:
        if plaintext is None:
            raise ValueError("Cannot encrypt None value")
        key = get_settings().ENCRYPTION_KEY.encode("utf-8")
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ciphertext).decode("utf-8")

    @staticmethod
    def decrypt(ciphertext_b64: str) -> str:
        if ciphertext_b64 is None:
            raise ValueError("Cannot decrypt None value")
        key = get_settings().ENCRYPTION_KEY.encode("utf-8")
        aesgcm = AESGCM(key)
        raw = base64.b64decode(ciphertext_b64)
        nonce = raw[:12]
        ciphertext = raw[12:]
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


def create_access_token(
    user_id: str,
    tenant_id: str,
    roles: list[str],
    expires_delta: timedelta | None = None,
) -> str:
    if expires_delta is None:
        expires_delta = timedelta(
            minutes=get_settings().ACCESS_TOKEN_EXPIRE_MINUTES
        )
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "roles": roles,
        "iat": now,
        "exp": now + expires_delta,
        "type": "access",
    }
    return jwt.encode(
        payload,
        get_settings().SECRET_KEY,
        algorithm="HS256",
    )


def create_refresh_token() -> str:
    return secrets.token_hex(64)


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            get_settings().SECRET_KEY,
            algorithms=["HS256"],
        )
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def create_temp_session_token(
    user_id: str,
    tenant_id: str,
    email: str,
) -> str:
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "roles": [],
        "email": email,
        "iat": now,
        "exp": now + timedelta(minutes=2),
        "type": "temp_session",
    }
    return jwt.encode(
        payload,
        get_settings().SECRET_KEY,
        algorithm="HS256",
    )
