"""Sliding-window rate limiter — in-memory, per-key.

Defines the ``RateLimiter`` abstract interface and an ``InMemoryRateLimiter``
implementation backed by monotonic timestamp deques.  A module-level singleton
is provided for FastAPI dependency injection.

Exports:
    - ``RateLimiter`` (ABC)
    - ``InMemoryRateLimiter``
    - ``rate_limiter`` (singleton instance)
    - ``rate_limit_login`` (FastAPI dependency)
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Sequence

from fastapi import HTTPException, Request

__all__ = [
    "RateLimiter",
    "InMemoryRateLimiter",
    "rate_limiter",
    "rate_limit_login",
]


class RateLimiter(ABC):
    """Sliding-window rate limiter interface.

    Each tracked key has a window of ``window_seconds`` during which at most
    ``max_attempts`` calls to :meth:`record_attempt` are allowed.
    """

    @abstractmethod
    def is_rate_limited(self, key: str) -> bool:
        """Return ``True`` if *key* has exhausted its allowed attempts."""

    @abstractmethod
    def remaining_attempts(self, key: str) -> int:
        """Return how many more attempts *key* may make before being limited."""

    @abstractmethod
    def retry_after_seconds(self, key: str) -> int:
        """Return seconds until the oldest attempt slides out of the window."""

    @abstractmethod
    def record_attempt(self, key: str) -> None:
        """Record one attempt for *key* (called before hitting the endpoint)."""


class InMemoryRateLimiter(RateLimiter):
    """Sliding-window rate limiter backed by an in-memory dict.

    Thread-safe for the typical ASGI single-process deployment.  Stale entries
    are cleaned lazily on every public method call.

    Parameters
    ----------
    max_attempts:
        Maximum attempts allowed within the window (default 5).
    window_seconds:
        Width of the sliding window in seconds (default 60).
    """

    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: int = 60,
    ) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)

    # ── internal helpers ──────────────────────────────────────

    def _cleanup(self, key: str) -> None:
        """Remove timestamps outside the current window."""
        cutoff = time.monotonic() - self._window_seconds
        timestamps = self._attempts.get(key)
        if timestamps is not None:
            kept = [t for t in timestamps if t > cutoff]
            if kept:
                self._attempts[key] = kept
            else:
                del self._attempts[key]

    def _window_count(self, key: str) -> int:
        """Number of recorded attempts for *key* (after cleanup)."""
        self._cleanup(key)
        return len(self._attempts.get(key, []))

    # ── public interface ──────────────────────────────────────

    def is_rate_limited(self, key: str) -> bool:
        return self._window_count(key) >= self._max_attempts

    def remaining_attempts(self, key: str) -> int:
        return max(0, self._max_attempts - self._window_count(key))

    def retry_after_seconds(self, key: str) -> int:
        self._cleanup(key)
        timestamps = self._attempts.get(key)
        if not timestamps:
            return 0
        elapsed = time.monotonic() - timestamps[0]
        remaining = self._window_seconds - elapsed
        return max(0, int(remaining) + 1)

    def record_attempt(self, key: str) -> None:
        self._attempts[key].append(time.monotonic())


# ── module-level singleton ─────────────────────────────────────

rate_limiter = InMemoryRateLimiter()


# ── FastAPI dependency ─────────────────────────────────────────

async def rate_limit_login(request: Request) -> None:
    """FastAPI dependency — rate-limit login attempts per ``ip:email``.

    Extracts the client IP and (optional) email from the request body,
    builds a composite key ``ip:email``, and checks the shared in-memory
    rate limiter.  If the limit is exceeded a 429 response with a
    ``Retry-After`` header is raised immediately.
    """
    ip = request.client.host if request.client else "unknown"

    email = ""
    try:
        body = await request.json()
        if isinstance(body, dict):
            email = body.get("email", "") or ""
    except Exception:
        pass

    key = f"{ip}:{email}"

    if rate_limiter.is_rate_limited(key):
        retry_after = rate_limiter.retry_after_seconds(key)
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    rate_limiter.record_attempt(key)
