"""Test that the FastAPI app starts without errors."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_app_lifespan(async_client: AsyncClient) -> None:
    """WHEN the app starts THEN it responds without crashing."""
    resp = await async_client.get("/health")
    assert resp.status_code == 200
