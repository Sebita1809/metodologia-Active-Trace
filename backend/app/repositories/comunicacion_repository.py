"""
app/repositories/comunicacion_repository.py — ComunicacionRepository.

Extends BaseRepository[Comunicacion] with bulk-write, queue-list,
conditional-transition, and approval operations.

Tenant isolation is MANDATORY via _base_query() — never bypassed.

The repository is AGNOSTIC of cryptography — it stores and returns
the `destinatario` field as-is (ciphertext). Encryption/decryption
is the responsibility of the service layer.

Key methods:
  create_many           — persist N Comunicacion rows atomically
  list_cola             — list by optional lote_id / estado filters
  aplicar_transicion_condicional — conditional UPDATE (race-safe)
  marcar_aprobado       — set aprobado_at / aprobado_por on Pendiente rows

Implemented: C-12 (comunicaciones-cola-worker)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comunicacion import Comunicacion, EstadoComunicacion
from app.repositories.base import BaseRepository


class ComunicacionRepository(BaseRepository[Comunicacion]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=Comunicacion, session=session, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Task 4.1 — create_many
    # ------------------------------------------------------------------

    async def create_many(self, comunicaciones: list[Comunicacion]) -> list[Comunicacion]:
        """Persist multiple Comunicacion rows in a single flush.

        All objects MUST have tenant_id == self._tenant_id (enforced via assertion).
        Returns the persisted objects with server-generated fields populated.
        """
        for com in comunicaciones:
            if com.tenant_id != self._tenant_id:
                raise ValueError(
                    f"Comunicacion tenant_id mismatch: {com.tenant_id} != {self._tenant_id}"
                )
            self._session.add(com)

        await self._session.flush()

        for com in comunicaciones:
            await self._session.refresh(com)

        return comunicaciones

    # ------------------------------------------------------------------
    # Task 4.2 — list_cola
    # ------------------------------------------------------------------

    async def list_cola(
        self,
        *,
        lote_id: uuid.UUID | None = None,
        estado: EstadoComunicacion | str | None = None,
        include_deleted: bool = False,
    ) -> list[Comunicacion]:
        """Return Comunicacion rows for this tenant with optional filters.

        Parameters:
            lote_id         — optional: filter by lote_id
            estado          — optional: filter by estado value
            include_deleted — if True, includes soft-deleted rows (admin use)

        Uses _base_query() for tenant isolation and soft-delete filter.
        """
        stmt = (
            self._base_query_including_deleted()
            if include_deleted
            else self._base_query()
        )

        if lote_id is not None:
            stmt = stmt.where(Comunicacion.lote_id == lote_id)

        if estado is not None:
            estado_val = estado.value if isinstance(estado, EstadoComunicacion) else estado
            stmt = stmt.where(Comunicacion.estado == estado_val)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Task 4.3 — aplicar_transicion_condicional (race-safe)
    # ------------------------------------------------------------------

    async def aplicar_transicion_condicional(
        self,
        comunicacion_id: uuid.UUID,
        *,
        desde: EstadoComunicacion | str,
        hacia: EstadoComunicacion | str,
        extra_values: dict | None = None,
    ) -> int:
        """Conditionally UPDATE estado WHERE estado == desde (race-safe).

        This is the ONLY correct way to transition a Comunicacion state in
        concurrent scenarios (worker vs. cancellation race, D-04 / risks).

        The UPDATE is applied only if the current state matches `desde`. If
        the row was already cancelled/transitioned, 0 rows are affected and
        the caller knows to skip this message.

        Parameters:
            comunicacion_id — the Comunicacion to update
            desde           — expected current state (UPDATE guard)
            hacia           — target state
            extra_values    — additional columns to set (e.g. enviado_at)

        Returns:
            Number of rows actually updated (0 or 1).
        """
        desde_val = desde.value if isinstance(desde, EstadoComunicacion) else desde
        hacia_val = hacia.value if isinstance(hacia, EstadoComunicacion) else hacia

        values: dict = {"estado": hacia_val}
        if extra_values:
            values.update(extra_values)

        stmt = (
            update(Comunicacion)
            .where(Comunicacion.id == comunicacion_id)
            .where(Comunicacion.tenant_id == self._tenant_id)
            .where(Comunicacion.estado == desde_val)
            .where(Comunicacion.deleted_at.is_(None))
            .values(**values)
        )
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Task 4.4 — marcar_aprobado
    # ------------------------------------------------------------------

    async def marcar_aprobado_por_lote(
        self,
        lote_id: uuid.UUID,
        *,
        aprobado_por: uuid.UUID,
    ) -> int:
        """Set aprobado_at and aprobado_por on all Pendiente rows of a lote.

        Only rows in estado == 'Pendiente' are updated (non-Pendiente rows
        are left untouched, since approving an already-sent message makes no
        sense).

        Returns the number of rows updated.
        """
        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(Comunicacion)
            .where(Comunicacion.tenant_id == self._tenant_id)
            .where(Comunicacion.lote_id == lote_id)
            .where(Comunicacion.estado == EstadoComunicacion.Pendiente.value)
            .where(Comunicacion.deleted_at.is_(None))
            .values(aprobado_at=now, aprobado_por=aprobado_por)
        )
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def marcar_aprobado_por_id(
        self,
        comunicacion_id: uuid.UUID,
        *,
        aprobado_por: uuid.UUID,
    ) -> int:
        """Set aprobado_at and aprobado_por on a single Pendiente Comunicacion.

        Only updates if estado == 'Pendiente'.
        Returns 1 if updated, 0 if not found or not Pendiente.
        """
        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(Comunicacion)
            .where(Comunicacion.id == comunicacion_id)
            .where(Comunicacion.tenant_id == self._tenant_id)
            .where(Comunicacion.estado == EstadoComunicacion.Pendiente.value)
            .where(Comunicacion.deleted_at.is_(None))
            .values(aprobado_at=now, aprobado_por=aprobado_por)
        )
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def list_despachables(
        self,
        *,
        requiere_aprobacion: bool,
    ) -> list[Comunicacion]:
        """Return Pendiente Comunicacion rows that the worker can dispatch.

        If requiere_aprobacion=True, only rows with aprobado_at IS NOT NULL
        are returned (fail-safe for tenants without explicit config — D-02).
        If requiere_aprobacion=False, all Pendiente rows are returned.
        """
        stmt = (
            self._base_query()
            .where(Comunicacion.estado == EstadoComunicacion.Pendiente.value)
        )
        if requiere_aprobacion:
            stmt = stmt.where(Comunicacion.aprobado_at.isnot(None))

        result = await self._session.execute(stmt)
        return list(result.scalars().all())
