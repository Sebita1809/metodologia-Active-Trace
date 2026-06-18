"""Cryptographic utilities: AES-256-GCM encryption for PII at rest."""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

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
