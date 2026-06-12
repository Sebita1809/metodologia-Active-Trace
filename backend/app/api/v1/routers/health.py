"""GET /health endpoint — liveness + database readiness."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Return application and database health status.

    Always returns 200. If the database is unreachable the endpoint
    reports ``database: down`` without crashing the process.
    """
    db_status = "up"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("Health-check DB ping failed", extra={"error": str(exc)})
        db_status = "down"

    return {"status": "ok", "database": db_status}
