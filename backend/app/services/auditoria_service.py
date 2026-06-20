"""
app/services/auditoria_service.py — AuditoriaService.

Orchestrates the audit panel and filtered log functionality (C-19):
  - Resolves the COORDINADOR team via Asignacion (C-07)
  - Applies scope (global → actor_ids=None; propio → coordinator team)
  - Delegates all DB queries to AuditLogRepository
  - Maps COMUNICACION_* action codes to named states

Governance ALTO — this module enforces scope; fail-closed is a hard requirement.

Rules:
  - No direct DB access; all queries via repository.
  - Fail-closed: coordinator with empty team → empty result, NEVER all-tenant data.
  - Identity and tenant always from session/JWT (passed as parameters, never from request).

Implemented: C-19 (panel-auditoria-metricas)
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.audit_log import AuditLogRepository
from app.schemas.auditoria import (
    AccionesPorDiaItem,
    AccionesPorDiaResponse,
    AuditLogItemResponse,
    ComunicacionesPorDocenteItem,
    ComunicacionesPorDocenteResponse,
    InteraccionesDocenteMateriaItem,
    InteraccionesDocenteMateriaResponse,
    LogFiltradoQuery,
    LogFiltradoResponse,
    UltimasAccionesResponse,
)

# ---------------------------------------------------------------------------
# 3.4 — COMUNICACION_* → estado mapping (centralised constant)
# ---------------------------------------------------------------------------

#: Maps accion code → canonical state name.
#: Codes not in this mapping are not counted as communication states.
COMUNICACION_ESTADO: dict[str, str] = {
    "COMUNICACION_CREAR": "Pendiente",
    "COMUNICACION_ENVIAR": "Enviado",
    "COMUNICACION_ENVIANDO": "Enviando",
    "COMUNICACION_FALLAR": "Fallido",
    "COMUNICACION_CANCELAR": "Cancelado",
    # Aliases / variants that may appear in the catalog
    "COMUNICACION_PENDIENTE": "Pendiente",
    "COMUNICACION_ENVIADO": "Enviado",
    "COMUNICACION_FALLIDO": "Fallido",
    "COMUNICACION_CANCELADO": "Cancelado",
}

#: Reverse mapping: estado name → set of accion codes.
_ESTADO_TO_ACCIONES: dict[str, set[str]] = defaultdict(set)
for _accion, _estado in COMUNICACION_ESTADO.items():
    _ESTADO_TO_ACCIONES[_estado].add(_accion)


def _estado_to_accion_codes(estado: str) -> set[str]:
    """Return the set of COMUNICACION_* codes that map to the given estado name."""
    return _ESTADO_TO_ACCIONES.get(estado, set())


# ---------------------------------------------------------------------------
# AuditoriaService
# ---------------------------------------------------------------------------

class AuditoriaService:
    """Service layer for audit panel and filtered log.

    Constructor parameters:
        session   — open AsyncSession for the current request
        tenant_id — UUID of the tenant (always from the JWT session)
    """

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._audit_repo = AuditLogRepository(session=session, tenant_id=tenant_id)
        self._asignacion_repo = AsignacionRepository(session=session, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # 3.2 — Resolver equipo del coordinador (from Asignacion C-07)
    # ------------------------------------------------------------------

    async def resolver_equipo_coordinador(
        self, coordinador_id: uuid.UUID
    ) -> set[uuid.UUID]:
        """Return the set of usuario_ids of the coordinator's team.

        Queries vigente Asignaciones where responsable_id == coordinador_id.
        The result is the set of usuario_ids of PROFESOR/TUTOR members.

        Fail-closed: if no asignaciones found, returns empty set (caller must
        treat empty set as "no data" — never as "all data").

        Parameters
        ----------
        coordinador_id:
            UUID of the COORDINADOR whose team we are resolving.

        Returns
        -------
        Set of usuario_id UUIDs belonging to the coordinator's team.
        """
        asignaciones = await self._asignacion_repo.list_with_filters(
            responsable_id=coordinador_id,
        )
        return {a.usuario_id for a in asignaciones}

    # ------------------------------------------------------------------
    # 3.3 — Scope resolution
    # ------------------------------------------------------------------

    async def _resolver_actor_ids(
        self,
        alcance: str,
        coordinador_id: uuid.UUID,
        usuario_id_filtro: uuid.UUID | None = None,
    ) -> list[uuid.UUID] | None:
        """Resolve actor_ids for repository queries based on permission scope.

        - alcance == 'global': actor_ids=None (no filter — all tenant)
          If usuario_id_filtro is provided, scope to that single user.
        - alcance == 'propio': actor_ids = coordinator's team (fail-closed)
          If usuario_id_filtro is provided, intersect with team.
          If filtro not in team → empty list (fail-closed).

        Parameters
        ----------
        alcance:
            'global' | 'propio' — from PermisoConcedido.alcance.
        coordinador_id:
            current_user.user_id — used to resolve team when alcance=='propio'.
        usuario_id_filtro:
            Optional usuario_id filter from query params.

        Returns
        -------
        None for global (no actor filter), or list of UUIDs (may be empty).
        """
        if alcance == "global":
            if usuario_id_filtro is not None:
                return [usuario_id_filtro]
            return None

        # alcance == "propio": resolve coordinator team
        equipo = await self.resolver_equipo_coordinador(coordinador_id)

        if not equipo:
            # Fail-closed: empty team → empty result
            return []

        if usuario_id_filtro is not None:
            # Intersect: only return if the requested user is in the team
            if usuario_id_filtro in equipo:
                return [usuario_id_filtro]
            return []  # Fail-closed: requested user outside team

        return list(equipo)

    # ------------------------------------------------------------------
    # 3.5 — Panel: acciones por día
    # ------------------------------------------------------------------

    async def panel_acciones_por_dia(
        self,
        *,
        desde: datetime,
        hasta: datetime,
        alcance: str,
        coordinador_id: uuid.UUID,
    ) -> AccionesPorDiaResponse:
        """Return daily action counts in a date range, scoped by permission.

        Parameters
        ----------
        desde, hasta:
            Date range (inclusive).
        alcance:
            'global' | 'propio' — from PermisoConcedido.
        coordinador_id:
            current_user.user_id (used for 'propio' scope resolution).
        """
        actor_ids = await self._resolver_actor_ids(alcance, coordinador_id)
        rows = await self._audit_repo.acciones_por_dia(
            desde=desde, hasta=hasta, actor_ids=actor_ids
        )
        items = [AccionesPorDiaItem(dia=r["dia"], total=r["total"]) for r in rows]
        return AccionesPorDiaResponse(items=items)

    # ------------------------------------------------------------------
    # 3.6 — Panel: comunicaciones por docente
    # ------------------------------------------------------------------

    async def panel_comunicaciones_por_docente(
        self,
        *,
        alcance: str,
        coordinador_id: uuid.UUID,
    ) -> ComunicacionesPorDocenteResponse:
        """Return communication state distribution per actor, scoped by permission.

        Groups COMUNICACION_* action codes into named states (see COMUNICACION_ESTADO).
        """
        actor_ids = await self._resolver_actor_ids(alcance, coordinador_id)
        rows = await self._audit_repo.comunicaciones_por_docente(actor_ids=actor_ids)

        # Aggregate per actor_id → estado counts
        agg: dict[uuid.UUID, dict[str, int]] = defaultdict(
            lambda: {"pendiente": 0, "enviando": 0, "enviado": 0, "fallido": 0, "cancelado": 0}
        )
        for row in rows:
            estado = COMUNICACION_ESTADO.get(row["accion"])
            if estado is None:
                continue  # skip unknown codes
            actor = row["actor_id"]
            agg[actor][estado.lower()] += row["total"]

        items = [
            ComunicacionesPorDocenteItem(actor_id=actor_id, **counts)
            for actor_id, counts in agg.items()
        ]
        return ComunicacionesPorDocenteResponse(items=items)

    # ------------------------------------------------------------------
    # 3.7 — Panel: interacciones por docente × materia
    # ------------------------------------------------------------------

    async def panel_interacciones_docente_materia(
        self,
        *,
        alcance: str,
        coordinador_id: uuid.UUID,
    ) -> InteraccionesDocenteMateriaResponse:
        """Return interaction counts per actor × materia, scoped by permission.

        Rows with materia_id=None represent the 'sin materia' bucket.
        """
        actor_ids = await self._resolver_actor_ids(alcance, coordinador_id)
        rows = await self._audit_repo.interacciones_por_docente_materia(
            actor_ids=actor_ids
        )
        items = [
            InteraccionesDocenteMateriaItem(
                actor_id=r["actor_id"],
                materia_id=r["materia_id"],
                total=r["total"],
            )
            for r in rows
        ]
        return InteraccionesDocenteMateriaResponse(items=items)

    # ------------------------------------------------------------------
    # 3.8 — Panel: últimas N acciones
    # ------------------------------------------------------------------

    async def panel_ultimas_acciones(
        self,
        *,
        limit: int = 200,
        alcance: str,
        coordinador_id: uuid.UUID,
    ) -> UltimasAccionesResponse:
        """Return the latest N audit records, scoped by permission.

        Default limit is 200. The repository caps at _MAX_ULTIMAS_ACCIONES (1000).
        """
        actor_ids = await self._resolver_actor_ids(alcance, coordinador_id)
        records = await self._audit_repo.ultimas_acciones(
            limit=limit, actor_ids=actor_ids
        )
        items = [AuditLogItemResponse.model_validate(r) for r in records]
        return UltimasAccionesResponse(items=items)

    # ------------------------------------------------------------------
    # 3.9 — Log filtrado
    # ------------------------------------------------------------------

    async def log_filtrado(
        self,
        *,
        query: LogFiltradoQuery,
        alcance: str,
        coordinador_id: uuid.UUID,
    ) -> LogFiltradoResponse:
        """Return filtered, paginated audit log scoped by permission.

        Applies all optional filters from LogFiltradoQuery.
        In 'propio' scope, usuario_id filter is intersected with coordinator team
        (fail-closed: if requested user is outside team → empty result).
        """
        actor_ids = await self._resolver_actor_ids(
            alcance, coordinador_id, usuario_id_filtro=query.usuario_id
        )

        # Resolve accion filter: if estado is provided, map to accion codes
        # If both accion and estado are provided, accion takes precedence
        accion_filter: str | None = query.accion
        if accion_filter is None and query.estado is not None:
            # estado filter: we need to get records matching any of the codes for that estado
            # Since listar_filtrado supports one accion code, we handle this in service:
            # We'll pass actor_ids and other filters, then post-filter by accion in Python
            # if there are multiple codes. For single code, pass it directly.
            estado_codes = _estado_to_accion_codes(query.estado)
            if not estado_codes:
                # Unknown estado — return empty
                return LogFiltradoResponse(items=[], total_returned=0)
            if len(estado_codes) == 1:
                accion_filter = next(iter(estado_codes))
            else:
                # Multiple codes for this estado: fetch without accion filter and post-filter
                records = await self._audit_repo.listar_filtrado(
                    desde=query.desde,
                    hasta=query.hasta,
                    materia_id=query.materia_id,
                    actor_ids=actor_ids,
                    accion=None,
                    limit=query.limit,
                    offset=query.offset,
                )
                records = [r for r in records if r.accion in estado_codes]
                items = [AuditLogItemResponse.model_validate(r) for r in records]
                return LogFiltradoResponse(items=items, total_returned=len(items))

        records = await self._audit_repo.listar_filtrado(
            desde=query.desde,
            hasta=query.hasta,
            materia_id=query.materia_id,
            actor_ids=actor_ids,
            accion=accion_filter,
            limit=query.limit,
            offset=query.offset,
        )
        items = [AuditLogItemResponse.model_validate(r) for r in records]
        return LogFiltradoResponse(items=items, total_returned=len(items))
