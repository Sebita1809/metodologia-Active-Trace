"""SQLAlchemy 2.0 async engine, session factory, and declarative Base.

Lazy initialisation: engine and session factory are created on first
call to ``get_engine()`` / ``get_session_factory()``.  This avoids
requiring ``Settings`` at import time (needed for test isolation).
"""

from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


@lru_cache
def get_engine() -> Any:
    """Create (or return cached) async engine."""
    settings = get_settings()
    return create_async_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        echo=False,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create (or return cached) async session factory bound to the engine."""
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
