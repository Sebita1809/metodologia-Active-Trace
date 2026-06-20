"""
app/core/rate_limiter.py — slowapi Limiter singleton.

The limiter uses an in-process MemoryStorage backend (IP-based, MVP scope).
Production upgrade: swap storage_uri for Redis when multi-process scaling is needed.

Implemented: C-03 (auth-jwt-2fa)
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
