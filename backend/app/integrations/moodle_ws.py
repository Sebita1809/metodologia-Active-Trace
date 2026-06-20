"""
app/integrations/moodle_ws.py — Moodle Web Services async client.

Provides an isolated async HTTP client for the Moodle LMS Web Services API.
All HTTP errors from the LMS are translated to MoodleIntegrationError,
which the router/service maps to HTTP 502.

Key design decisions (from C-09 design.md D6):
  - Isolated client: no coupling to SQLAlchemy or domain models.
  - Typed exception: MoodleIntegrationError (not raw HTTP errors).
  - Retry policy: 3 attempts, exponential backoff (0.5s → 1s → 2s), timeout 30s.
  - Only complete data triggers a version activation (no partial state).

Retry policy:
  - Attempts: 3
  - Backoff: 0.5s, 1s, 2s (wait before attempt 2, 3)
  - Timeout: 30s per request
  - Retry triggers: httpx.TimeoutException, httpx.NetworkError, HTTP 5xx

Implemented: C-09 (padron-ingesta-moodle)
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = [0.5, 1.0, 2.0]  # wait before attempt i+1 (index = attempt number - 1)
_TIMEOUT_SECONDS = 30.0


class MoodleIntegrationError(Exception):
    """Raised when the Moodle LMS is unreachable or returns an error response.

    The router maps this to HTTP 502 Bad Gateway.
    """

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class EntradaCruda:
    """Raw padrón entry returned by the Moodle WS API.

    Field names match the Moodle WS response contract.
    No PII encryption here — encryption is the responsibility of PadronService.
    """

    nombre: str
    apellidos: str
    email: str
    comision: str | None = None
    regional: str | None = None


class MoodleWSClient:
    """Async Moodle Web Services client.

    Parameters:
        base_url — Moodle site URL (e.g. "https://moodle.example.com")
        token    — Moodle Web Services token

    The client is stateless and does not hold any DB session.
    """

    def __init__(self, *, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token

    async def fetch_padron(self, curso_ref: str) -> list[EntradaCruda]:
        """Fetch the student roster for a Moodle course.

        Parameters:
            curso_ref — Moodle course shortname or numeric ID

        Returns:
            List of EntradaCruda parsed from the Moodle WS response.

        Raises:
            MoodleIntegrationError — on network error, timeout, or HTTP >= 400
                                     after all retries are exhausted.
        """
        params = {
            "wstoken": self._token,
            "wsfunction": "core_enrol_get_enrolled_users",
            "moodlewsrestformat": "json",
            "courseid": curso_ref,
        }
        raw = await self._request_with_retry(
            method="GET",
            url=f"{self._base_url}/webservice/rest/server.php",
            params=params,
        )

        return _parse_enrolled_users(raw)

    async def fetch_actividades(self, curso_ref: str) -> list[dict]:
        """Fetch activity completions for a Moodle course.

        Parameters:
            curso_ref — Moodle course shortname or numeric ID

        Returns:
            Raw list of activity dicts from the Moodle WS response.

        Raises:
            MoodleIntegrationError — on network error, timeout, or HTTP >= 400
                                     after all retries are exhausted.
        """
        params = {
            "wstoken": self._token,
            "wsfunction": "core_completion_get_activities_completion_status",
            "moodlewsrestformat": "json",
            "courseid": curso_ref,
        }
        raw = await self._request_with_retry(
            method="GET",
            url=f"{self._base_url}/webservice/rest/server.php",
            params=params,
        )

        if isinstance(raw, dict):
            return raw.get("statuses", [])
        if isinstance(raw, list):
            return raw
        return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request_with_retry(
        self,
        *,
        method: str,
        url: str,
        params: dict | None = None,
        json: dict | None = None,
    ) -> dict | list:
        """Execute an HTTP request with retry + exponential backoff.

        Retries on:
          - httpx.TimeoutException
          - httpx.NetworkError
          - HTTP 5xx responses

        Raises MoodleIntegrationError after all retries are exhausted,
        or immediately on HTTP 4xx (client errors are not retried).
        """
        last_exc: Exception | None = None

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                    response = await client.request(
                        method,
                        url,
                        params=params,
                        json=json,
                    )

                if response.status_code >= 500:
                    last_exc = MoodleIntegrationError(
                        f"Moodle returned HTTP {response.status_code} on attempt {attempt}",
                        status_code=response.status_code,
                    )
                    logger.warning(
                        "Moodle WS HTTP %d on attempt %d/%d",
                        response.status_code,
                        attempt,
                        _MAX_ATTEMPTS,
                    )
                    if attempt < _MAX_ATTEMPTS:
                        await asyncio.sleep(_BACKOFF_SECONDS[attempt - 1])
                    continue

                if response.status_code >= 400:
                    # 4xx — client error, do not retry
                    raise MoodleIntegrationError(
                        f"Moodle returned HTTP {response.status_code} (client error)",
                        status_code=response.status_code,
                    )

                return response.json()  # type: ignore[no-any-return]

            except MoodleIntegrationError:
                raise
            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning(
                    "Moodle WS timeout on attempt %d/%d: %s",
                    attempt,
                    _MAX_ATTEMPTS,
                    exc,
                )
                if attempt < _MAX_ATTEMPTS:
                    await asyncio.sleep(_BACKOFF_SECONDS[attempt - 1])
            except httpx.NetworkError as exc:
                last_exc = exc
                logger.warning(
                    "Moodle WS network error on attempt %d/%d: %s",
                    attempt,
                    _MAX_ATTEMPTS,
                    exc,
                )
                if attempt < _MAX_ATTEMPTS:
                    await asyncio.sleep(_BACKOFF_SECONDS[attempt - 1])

        raise MoodleIntegrationError(
            f"Moodle WS unavailable after {_MAX_ATTEMPTS} attempts: {last_exc}"
        ) from last_exc


# ---------------------------------------------------------------------------
# Response parsers
# ---------------------------------------------------------------------------

def _parse_enrolled_users(raw: dict | list) -> list[EntradaCruda]:
    """Parse Moodle's core_enrol_get_enrolled_users response.

    Expected format: list of user objects with at minimum:
      { "firstname": str, "lastname": str, "email": str, ... }

    Unknown fields are silently ignored.
    Rows missing required fields are skipped (logged as warnings, no PII).
    """
    if not isinstance(raw, list):
        raise MoodleIntegrationError(
            "Unexpected Moodle response format for enrolled users"
        )

    entradas: list[EntradaCruda] = []
    for idx, user in enumerate(raw):
        try:
            nombre = str(user.get("firstname", "")).strip()
            apellidos = str(user.get("lastname", "")).strip()
            email = str(user.get("email", "")).strip().lower()

            if not nombre or not apellidos or not email:
                logger.warning("Moodle enrolled user at index %d missing required fields", idx)
                continue

            entradas.append(
                EntradaCruda(
                    nombre=nombre,
                    apellidos=apellidos,
                    email=email,
                    comision=user.get("department") or None,
                    regional=user.get("institution") or None,
                )
            )
        except Exception:
            logger.warning("Failed to parse Moodle enrolled user at index %d", idx)
            continue

    return entradas
