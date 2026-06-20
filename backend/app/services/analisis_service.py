"""
app/services/analisis_service.py — AnalisisService.

Analytics logic over existing Calificacion and EntradaPadron data:
  - get_atrasados      : detect late students (RN-06)
  - get_ranking        : rank by approved activities (RN-09)
  - get_notas_finales  : per-student pass ratio (F2.5)
  - get_reporte        : aggregated metrics for an asignacion (F2.4)
  - get_monitor_general: cross-cutting monitor for all tenant students (F2.7) — C-23

No new DB tables — operates on Calificacion, EntradaPadron, VersionPadron, Asignacion,
Materia, Cohorte.
Computation is done in-memory in Python (D-01: dataset is small, < 200 × 30).

Tenant isolation: all repo calls scoped to tenant_id (from JWT).

Implemented: C-11 (analisis-atrasados-reportes)
Updated:     C-23 (monitor-general)
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calificacion import Calificacion
from app.models.entrada_padron import EntradaPadron
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.calificacion_repository import CalificacionRepository
from app.repositories.cohorte_repository import CohorteRepository
from app.repositories.entrada_padron_repository import EntradaPadronRepository
from app.repositories.materia_repository import MateriaRepository
from app.repositories.version_padron_repository import VersionPadronRepository
from app.schemas.analisis import (
    AlumnoAtrasado,
    AtrasadosResponse,
    MonitorGeneralItem,
    MonitorGeneralResponse,
    NotaFinalItem,
    NotasFinalesResponse,
    RankingItem,
    RankingResponse,
    ReporteAsignacion,
)


# ---------------------------------------------------------------------------
# DB accessor — shared by all public functions
# ---------------------------------------------------------------------------

async def _get_entradas_activas(
    asignacion_id: uuid.UUID,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[EntradaPadron]:
    """Return EntradaPadron rows for the asignacion's active padrón version.

    Returns [] if the asignacion is not found or has no active padrón version.
    Tenant is enforced via each repository's _base_query().
    """
    asignacion_repo = AsignacionRepository(session=db, tenant_id=tenant_id)
    asignacion = await asignacion_repo.get(asignacion_id)
    if asignacion is None or asignacion.materia_id is None or asignacion.cohorte_id is None:
        return []

    version_repo = VersionPadronRepository(session=db, tenant_id=tenant_id)
    version = await version_repo.get_activa(asignacion.materia_id, asignacion.cohorte_id)
    if version is None:
        return []

    entrada_repo = EntradaPadronRepository(session=db, tenant_id=tenant_id)
    return await entrada_repo.list_by_version(version.id)


# ---------------------------------------------------------------------------
# Pure computation helpers — sync, no DB, easily unit-testable
# ---------------------------------------------------------------------------

def _compute_atrasados(
    entradas: list[EntradaPadron],
    cals: list[Calificacion],
) -> list[AlumnoAtrasado]:
    """Compute the list of late students from pre-fetched data.

    An alumno is late (atrasado) if:
      (a) they have zero calificaciones in this asignacion, OR
      (b) they have at least one calificacion with aprobado=False.

    actividades_faltantes is always [] in this MVP (no master activity list).
    actividades_reprobadas lists the activity names where aprobado=False.
    """
    cals_by_entrada: dict[uuid.UUID, list[Calificacion]] = defaultdict(list)
    for cal in cals:
        cals_by_entrada[cal.entrada_padron_id].append(cal)

    result: list[AlumnoAtrasado] = []
    for entrada in entradas:
        entrada_cals = cals_by_entrada.get(entrada.id, [])
        reprobadas = [c.actividad for c in entrada_cals if not c.aprobado]

        if len(entrada_cals) == 0 or reprobadas:
            result.append(
                AlumnoAtrasado(
                    alumno_id=entrada.id,
                    nombre=entrada.nombre,
                    apellidos=entrada.apellidos,
                    actividades_faltantes=[],
                    actividades_reprobadas=reprobadas,
                )
            )

    return result


def _compute_ranking(
    entradas: list[EntradaPadron],
    cals: list[Calificacion],
) -> list[RankingItem]:
    """Rank students by number of approved activities (RN-09).

    Only students with count(aprobado=True) >= 1 are included, sorted desc.
    """
    entrada_map: dict[uuid.UUID, EntradaPadron] = {e.id: e for e in entradas}

    aprobadas_count: dict[uuid.UUID, int] = defaultdict(int)
    for cal in cals:
        if cal.aprobado:
            aprobadas_count[cal.entrada_padron_id] += 1

    items: list[RankingItem] = []
    for entrada_id, count in aprobadas_count.items():
        if count < 1:
            continue
        entrada = entrada_map.get(entrada_id)
        if entrada is None:
            continue
        items.append(
            RankingItem(
                alumno_id=entrada_id,
                nombre=entrada.nombre,
                apellidos=entrada.apellidos,
                aprobadas=count,
            )
        )

    items.sort(key=lambda x: x.aprobadas, reverse=True)
    return items


def _compute_notas_finales(
    entradas: list[EntradaPadron],
    cals: list[Calificacion],
) -> list[NotaFinalItem]:
    """Compute per-student pass ratio (F2.5).

    Every student in the active padrón is included.
    Students without calificaciones get aprobadas=0, total=0, pct=0.0.
    """
    cals_by_entrada: dict[uuid.UUID, list[Calificacion]] = defaultdict(list)
    for cal in cals:
        cals_by_entrada[cal.entrada_padron_id].append(cal)

    items: list[NotaFinalItem] = []
    for entrada in entradas:
        entrada_cals = cals_by_entrada.get(entrada.id, [])
        total = len(entrada_cals)
        aprobadas = sum(1 for c in entrada_cals if c.aprobado)
        pct = (aprobadas / total * 100.0) if total > 0 else 0.0

        items.append(
            NotaFinalItem(
                alumno_id=entrada.id,
                nombre=entrada.nombre,
                apellidos=entrada.apellidos,
                aprobadas=aprobadas,
                total_actividades=total,
                porcentaje_aprobacion=pct,
            )
        )

    return items


def _compute_reporte(
    entradas: list[EntradaPadron],
    cals: list[Calificacion],
) -> ReporteAsignacion:
    """Aggregate metrics for a single asignacion (F2.4).

    tiene_datos=True only when calificaciones exist.
    pct_aprobacion_general is across all calificaciones, not per-student.
    total_actividades is the count of distinct activity names imported.
    """
    total_alumnos = len(entradas)
    tiene_datos = len(cals) > 0

    atrasados = _compute_atrasados(entradas, cals)
    total_atrasados = len(atrasados)

    total_cal = len(cals)
    total_aprobadas = sum(1 for c in cals if c.aprobado)
    pct_aprobacion_general = (total_aprobadas / total_cal * 100.0) if total_cal > 0 else 0.0

    total_actividades = len({c.actividad for c in cals})

    return ReporteAsignacion(
        total_alumnos=total_alumnos,
        total_atrasados=total_atrasados,
        pct_aprobacion_general=pct_aprobacion_general,
        total_actividades=total_actividades,
        tiene_datos=tiene_datos,
    )


# ---------------------------------------------------------------------------
# Monitor general (F2.7) — C-23
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MonitorFilters:
    """Optional filters for get_monitor_general."""

    materia_id: uuid.UUID | None = None
    cohorte_id: uuid.UUID | None = None
    comision: str | None = None
    busqueda: str | None = None          # partial, case-insensitive match on nombre/apellidos
    estado_actividad: str | None = None  # "al_dia" | "atrasado" | "sin_datos"


def _derive_estado(
    entrada_cals: list,
) -> tuple[str, int, int]:
    """Return (estado, aprobadas, totales) for a single student.

    Rules:
      - No calificaciones → "sin_datos", (0, 0)
      - All aprobado=True  → "al_dia"
      - Any  aprobado=False → "atrasado"
    """
    if not entrada_cals:
        return "sin_datos", 0, 0

    totales = len(entrada_cals)
    aprobadas = sum(1 for c in entrada_cals if c.aprobado)
    any_reprobada = any(not c.aprobado for c in entrada_cals)

    estado = "atrasado" if any_reprobada else "al_dia"
    return estado, aprobadas, totales


def _compute_monitor(
    bundles: list[tuple],  # list of (asignacion, entradas, calificaciones)
    filters: MonitorFilters,
) -> MonitorGeneralResponse:
    """Build MonitorGeneralResponse from pre-fetched bundles.

    Each bundle is a 3-tuple: (asignacion_ns, list[entrada_ns], list[cal_ns]).
    The asignacion namespace must expose: id, materia_id, cohorte_id,
    materia_nombre, cohorte_nombre.
    The entrada namespace must expose: id, nombre, apellidos, email, comision.
    The cal namespace must expose: entrada_padron_id, aprobado.

    All filters are applied in-memory after building per-student estado.
    """
    items: list[MonitorGeneralItem] = []

    for asignacion, entradas, cals in bundles:
        # Pre-filter by materia_id / cohorte_id at the bundle level (fast path)
        if filters.materia_id is not None and asignacion.materia_id != filters.materia_id:
            continue
        if filters.cohorte_id is not None and asignacion.cohorte_id != filters.cohorte_id:
            continue

        # Build cal index per entrada
        cals_by_entrada: dict[uuid.UUID, list] = defaultdict(list)
        for cal in cals:
            cals_by_entrada[cal.entrada_padron_id].append(cal)

        for entrada in entradas:
            # comision filter
            if filters.comision is not None and entrada.comision != filters.comision:
                continue

            # busqueda filter (name / apellidos, case-insensitive, partial)
            if filters.busqueda is not None:
                term = filters.busqueda.lower()
                haystack = f"{entrada.nombre} {entrada.apellidos}".lower()
                if term not in haystack:
                    continue

            estado, aprobadas, totales = _derive_estado(cals_by_entrada.get(entrada.id, []))

            # estado_actividad filter
            if filters.estado_actividad is not None and estado != filters.estado_actividad:
                continue

            items.append(
                MonitorGeneralItem(
                    alumno_id=entrada.id,
                    nombre=entrada.nombre,
                    apellidos=entrada.apellidos,
                    email=entrada.email,
                    materia=asignacion.materia_nombre,
                    comision=entrada.comision,
                    cohorte=asignacion.cohorte_nombre,
                    actividades_aprobadas=aprobadas,
                    actividades_totales=totales,
                    estado=estado,
                )
            )

    return MonitorGeneralResponse(items=items, total=len(items))


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------

async def get_atrasados(
    asignacion_id: uuid.UUID,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> AtrasadosResponse:
    """Return list of late students for the given asignacion."""
    entradas = await _get_entradas_activas(asignacion_id, db, tenant_id)
    if not entradas:
        return AtrasadosResponse(atrasados=[], sin_padron=True)

    cal_repo = CalificacionRepository(session=db, tenant_id=tenant_id)
    cals = await cal_repo.list_by_entradas([e.id for e in entradas])

    return AtrasadosResponse(
        atrasados=_compute_atrasados(entradas, cals),
        sin_padron=False,
    )


async def get_ranking(
    asignacion_id: uuid.UUID,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> RankingResponse:
    """Return students ranked by number of approved activities (RN-09)."""
    entradas = await _get_entradas_activas(asignacion_id, db, tenant_id)
    if not entradas:
        return RankingResponse(items=[])

    cal_repo = CalificacionRepository(session=db, tenant_id=tenant_id)
    cals = await cal_repo.list_by_entradas([e.id for e in entradas])

    return RankingResponse(items=_compute_ranking(entradas, cals))


async def get_notas_finales(
    asignacion_id: uuid.UUID,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> NotasFinalesResponse:
    """Return per-student pass ratios for the given asignacion (F2.5)."""
    entradas = await _get_entradas_activas(asignacion_id, db, tenant_id)
    if not entradas:
        return NotasFinalesResponse(items=[])

    cal_repo = CalificacionRepository(session=db, tenant_id=tenant_id)
    cals = await cal_repo.list_by_entradas([e.id for e in entradas])

    return NotasFinalesResponse(items=_compute_notas_finales(entradas, cals))


async def get_reporte(
    asignacion_id: uuid.UUID,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> ReporteAsignacion:
    """Return aggregated metrics for the given asignacion (F2.4)."""
    entradas = await _get_entradas_activas(asignacion_id, db, tenant_id)
    if not entradas:
        return ReporteAsignacion(
            total_alumnos=0,
            total_atrasados=0,
            pct_aprobacion_general=0.0,
            total_actividades=0,
            tiene_datos=False,
        )

    cal_repo = CalificacionRepository(session=db, tenant_id=tenant_id)
    cals = await cal_repo.list_by_entradas([e.id for e in entradas])

    return _compute_reporte(entradas, cals)


async def get_monitor_general(
    tenant_id: uuid.UUID,
    filters: MonitorFilters,
    db: AsyncSession,
) -> MonitorGeneralResponse:
    """Return the cross-cutting monitor view for all students in the tenant (F2.7).

    Fetches all asignaciones with a valid padrón, then builds per-student
    estado from their calificaciones. All filtering is applied in-memory
    following the same D-01 pattern as the other analytics functions.

    Tenant isolation is enforced via every repo's _base_query().
    """
    asignacion_repo = AsignacionRepository(session=db, tenant_id=tenant_id)
    asignaciones = await asignacion_repo.list_with_filters()

    materia_repo = MateriaRepository(session=db, tenant_id=tenant_id)
    cohorte_repo = CohorteRepository(session=db, tenant_id=tenant_id)
    version_repo = VersionPadronRepository(session=db, tenant_id=tenant_id)
    entrada_repo = EntradaPadronRepository(session=db, tenant_id=tenant_id)
    cal_repo = CalificacionRepository(session=db, tenant_id=tenant_id)

    # Cache lookups to avoid N+1 per asignacion
    materia_cache: dict[uuid.UUID, str] = {}
    cohorte_cache: dict[uuid.UUID, str] = {}

    bundles = []
    for asignacion in asignaciones:
        if asignacion.materia_id is None or asignacion.cohorte_id is None:
            continue

        version = await version_repo.get_activa(asignacion.materia_id, asignacion.cohorte_id)
        if version is None:
            continue

        entradas = await entrada_repo.list_by_version(version.id)
        if not entradas:
            continue

        # Resolve materia/cohorte names (with per-request cache)
        if asignacion.materia_id not in materia_cache:
            materia = await materia_repo.get(asignacion.materia_id)
            materia_cache[asignacion.materia_id] = materia.nombre if materia else ""
        if asignacion.cohorte_id not in cohorte_cache:
            cohorte = await cohorte_repo.get(asignacion.cohorte_id)
            cohorte_cache[asignacion.cohorte_id] = cohorte.nombre if cohorte else ""

        cals = await cal_repo.list_by_entradas([e.id for e in entradas])

        # Build a lightweight namespace so _compute_monitor stays pure / testable
        from types import SimpleNamespace  # noqa: PLC0415
        asig_ns = SimpleNamespace(
            id=asignacion.id,
            materia_id=asignacion.materia_id,
            cohorte_id=asignacion.cohorte_id,
            materia_nombre=materia_cache[asignacion.materia_id],
            cohorte_nombre=cohorte_cache[asignacion.cohorte_id],
        )
        bundles.append((asig_ns, entradas, cals))

    return _compute_monitor(bundles, filters)
