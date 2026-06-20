"""
app/services/tarea_service.py — TareaService (C-16).

Business logic for the internal task workflow (Épica 8, FL-05).

Rules enforced:
  - asignado_por ALWAYS from JWT (CurrentUser.user_id); never from request body (D3).
  - autor_id on comments ALWAYS from JWT; never from request body (D7).
  - tenant_id always from service constructor (JWT), never from body.
  - State machine transitions (D2):
      Pendiente  → {En progreso, Cancelada}
      En progreso → {Resuelta, Cancelada, Pendiente}
      Resuelta   → {En progreso}
      Cancelada  → {} (terminal)
  - Delegation validates that the target user belongs to the same tenant (D3).
  - "Mis tareas" = asignado_a filter on session user.
  - Admin list = all tenant tareas with optional filters and pagination (D6).

Governance: MEDIO — checkpoints at state transitions and delegation.

Implemented: C-16 (tareas-internas)
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.models.comentario_tarea import ComentarioTarea
from app.models.tarea import EstadoTarea, Tarea
from app.repositories.comentario_tarea_repository import ComentarioTareaRepository
from app.repositories.tarea_repository import TareaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.tareas import (
    ComentarioTareaCreate,
    ComentarioTareaResponse,
    TareaCreate,
    TareaDelegar,
    TareaFiltros,
    TareaResponse,
)

# ---------------------------------------------------------------------------
# State machine (D2) — explicit transition map
# ---------------------------------------------------------------------------

_TRANSICIONES_VALIDAS: dict[EstadoTarea, set[EstadoTarea]] = {
    EstadoTarea.Pendiente:   {EstadoTarea.EnProgreso, EstadoTarea.Cancelada},
    EstadoTarea.EnProgreso:  {EstadoTarea.Resuelta, EstadoTarea.Cancelada, EstadoTarea.Pendiente},
    EstadoTarea.Resuelta:    {EstadoTarea.EnProgreso},
    EstadoTarea.Cancelada:   set(),  # terminal
}


class TareaService:
    """Orchestrates internal task lifecycle for a single tenant.

    All operations scoped to *tenant_id* from JWT — never from request body.
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._repo = TareaRepository(session=session, tenant_id=tenant_id)
        self._comentario_repo = ComentarioTareaRepository(
            session=session, tenant_id=tenant_id
        )
        self._usuario_repo = UsuarioRepository(session=session, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_tarea_or_404(self, tarea_id: uuid.UUID) -> Tarea:
        """Return the tarea or raise 404 if not found in this tenant."""
        tarea = await self._repo.get_by_id(tarea_id)
        if tarea is None:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")
        return tarea

    def _to_response(self, tarea: Tarea) -> TareaResponse:
        """Build TareaResponse from ORM model."""
        return TareaResponse(
            id=tarea.id,
            tenant_id=tarea.tenant_id,
            materia_id=tarea.materia_id,
            asignado_a=tarea.asignado_a,
            asignado_por=tarea.asignado_por,
            estado=tarea.estado,
            descripcion=tarea.descripcion,
            contexto_id=tarea.contexto_id,
            created_at=tarea.created_at,
            updated_at=tarea.updated_at,
            deleted_at=tarea.deleted_at,
        )

    def _to_comentario_response(self, c: ComentarioTarea) -> ComentarioTareaResponse:
        """Build ComentarioTareaResponse from ORM model."""
        return ComentarioTareaResponse(
            id=c.id,
            tenant_id=c.tenant_id,
            tarea_id=c.tarea_id,
            autor_id=c.autor_id,
            texto=c.texto,
            creado_at=c.creado_at,
            created_at=c.created_at,
            updated_at=c.updated_at,
            deleted_at=c.deleted_at,
        )

    # ------------------------------------------------------------------
    # Task 5.2 — crear_tarea
    # ------------------------------------------------------------------

    async def crear_tarea(
        self,
        data: TareaCreate,
        current_user: CurrentUser,
    ) -> TareaResponse:
        """Create a new tarea.

        asignado_por = current_user.user_id (from JWT — never from body).
        estado initial = Pendiente.
        tenant_id = self._tenant_id (from constructor JWT — never from body).
        Auto-assignment (asignado_a == asignado_por) is explicitly allowed (D3).
        """
        tarea = Tarea(
            tenant_id=self._tenant_id,
            asignado_a=data.asignado_a,
            asignado_por=current_user.user_id,
            estado=EstadoTarea.Pendiente,
            descripcion=data.descripcion,
            materia_id=data.materia_id,
            contexto_id=data.contexto_id,
        )
        tarea = await self._repo.create(tarea)
        return self._to_response(tarea)

    # ------------------------------------------------------------------
    # Task 5.3 — cambiar_estado
    # ------------------------------------------------------------------

    async def cambiar_estado(
        self,
        tarea_id: uuid.UUID,
        nuevo_estado: EstadoTarea,
        current_user: CurrentUser,  # noqa: ARG002 — available for future audit
    ) -> TareaResponse:
        """Change the state of a tarea, enforcing the state machine (D2).

        Raises HTTPException(409) if the transition is invalid.
        Raises HTTPException(404) if the tarea is not found.
        """
        tarea = await self._get_tarea_or_404(tarea_id)

        estado_actual = EstadoTarea(tarea.estado)
        transiciones_permitidas = _TRANSICIONES_VALIDAS.get(estado_actual, set())

        if nuevo_estado not in transiciones_permitidas:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Transición inválida: {estado_actual.value!r} → {nuevo_estado.value!r}. "
                    f"Transiciones permitidas: "
                    f"{[t.value for t in transiciones_permitidas] or 'ninguna (estado terminal)'}."
                ),
            )

        updated = await self._repo.update(tarea_id, estado=nuevo_estado.value)
        if updated is None:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")
        return self._to_response(updated)

    # ------------------------------------------------------------------
    # Task 5.4 — delegar_tarea
    # ------------------------------------------------------------------

    async def delegar_tarea(
        self,
        tarea_id: uuid.UUID,
        data: TareaDelegar,
        current_user: CurrentUser,  # noqa: ARG002 — available for future audit
    ) -> TareaResponse:
        """Delegate tarea to a different user.

        asignado_por is preserved (original assigner never changes — D3).
        asignado_a is updated to nuevo_asignado_a.

        Validates that the target user belongs to the same tenant.
        If C-07 EquipoRepository is available, more granular team validation
        can be added; currently validates tenant membership only.
        """
        await self._get_tarea_or_404(tarea_id)

        # Validate target user exists in tenant
        nuevo_asignado = await self._usuario_repo.get(data.nuevo_asignado_a)
        if nuevo_asignado is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Usuario {data.nuevo_asignado_a} no encontrado en este tenant. "
                    "La delegación sólo puede hacerse a miembros del tenant."
                ),
            )

        updated = await self._repo.update(tarea_id, asignado_a=data.nuevo_asignado_a)
        if updated is None:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")
        return self._to_response(updated)

    # ------------------------------------------------------------------
    # Task 5.5 — mis_tareas
    # ------------------------------------------------------------------

    async def mis_tareas(
        self,
        current_user: CurrentUser,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TareaResponse]:
        """Return tareas assigned to the authenticated user.

        F8.1 — asignado_a filter scoped to session user.
        Tenant isolation guaranteed by repository.
        """
        tareas = await self._repo.listar(
            asignado_a=current_user.user_id,
            limit=limit,
            offset=offset,
        )
        return [self._to_response(t) for t in tareas]

    # ------------------------------------------------------------------
    # Task 5.6 — listar_admin
    # ------------------------------------------------------------------

    async def listar_admin(
        self,
        filtros: TareaFiltros,
        current_user: CurrentUser,  # noqa: ARG002 — available for role-based scoping
    ) -> list[TareaResponse]:
        """Return all tenant tareas with optional filters and pagination.

        F8.3 — admin / COORDINADOR view.
        Service passes all filter fields to repository for composable filtering.
        Tenant isolation guaranteed by repository.
        """
        tareas = await self._repo.listar(
            estado=filtros.estado.value if filtros.estado else None,
            asignado_a=filtros.asignado_a,
            asignado_por=filtros.asignado_por,
            materia_id=filtros.materia_id,
            limit=filtros.limit,
            offset=filtros.offset,
        )
        return [self._to_response(t) for t in tareas]

    # ------------------------------------------------------------------
    # Task 5.7 — agregar_comentario
    # ------------------------------------------------------------------

    async def agregar_comentario(
        self,
        tarea_id: uuid.UUID,
        data: ComentarioTareaCreate,
        current_user: CurrentUser,
    ) -> ComentarioTareaResponse:
        """Add a comment to a tarea.

        autor_id = current_user.user_id (from JWT — never from body — D7).
        Validates that the tarea exists and is not soft-deleted in this tenant.
        Raises HTTPException(404) if tarea not found.
        """
        # Validate tarea exists in tenant (raises 404 if not)
        await self._get_tarea_or_404(tarea_id)

        comentario = ComentarioTarea(
            tenant_id=self._tenant_id,
            tarea_id=tarea_id,
            autor_id=current_user.user_id,
            texto=data.texto,
        )
        comentario = await self._comentario_repo.create(comentario)
        return self._to_comentario_response(comentario)

    # ------------------------------------------------------------------
    # Task 5.8 — listar_comentarios
    # ------------------------------------------------------------------

    async def listar_comentarios(
        self,
        tarea_id: uuid.UUID,
        current_user: CurrentUser,  # noqa: ARG002
    ) -> list[ComentarioTareaResponse]:
        """Return the chronological comment thread for a tarea.

        F8.2 — ordered by creado_at asc (D7).
        Validates tarea exists in tenant first.
        """
        await self._get_tarea_or_404(tarea_id)
        comentarios = await self._comentario_repo.listar_por_tarea(tarea_id)
        return [self._to_comentario_response(c) for c in comentarios]
