"""FastAPI application bootstrap for activia-trace."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.asignaciones import router as asignaciones_router
from app.api.v1.routers.carreras import router as carreras_router
from app.api.v1.routers.cohortes import router as cohortes_router
from app.api.v1.routers.equipos import router as equipos_router
from app.api.v1.routers.health import router as health_router
from app.api.v1.routers.impersonacion import router as impersonacion_router
from app.api.v1.routers.materias import router as materias_router
from app.api.v1.routers.padron import router as padron_router
from app.api.v1.routers.usuarios import router as usuarios_router
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
app.include_router(carreras_router, prefix="/api/v1")
app.include_router(cohortes_router, prefix="/api/v1")
app.include_router(health_router)
app.include_router(impersonacion_router)
app.include_router(usuarios_router, prefix="/api/v1")
app.include_router(asignaciones_router, prefix="/api/v1")
app.include_router(equipos_router, prefix="/api/v1")
app.include_router(materias_router, prefix="/api/v1")
app.include_router(padron_router, prefix="/api/v1")
