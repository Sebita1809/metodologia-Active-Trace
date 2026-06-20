"""
app/repositories/asignacion_repository.py — AsignacionRepository.

Extends BaseRepository[Asignacion] with filtered list support.
All filters are optional — None means "no filter on this field".
Tenant isolation is inherited from BaseRepository (mandatory).

Implemented: C-07 (usuarios-y-asignaciones)
Updated:     C-08 (equipos-docentes) — bulk operations + export
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import Row, func, outerjoin, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asignacion import Asignacion
from app.models.carrera import Carrera
from app.models.cohorte import Cohorte
from app.models.materia import Materia
from app.models.usuario import Usuario
from app.repositories.base import BaseRepository


class AsignacionRepository(BaseRepository[Asignacion]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=Asignacion, session=session, tenant_id=tenant_id)

    async def list_with_filters(
        self,
        *,
        usuario_id: uuid.UUID | None = None,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
        rol: str | None = None,
        responsable_id: uuid.UUID | None = None,
    ) -> list[Asignacion]:
        """Return asignaciones matching all provided (non-None) filters.

        Starts from _base_query() to guarantee tenant isolation and soft-delete filter.
        All parameters are optional; None means "no constraint on this field".
        """
        stmt = self._base_query()

        if usuario_id is not None:
            stmt = stmt.where(Asignacion.usuario_id == usuario_id)
        if materia_id is not None:
            stmt = stmt.where(Asignacion.materia_id == materia_id)
        if carrera_id is not None:
            stmt = stmt.where(Asignacion.carrera_id == carrera_id)
        if cohorte_id is not None:
            stmt = stmt.where(Asignacion.cohorte_id == cohorte_id)
        if rol is not None:
            stmt = stmt.where(Asignacion.rol == rol)
        if responsable_id is not None:
            stmt = stmt.where(Asignacion.responsable_id == responsable_id)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # C-08: team operations
    # ------------------------------------------------------------------

    async def list_by_usuario(
        self,
        usuario_id: uuid.UUID,
        *,
        estado_vigencia: str | None = None,
        materia_id: uuid.UUID | None = None,
        rol: str | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
    ) -> list[Asignacion]:
        """Return asignaciones for *usuario_id* with optional filters.

        estado_vigencia filtering uses date comparison (not a stored column):
          "Vigente": desde <= today AND (hasta IS NULL OR hasta >= today)
          "Vencida": hasta IS NOT NULL AND hasta < today

        Uses _base_query() for tenant isolation and soft-delete filter.
        """
        stmt = self._base_query().where(Asignacion.usuario_id == usuario_id)

        hoy = date.today()
        if estado_vigencia == "Vigente":
            stmt = stmt.where(Asignacion.desde <= hoy).where(
                (Asignacion.hasta.is_(None)) | (Asignacion.hasta >= hoy)
            )
        elif estado_vigencia == "Vencida":
            stmt = stmt.where(
                Asignacion.hasta.is_not(None)
            ).where(Asignacion.hasta < hoy)

        if materia_id is not None:
            stmt = stmt.where(Asignacion.materia_id == materia_id)
        if rol is not None:
            stmt = stmt.where(Asignacion.rol == rol)
        if carrera_id is not None:
            stmt = stmt.where(Asignacion.carrera_id == carrera_id)
        if cohorte_id is not None:
            stmt = stmt.where(Asignacion.cohorte_id == cohorte_id)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create(self, asignaciones: list[Asignacion]) -> list[Asignacion]:
        """Insert multiple Asignacion objects in a single flush.

        Each object must have tenant_id pre-set by the caller.
        Rollback on failure is handled by the caller / session context.
        """
        for obj in asignaciones:
            self._session.add(obj)
        await self._session.flush()
        for obj in asignaciones:
            await self._session.refresh(obj)
        return asignaciones

    async def clone_from(
        self,
        origen_materia_id: uuid.UUID,
        origen_cohorte_id: uuid.UUID | None = None,
    ) -> list[Asignacion]:
        """Return vigentes from the origin context (read-only, not cloned yet).

        Uses the same vigencia logic as list_by_usuario (Vigente state).
        Returns ORM objects still attached to the session; caller creates
        new Asignacion objects for the destination context.
        """
        hoy = date.today()
        stmt = (
            self._base_query()
            .where(Asignacion.materia_id == origen_materia_id)
            .where(Asignacion.desde <= hoy)
            .where(
                (Asignacion.hasta.is_(None)) | (Asignacion.hasta >= hoy)
            )
        )
        if origen_cohorte_id is not None:
            stmt = stmt.where(Asignacion.cohorte_id == origen_cohorte_id)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_update_vigencia(
        self,
        materia_id: uuid.UUID,
        desde: date,
        hasta: date | None = None,
        *,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
    ) -> int:
        """UPDATE desde/hasta for all tenant asignaciones matching the context.

        Returns the number of rows affected.
        hasta=None sets open-ended validity (UPDATE hasta = NULL).
        """
        stmt = (
            update(Asignacion)
            .where(Asignacion.tenant_id == self._tenant_id)
            .where(Asignacion.deleted_at.is_(None))
            .where(Asignacion.materia_id == materia_id)
            .values(desde=desde, hasta=hasta)
        )
        if carrera_id is not None:
            stmt = stmt.where(Asignacion.carrera_id == carrera_id)
        if cohorte_id is not None:
            stmt = stmt.where(Asignacion.cohorte_id == cohorte_id)

        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def list_for_export(
        self,
        materia_id: uuid.UUID | None = None,
        carrera_id: uuid.UUID | None = None,
        cohorte_id: uuid.UUID | None = None,
    ) -> list[Row[Any]]:
        """Return rows with joined fields for CSV export.

        Joins usuarios (inner), materias/carreras/cohortes (outer).
        Filters by tenant_id + deleted_at IS NULL + optional context filters.
        Returns SQLAlchemy Row objects (named tuples).
        """
        stmt = (
            select(
                Asignacion.id,
                Asignacion.usuario_id,
                Usuario.nombre.label("nombre"),
                Usuario.apellidos.label("apellidos"),
                Asignacion.rol,
                Materia.nombre.label("materia_nombre"),
                Carrera.nombre.label("carrera_nombre"),
                Cohorte.nombre.label("cohorte_nombre"),
                Asignacion.comisiones,
                Asignacion.desde,
                Asignacion.hasta,
            )
            .join(Usuario, Asignacion.usuario_id == Usuario.id)
            .outerjoin(Materia, Asignacion.materia_id == Materia.id)
            .outerjoin(Carrera, Asignacion.carrera_id == Carrera.id)
            .outerjoin(Cohorte, Asignacion.cohorte_id == Cohorte.id)
            .where(Asignacion.tenant_id == self._tenant_id)
            .where(Asignacion.deleted_at.is_(None))
        )

        if materia_id is not None:
            stmt = stmt.where(Asignacion.materia_id == materia_id)
        if carrera_id is not None:
            stmt = stmt.where(Asignacion.carrera_id == carrera_id)
        if cohorte_id is not None:
            stmt = stmt.where(Asignacion.cohorte_id == cohorte_id)

        result = await self._session.execute(stmt)
        return list(result.all())
