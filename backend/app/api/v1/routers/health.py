"""
api/v1/routers/health.py — Health-check endpoint.

GET /health returns:
  200 OK  {"status": "ok", "database": "up"}   — when DB is reachable
  200 OK  {"status": "ok", "database": "down"} — when DB is unreachable

The endpoint NEVER crashes due to a DB failure: liveness is always
reported as "ok" as long as the process is running.

Implemented: C-01 (foundation-setup)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Response schema for GET /health."""

    model_config = ConfigDict(extra="forbid")

    status: str
    database: str


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Report application liveness and database readiness.

    Always responds 200 OK.  The `database` field reflects whether
    the DB connection is healthy ("up") or not ("down").
    """
    db_status = "down"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "up"
    except Exception:
        logger.warning("Health check: database unreachable")

    return HealthResponse(status="ok", database=db_status)
