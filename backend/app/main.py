"""FastAPI application bootstrap for activia-trace."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.health import router as health_router
from app.core.logging import setup_logging
from app.core.observability import setup_observability

# ── Initialise structured logging ────────────────────────────
setup_logging()
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> None:  # noqa: ARG001
    """Startup and shutdown lifecycle."""
    logger.info("activia-trace starting")
    setup_observability(instrument_fastapi_app=app)
    yield
    logger.info("activia-trace shutting down")


# ── Application factory ──────────────────────────────────────
app = FastAPI(
    title="activia-trace",
    version="0.1.0",
    description="Plataforma de gestión académica y trazabilidad multi-tenant",
    lifespan=lifespan,
)

# ── Routers ──────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api/v1")
app.include_router(health_router)
