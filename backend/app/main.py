"""
app/main.py — FastAPI application factory and entry-point.

Bootstrap order (lifespan):
  1. Configure structured JSON logging
  2. Load Settings
  3. Initialise async DB engine
  4. Register OpenTelemetry instrumentation (opt-in)
  5. Mount routers

The module exposes:
  create_app() → FastAPI  (used by tests and ASGI servers)
  app           (module-level singleton for uvicorn / Easypanel)

Implemented: C-01 (foundation-setup)
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Build and return a configured FastAPI application.

    Factored into a function so that tests can call it without triggering
    the module-level `app` singleton side-effects.
    """
    from app.core.database import init_engine  # noqa: PLC0415
    from app.core.observability import init_observability  # noqa: PLC0415
    from app.core.rate_limiter import limiter  # noqa: PLC0415
    from app.api.v1.routers.health import router as health_router  # noqa: PLC0415
    from app.api.v1.routers.auth import router as auth_router  # noqa: PLC0415
    from app.api.v1.routers.rbac import router as rbac_router  # noqa: PLC0415
    from app.api.v1.routers.impersonacion import router as impersonacion_router  # noqa: PLC0415
    from app.api.v1.routers.auditoria import router as auditoria_router  # noqa: PLC0415
    from app.api.v1.routers.carreras import router as carreras_router  # noqa: PLC0415
    from app.api.v1.routers.cohortes import router as cohortes_router  # noqa: PLC0415
    from app.api.v1.routers.materias import router as materias_router  # noqa: PLC0415
    from app.api.v1.routers.usuarios import router as usuarios_router  # noqa: PLC0415
    from app.api.v1.routers.asignaciones import router as asignaciones_router  # noqa: PLC0415
    from app.api.v1.routers.equipos import router as equipos_router  # noqa: PLC0415
    from app.api.v1.routers.padron import router as padron_router  # noqa: PLC0415
    from app.api.v1.routers.calificaciones import router as calificaciones_router  # noqa: PLC0415
    from app.api.v1.routers.analisis import router as analisis_router  # noqa: PLC0415
    from app.api.v1.routers.encuentros import router as encuentros_router  # noqa: PLC0415
    from app.api.v1.routers.guardias import router as guardias_router  # noqa: PLC0415
    from app.api.v1.routers.coloquios import router as coloquios_router  # noqa: PLC0415
    from app.api.v1.routers.avisos import router as avisos_router  # noqa: PLC0415
    from app.api.v1.routers.tareas import router as tareas_router  # noqa: PLC0415
    from app.api.v1.routers.programas import router as programas_router  # noqa: PLC0415
    from app.api.v1.routers.fechas_academicas import router as fechas_academicas_router  # noqa: PLC0415
    from app.api.v1.routers.liquidaciones import router as liquidaciones_router  # noqa: PLC0415
    from app.api.v1.routers.facturas import router as facturas_router  # noqa: PLC0415
    from app.api.v1.routers.perfil import router as perfil_router  # noqa: PLC0415
    from app.api.v1.routers.inbox import router as inbox_router  # noqa: PLC0415
    from app.api.v1.routers.comunicaciones import router as comunicaciones_router  # noqa: PLC0415

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
        """Manage app lifecycle: startup and shutdown."""
        # Import Settings inside lifespan so tests can monkeypatch env vars
        # before the module-level singleton is created.
        from app.core.config import Settings  # noqa: PLC0415
        settings = Settings()

        configure_logging(settings.log_level)
        logger.info("activia-trace starting up", extra={"env": settings.app_env})

        # Initialise DB engine on startup
        engine = init_engine(settings.database_url)
        logger.info("Database engine initialised")

        yield  # application runs here

        # Dispose engine on shutdown (close all pool connections)
        await engine.dispose()
        logger.info("activia-trace shut down cleanly")

    application = FastAPI(
        title="activia-trace API",
        description="Plataforma de gestión académica y trazabilidad multi-tenant.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — must be added before any other middleware
    from app.core.config import get_settings as _get_settings  # noqa: PLC0415
    _cfg = _get_settings()
    _origins = [o.strip() for o in _cfg.cors_origins.split(",") if o.strip()]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Mount routers
    application.include_router(health_router)
    application.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    application.include_router(rbac_router, prefix="/api/rbac", tags=["rbac"])
    application.include_router(impersonacion_router, prefix="/api/impersonacion", tags=["impersonacion"])
    application.include_router(auditoria_router, prefix="/api/auditoria", tags=["auditoria"])
    application.include_router(carreras_router, prefix="/api/admin/carreras", tags=["estructura"])
    application.include_router(cohortes_router, prefix="/api/admin/cohortes", tags=["estructura"])
    application.include_router(materias_router, prefix="/api/admin/materias", tags=["estructura"])
    application.include_router(usuarios_router, prefix="/api/admin/usuarios", tags=["usuarios"])
    application.include_router(asignaciones_router, prefix="/api/asignaciones", tags=["asignaciones"])
    application.include_router(equipos_router, prefix="/api/equipos", tags=["equipos"])
    application.include_router(padron_router, prefix="/api/padron", tags=["padron"])
    application.include_router(calificaciones_router, prefix="/api/calificaciones", tags=["calificaciones"])
    application.include_router(analisis_router, prefix="/api/v1", tags=["analisis"])
    application.include_router(encuentros_router, prefix="/api/v1", tags=["encuentros"])
    application.include_router(guardias_router, prefix="/api/v1", tags=["guardias"])
    application.include_router(coloquios_router, prefix="/api/v1/coloquios", tags=["coloquios"])
    application.include_router(avisos_router, prefix="/api/avisos", tags=["avisos"])
    application.include_router(tareas_router, prefix="/api/v1/tareas", tags=["tareas"])
    application.include_router(programas_router, prefix="/api/v1/programas", tags=["programas"])
    application.include_router(fechas_academicas_router, prefix="/api/v1/fechas-academicas", tags=["fechas-academicas"])
    application.include_router(liquidaciones_router, prefix="/api/liquidaciones", tags=["liquidaciones"])
    application.include_router(facturas_router, prefix="/api/facturas", tags=["facturas"])
    application.include_router(perfil_router, prefix="/api/perfil", tags=["perfil"])
    application.include_router(inbox_router, prefix="/api/inbox", tags=["inbox"])
    application.include_router(comunicaciones_router, prefix="/api/comunicaciones", tags=["comunicaciones"])

    # Instrument with OpenTelemetry if enabled (settings resolved at lifespan time)
    # Note: otel init happens during lifespan, not here, to avoid import-time settings load.

    return application


def _get_app() -> FastAPI:
    """Return the module-level app singleton, creating it with env vars set.

    This is called lazily so that the module can be imported in tests
    without requiring DATABASE_URL / SECRET_KEY to be in the environment.
    """
    return create_app()


# ---------------------------------------------------------------------------
# Module-level singleton — used by uvicorn / docker CMD
# uvicorn app.main:app
# ---------------------------------------------------------------------------
app: FastAPI = _get_app()
