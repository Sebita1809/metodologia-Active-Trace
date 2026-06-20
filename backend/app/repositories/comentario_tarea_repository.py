"""
app/repositories/comentario_tarea_repository.py — ComentarioTareaRepository.

Extends BaseRepository[ComentarioTarea] with:
  - listar_por_tarea: ordered chronologically (creado_at asc), tenant-scoped,
    excludes soft-deleted.

Tenant isolation is inherited from BaseRepository (mandatory).
Comments are append-only — no update or delete exposed (D7).

Implemented: C-16 (tareas-internas)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comentario_tarea import ComentarioTarea
from app.repositories.base import BaseRepository


class ComentarioTareaRepository(BaseRepository[ComentarioTarea]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=ComentarioTarea, session=session, tenant_id=tenant_id)

    async def listar_por_tarea(
        self,
        tarea_id: uuid.UUID,
    ) -> list[ComentarioTarea]:
        """Return non-deleted comments for *tarea_id*, ordered by creado_at asc.

        Tenant isolation enforced via _base_query() — comments from another
        tenant's tarea will never appear here even if tarea_id is known.
        """
        stmt = (
            self._base_query()
            .where(ComentarioTarea.tarea_id == tarea_id)
            .order_by(ComentarioTarea.creado_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
