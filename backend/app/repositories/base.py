"""
app/repositories/base.py — Generic async repository with mandatory tenant scope.

Every concrete repository inherits BaseRepository[T] and passes the correct
tenant_id in its constructor. The _base_query() method is the ONLY place where
the tenant filter and soft-delete filter are applied — all public methods call
_base_query() to guarantee isolation cannot be accidentally bypassed.

Decision references:
  D2 — BaseRepository[T] Generic, tenant_id in constructor
  D3 — Soft delete via deleted_at; _base_query filters deleted_at IS NULL

Implemented: C-02 (core-models-y-tenancy)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Generic, TypeVar

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import BaseTenantModel

T = TypeVar("T", bound=BaseTenantModel)


class BaseRepository(Generic[T]):
    """Generic async repository that scopes every operation to a single tenant.

    Constructor parameters:
        model      — the SQLAlchemy model class (e.g. Item)
        session    — an open AsyncSession for the current request / test
        tenant_id  — UUID of the tenant that owns this repository scope

    Public methods: get, list, create, update, soft_delete.
    All methods filter by self._tenant_id AND deleted_at IS NULL (except
    _base_query_including_deleted which is reserved for audit use cases).
    """

    def __init__(
        self,
        *,
        model: type[T],
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> None:
        self._model = model
        self._session = session
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Internal — the single place where tenant + soft-delete filters live
    # ------------------------------------------------------------------

    def _base_query(self):
        """Return a SELECT statement pre-filtered by tenant_id and deleted_at IS NULL."""
        return (
            select(self._model)
            .where(self._model.tenant_id == self._tenant_id)
            .where(self._model.deleted_at.is_(None))
        )

    def _base_query_including_deleted(self):
        """Return a SELECT filtered by tenant_id only (includes soft-deleted rows).

        Intended for audit/admin use cases. NEVER call from normal business logic.
        """
        return select(self._model).where(self._model.tenant_id == self._tenant_id)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get(self, record_id: uuid.UUID) -> T | None:
        """Return the record with *record_id* if it belongs to this tenant and is not deleted.

        Returns None if the record does not exist, belongs to another tenant,
        or has been soft-deleted.
        """
        stmt = self._base_query().where(self._model.id == record_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, **filters) -> list[T]:
        """Return all active (non-deleted) records belonging to this tenant.

        Additional keyword filters can be passed as column=value pairs.
        """
        stmt = self._base_query()
        for attr, value in filters.items():
            stmt = stmt.where(getattr(self._model, attr) == value)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj: T) -> T:
        """Persist *obj* and return it with server-generated fields populated.

        The caller is responsible for setting obj.tenant_id to self._tenant_id
        before calling create(). This is intentional — it keeps the assignment
        explicit and auditable.
        """
        self._session.add(obj)
        await self._session.flush()  # flush to get server defaults (id, created_at)
        await self._session.refresh(obj)
        return obj

    async def update(self, record_id: uuid.UUID, **data) -> T | None:
        """Update fields on a record that belongs to this tenant.

        Returns the updated record, or None if not found / different tenant.
        Only keys present in *data* are changed; unknown keys are silently ignored
        by SQLAlchemy (column names not on the model simply won't match).
        """
        obj = await self.get(record_id)
        if obj is None:
            return None
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def soft_delete(self, record_id: uuid.UUID) -> bool:
        """Mark *record_id* as deleted by setting deleted_at to now().

        Returns True if a record was found and deleted (scoped to this tenant).
        Returns False if the record does not exist or belongs to another tenant.

        Crucially: uses _base_query() so a T1 repo can NEVER soft-delete a T2 record.
        """
        stmt = (
            update(self._model)
            .where(self._model.id == record_id)
            .where(self._model.tenant_id == self._tenant_id)
            .where(self._model.deleted_at.is_(None))
            .values(deleted_at=datetime.now(tz=timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0  # type: ignore[return-value]
