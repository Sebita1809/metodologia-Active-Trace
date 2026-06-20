"""
core/database.py — SQLAlchemy 2.0 async engine, session factory and declarative Base.

Pattern: one async engine per process, session-per-request via get_db() dependency.
The engine is created from DATABASE_URL in Settings; tests use TEST_DATABASE_URL.

Implemented: C-01 (foundation-setup)
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models.

    Models added in C-02 onwards will inherit from this base.
    multi-tenancy mixin (tenant_id) added in C-02 via TenantMixin.
    """


def build_engine(database_url: str) -> AsyncEngine:
    """Create and return a new async SQLAlchemy engine for *database_url*.

    Factored out of the module-level singleton so that tests can build
    isolated engines against the test database without importing settings.
    """
    return create_async_engine(
        database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,  # detect stale connections before use
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return an async_sessionmaker bound to *engine*.

    expire_on_commit=False: avoid lazy-load errors after commit when
    accessing model attributes outside the session scope.
    """
    return async_sessionmaker(engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Module-level singletons (used by the running application)
# Replaced during lifespan in main.py; tests build their own instances.
# ---------------------------------------------------------------------------
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str) -> AsyncEngine:
    """Initialize the module-level engine. Called from app lifespan."""
    global _engine, _session_factory  # noqa: PLW0603
    _engine = build_engine(database_url)
    _session_factory = build_session_factory(_engine)
    return _engine


def get_engine() -> AsyncEngine:
    """Return the current module-level engine (must call init_engine first)."""
    if _engine is None:
        raise RuntimeError("Engine not initialized — call init_engine() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the current session factory (must call init_engine first)."""
    if _session_factory is None:
        raise RuntimeError("Session factory not initialized — call init_engine() first.")
    return _session_factory
