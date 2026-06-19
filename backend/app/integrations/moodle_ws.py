"""Moodle Web Services client for activia-trace integration.

Provides access to Moodle WS functions for syncing users, grades, and activities.
Per-tenant configuration via MOODLE_WS_URL and MOODLE_WS_TOKEN.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MoodleConnectionError(Exception):
    """Raised when connection to Moodle fails after retries."""
    def __init__(self, message: str, status_code: int = 502):
        self.status_code = status_code
        super().__init__(message)


class MoodleWSClient:
    """HTTP client for Moodle Web Services REST API."""

    BASE_FUNCTIONS = {
        "get_enrolled_users": "core_enrol_get_enrolled_users",
        "get_users": "core_user_get_users",
        "get_grades": "core_grades_get_grades",
        "get_grade_items": "gradereport_user_get_grade_items",
        "get_courses": "core_course_get_courses",
    }

    def __init__(
        self,
        ws_url: str,
        ws_token: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ):
        """
        Args:
            ws_url: Base URL of Moodle WS endpoint (e.g., https://moodle.example.com/webservice/rest/server.php)
            ws_token: Moodle Web Services token
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay for exponential backoff
        """
        self.ws_url = ws_url.rstrip("/")
        self.ws_token = ws_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def _call(self, function: str, params: dict[str, Any] | None = None) -> Any:
        """Make a Moodle WS REST API call with retry logic."""
        if params is None:
            params = {}

        params["wstoken"] = self.ws_token
        params["wsfunction"] = function
        params["moodlewsrestformat"] = "json"

        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(self.ws_url, data=params)

                    if response.status_code == 200:
                        data = response.json()
                        # Moodle returns error in JSON body for some failures
                        if isinstance(data, dict) and "exception" in data:
                            raise MoodleConnectionError(
                                f"Moodle WS error: {data.get('message', 'Unknown Moodle error')}",
                                status_code=502,
                            )
                        return data
                    else:
                        raise MoodleConnectionError(
                            f"Moodle HTTP {response.status_code}: {response.text[:200]}",
                            status_code=502,
                        )

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = MoodleConnectionError(
                    f"Connection to Moodle failed (attempt {attempt}/{self.max_retries}): {str(e)}",
                    status_code=502,
                )
                logger.warning(str(last_error))
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
                    continue
            except MoodleConnectionError:
                raise
            except Exception as e:
                last_error = MoodleConnectionError(
                    f"Unexpected Moodle error (attempt {attempt}/{self.max_retries}): {str(e)}",
                    status_code=502,
                )
                logger.warning(str(last_error))
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
                    continue

        raise last_error or MoodleConnectionError("All Moodle retry attempts failed", status_code=502)

    async def get_enrolled_users(self, course_id: int) -> list[dict[str, Any]]:
        """Fetch enrolled users for a Moodle course.

        Calls core_enrol_get_enrolled_users.
        Returns list of user dicts with fields: id, username, firstname, lastname, email, etc.
        """
        result = await self._call("core_enrol_get_enrolled_users", {"courseid": course_id})
        if not isinstance(result, list):
            return []
        return result

    async def get_courses(self) -> list[dict[str, Any]]:
        """Fetch all courses from Moodle."""
        result = await self._call("core_course_get_courses", {})
        if not isinstance(result, list):
            return []
        return result

    async def get_users_by_field(self, field: str = "email", values: list[str] | None = None) -> list[dict[str, Any]]:
        """Fetch users by field value. Calls core_user_get_users_by_field."""
        if values is None:
            return []
        result = await self._call("core_user_get_users_by_field", {
            "field": field,
            "values": values,
        })
        if not isinstance(result, list):
            return []
        return result
