"""
app/services/umbral_materia_service.py — UmbralMateriaService.

Business logic for managing per-asignacion approval thresholds:
  - upsert: create or update UmbralMateria for an asignacion
  - get: return the threshold (with defaults if not configured)

Tenant isolation: all repo calls scoped to self._tenant_id (from JWT).

Implemented: C-10 (calificaciones-y-umbral)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.umbral_materia_repository import UmbralMateriaRepository
from app.schemas.umbral_materia import UmbralMateriaRead
from app.services.calificacion_service import (
    DEFAULT_UMBRAL_PCT,
    DEFAULT_VALORES_APROBATORIOS,
)

# Sentinel UUID used for the "default" response when no record exists
_DEFAULT_UUID = uuid.UUID("00000000-0000-0000-0000-000000000000")


class UmbralMateriaService:
    """Service for managing per-asignacion approval thresholds.

    All operations scoped to *tenant_id* from JWT — never from request body.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._repo = UmbralMateriaRepository(session=session, tenant_id=tenant_id)

    async def upsert(
        self,
        asignacion_id: uuid.UUID,
        materia_id: uuid.UUID,
        umbral_pct: int,
        valores_aprobatorios: list[str],
    ) -> UmbralMateriaRead:
        """Create or update the UmbralMateria for the given asignacion.

        Returns the persisted record as a read schema.
        """
        obj = await self._repo.upsert(
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            umbral_pct=umbral_pct,
            valores_aprobatorios=valores_aprobatorios,
        )
        return UmbralMateriaRead.model_validate(obj)

    async def get(self, asignacion_id: uuid.UUID) -> UmbralMateriaRead:
        """Return the UmbralMateria for the given asignacion.

        If no record exists, returns a virtual default record with:
          - umbral_pct = 60
          - valores_aprobatorios = ["Satisfactorio", "Supera lo esperado"]

        The default record has id=_DEFAULT_UUID and materia_id=_DEFAULT_UUID
        to indicate it is not persisted.
        """
        obj = await self._repo.get_by_asignacion(asignacion_id)

        if obj is not None:
            return UmbralMateriaRead.model_validate(obj)

        # Return virtual defaults — not persisted
        return UmbralMateriaRead(
            id=_DEFAULT_UUID,
            asignacion_id=asignacion_id,
            materia_id=_DEFAULT_UUID,
            umbral_pct=DEFAULT_UMBRAL_PCT,
            valores_aprobatorios=list(DEFAULT_VALORES_APROBATORIOS),
        )
