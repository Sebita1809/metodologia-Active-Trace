"""
tests/test_moodle_ws.py — TDD tests for the Moodle WS client (tasks 5.1, 5.3).

These tests mock only the HTTP layer (httpx) — no DB interaction.

Tests:
  5.1 — MoodleWSClient.fetch_padron with mocked HTTP returns normalized EntradaCruda list
  5.3 — Transient errors are retried before propagating as MoodleIntegrationError
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.integrations.moodle_ws import EntradaCruda, MoodleIntegrationError, MoodleWSClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status_code: int, json_data: object) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


SAMPLE_ENROLLED_USERS = [
    {"firstname": "Ana",   "lastname": "García",  "email": "ana@moodle.com",   "department": "A1", "institution": "Norte"},
    {"firstname": "Bruno", "lastname": "López",   "email": "bruno@moodle.com", "department": "",   "institution": ""},
]


# ---------------------------------------------------------------------------
# Task 5.1 — fetch_padron with mocked HTTP returns normalized EntradaCruda
# ---------------------------------------------------------------------------

async def test_fetch_padron_returns_normalized_entries():
    """fetch_padron returns a list of EntradaCruda from a mocked HTTP response."""
    client = MoodleWSClient(base_url="https://moodle.example.com", token="testtoken")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_client.request = AsyncMock(return_value=_mock_response(200, SAMPLE_ENROLLED_USERS))

        entradas = await client.fetch_padron("123")

    assert len(entradas) == 2
    assert all(isinstance(e, EntradaCruda) for e in entradas)

    emails = [e.email for e in entradas]
    assert "ana@moodle.com" in emails
    assert "bruno@moodle.com" in emails

    ana = next(e for e in entradas if e.email == "ana@moodle.com")
    assert ana.nombre == "Ana"
    assert ana.apellidos == "García"
    assert ana.comision == "A1"
    assert ana.regional == "Norte"

    bruno = next(e for e in entradas if e.email == "bruno@moodle.com")
    assert bruno.comision is None
    assert bruno.regional is None


async def test_fetch_padron_skips_users_with_missing_fields():
    """Users with missing required fields are skipped (not raised as errors)."""
    client = MoodleWSClient(base_url="https://moodle.example.com", token="tok")

    bad_users = [
        {"firstname": "",    "lastname": "García", "email": "ok@ok.com"},  # missing firstname
        {"firstname": "Ana", "lastname": "",        "email": "ana@ok.com"},  # missing lastname
        {"firstname": "Bob", "lastname": "Smith",   "email": "bob@ok.com"},  # valid
    ]

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_client.request = AsyncMock(return_value=_mock_response(200, bad_users))

        entradas = await client.fetch_padron("abc")

    assert len(entradas) == 1
    assert entradas[0].nombre == "Bob"


async def test_fetch_padron_raises_moodle_error_on_http_error():
    """fetch_padron raises MoodleIntegrationError on 4xx without retrying."""
    client = MoodleWSClient(base_url="https://moodle.example.com", token="tok")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_client.request = AsyncMock(return_value=_mock_response(403, {}))

        with pytest.raises(MoodleIntegrationError):
            await client.fetch_padron("xyz")


# ---------------------------------------------------------------------------
# Task 5.3 — transient errors retried; MoodleIntegrationError after exhaustion
# ---------------------------------------------------------------------------

async def test_fetch_padron_retries_on_5xx():
    """fetch_padron retries on HTTP 5xx and succeeds on the last attempt."""
    import httpx  # noqa: PLC0415
    client = MoodleWSClient(base_url="https://moodle.example.com", token="tok")

    call_count = 0

    async def flaky_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return _mock_response(503, {})
        return _mock_response(200, SAMPLE_ENROLLED_USERS)

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_client.request = flaky_request

        with patch("asyncio.sleep", new_callable=AsyncMock):
            entradas = await client.fetch_padron("course1")

    assert call_count == 3
    assert len(entradas) == 2


async def test_fetch_padron_raises_after_all_retries_exhausted():
    """fetch_padron raises MoodleIntegrationError after all 3 attempts fail."""
    client = MoodleWSClient(base_url="https://moodle.example.com", token="tok")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_client.request = AsyncMock(return_value=_mock_response(502, {}))

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(MoodleIntegrationError):
                await client.fetch_padron("failing-course")


async def test_fetch_padron_retries_on_network_error():
    """fetch_padron retries on httpx.NetworkError and raises after exhaustion."""
    import httpx  # noqa: PLC0415
    client = MoodleWSClient(base_url="https://moodle.example.com", token="tok")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_client.request = AsyncMock(
            side_effect=httpx.NetworkError("connection refused")
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(MoodleIntegrationError):
                await client.fetch_padron("bad-course")
