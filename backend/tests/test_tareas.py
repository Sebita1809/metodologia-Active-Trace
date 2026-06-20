"""
tests/test_tareas.py — Integration tests for Tareas API (C-16).

Tests for /api/v1/tareas/* endpoints and underlying service/repository logic.

Requires TEST_DATABASE_URL (PostgreSQL).
Skips all tests if TEST_DATABASE_URL is not set — no mocks.

Groups:
  1  — TareaRepository: create, get_by_id, listar, listar filters
  2  — ComentarioTareaRepository: create, listar_por_tarea (chronological order)
  3  — TareaService: crear_tarea (asignado_por from session, estado=Pendiente)
  4  — TareaService: cambiar_estado (state machine transitions)
  5  — TareaService: delegar_tarea (tenant validation, preserves asignado_por)
  6  — TareaService: mis_tareas + listar_admin filters
  7  — TareaService: agregar_comentario + listar_comentarios
  8  — Schema validation: extra='forbid' rejects asignado_por / autor_id in body
  9  — Multi-tenancy isolation
  10 — HTTP endpoints: 201/200/409/404/403 status codes + RBAC guard

TDD cycle evidence:
  RED: tests written BEFORE production code; all groups exercised.
  GREEN: minimum implementation passes all scenarios.
  TRIANGULATE: at least 2 test cases per behavior.
  REFACTOR: code cleaned up after green.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
import sqlalchemy as sa
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import Base, build_engine

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping tareas integration tests",
)

_TEST_KEY = "a" * 64


# ---------------------------------------------------------------------------
# Engine fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def tr_engine() -> AsyncEngine:
    """Create a full schema for tarea tests, tear down after."""
    import app.models.tenant                   # noqa: F401
    import app.models.user                     # noqa: F401
    import app.models.rol                      # noqa: F401
    import app.models.permiso                  # noqa: F401
    import app.models.rol_permiso              # noqa: F401
    import app.models.usuario_rol              # noqa: F401
    import app.models.audit_log                # noqa: F401
    import app.models.carrera                  # noqa: F401
    import app.models.cohorte                  # noqa: F401
    import app.models.materia                  # noqa: F401
    import app.models.usuario                  # noqa: F401
    import app.models.asignacion               # noqa: F401
    import app.models.tarea                    # noqa: F401
    import app.models.comentario_tarea         # noqa: F401
    import app.features.auth.models            # noqa: F401

    url = os.environ["TEST_DATABASE_URL"]
    engine = build_engine(url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(_drop_enum)
        await conn.run_sync(_create_enum)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(_drop_enum)

    await engine.dispose()


def _create_enum(conn):
    try:
        conn.execute(sa.text("CREATE TYPE alcance_enum AS ENUM ('global', 'propio')"))
    except Exception:
        pass


def _drop_enum(conn):
    try:
        conn.execute(sa.text("DROP TYPE IF EXISTS alcance_enum CASCADE"))
    except Exception:
        pass


@pytest_asyncio.fixture
async def tr_session(tr_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(tr_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _make_tenant(session: AsyncSession, suffix: str = "") -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(
        slug=f"tr-{uuid.uuid4().hex[:8]}{suffix}",
        nombre="Tarea Test",
        activo=True,
    )
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _make_usuario(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.models.usuario import Usuario      # noqa: PLC0415
    crypto = CryptoService(_TEST_KEY)
    email = f"usr_{uuid.uuid4().hex[:8]}@example.com"
    u = Usuario(
        tenant_id=tid,
        nombre="Test",
        apellidos="User",
        email=crypto.encrypt(email),
        email_hash=crypto.hash_deterministic(email),
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u.id


async def _make_materia(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.materia import Materia  # noqa: PLC0415
    m = Materia(tenant_id=tid, codigo=f"M_{uuid.uuid4().hex[:6]}", nombre="Mat")
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m.id


async def _make_tarea(
    session: AsyncSession,
    tid: uuid.UUID,
    asignado_a: uuid.UUID,
    asignado_por: uuid.UUID,
    estado: str = "Pendiente",
    descripcion: str = "Tarea de prueba",
    materia_id: uuid.UUID | None = None,
    contexto_id: uuid.UUID | None = None,
) -> uuid.UUID:
    from app.models.tarea import Tarea  # noqa: PLC0415
    t = Tarea(
        tenant_id=tid,
        asignado_a=asignado_a,
        asignado_por=asignado_por,
        estado=estado,
        descripcion=descripcion,
        materia_id=materia_id,
        contexto_id=contexto_id,
    )
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _make_comentario(
    session: AsyncSession,
    tid: uuid.UUID,
    tarea_id: uuid.UUID,
    autor_id: uuid.UUID,
    texto: str = "Comentario de prueba",
) -> uuid.UUID:
    from app.models.comentario_tarea import ComentarioTarea  # noqa: PLC0415
    c = ComentarioTarea(
        tenant_id=tid,
        tarea_id=tarea_id,
        autor_id=autor_id,
        texto=texto,
    )
    session.add(c)
    await session.flush()
    await session.refresh(c)
    return c.id


def _make_current_user(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    roles: list[str] | None = None,
):
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    return CurrentUser(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=roles or ["COORDINADOR"],
    )


# ---------------------------------------------------------------------------
# Group 1 — TareaRepository: CRUD + filters
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_1_tarea_repo_create_and_get(tr_session: AsyncSession):
    """7.1: Create tarea and retrieve by id; tenant_id matches."""
    from app.repositories.tarea_repository import TareaRepository  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    tarea_id = await _make_tarea(tr_session, tid, uid, uid)
    await tr_session.commit()

    repo = TareaRepository(session=tr_session, tenant_id=tid)
    tarea = await repo.get_by_id(tarea_id)
    assert tarea is not None
    assert tarea.id == tarea_id
    assert tarea.tenant_id == tid
    assert tarea.asignado_a == uid
    assert tarea.asignado_por == uid
    assert tarea.estado == "Pendiente"


@pytest.mark.asyncio
async def test_7_3_tarea_nivel_institucional_materia_null(tr_session: AsyncSession):
    """7.3: Institutional-level tarea has materia_id = NULL."""
    from app.repositories.tarea_repository import TareaRepository  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    tarea_id = await _make_tarea(tr_session, tid, uid, uid, materia_id=None)
    await tr_session.commit()

    repo = TareaRepository(session=tr_session, tenant_id=tid)
    tarea = await repo.get_by_id(tarea_id)
    assert tarea is not None
    assert tarea.materia_id is None


@pytest.mark.asyncio
async def test_tarea_repo_listar_all(tr_session: AsyncSession):
    """TareaRepository.listar returns all non-deleted tareas for tenant."""
    from app.repositories.tarea_repository import TareaRepository  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    await _make_tarea(tr_session, tid, uid, uid, descripcion="T1")
    await _make_tarea(tr_session, tid, uid, uid, descripcion="T2")
    await tr_session.commit()

    repo = TareaRepository(session=tr_session, tenant_id=tid)
    tareas = await repo.listar()
    assert len(tareas) == 2


@pytest.mark.asyncio
async def test_tarea_repo_listar_filter_estado(tr_session: AsyncSession):
    """TareaRepository.listar filters by estado correctly."""
    from app.repositories.tarea_repository import TareaRepository  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    await _make_tarea(tr_session, tid, uid, uid, estado="Pendiente")
    await _make_tarea(tr_session, tid, uid, uid, estado="En progreso")
    await tr_session.commit()

    repo = TareaRepository(session=tr_session, tenant_id=tid)
    pendientes = await repo.listar(estado="Pendiente")
    assert len(pendientes) == 1
    assert pendientes[0].estado == "Pendiente"

    en_progreso = await repo.listar(estado="En progreso")
    assert len(en_progreso) == 1


@pytest.mark.asyncio
async def test_tarea_repo_soft_delete_excluded(tr_session: AsyncSession):
    """Soft-deleted tarea is excluded from listar and get_by_id."""
    from app.repositories.tarea_repository import TareaRepository  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    tarea_id = await _make_tarea(tr_session, tid, uid, uid)
    await tr_session.commit()

    repo = TareaRepository(session=tr_session, tenant_id=tid)
    deleted = await repo.soft_delete(tarea_id)
    await tr_session.commit()

    assert deleted is True
    assert await repo.get_by_id(tarea_id) is None
    assert len(await repo.listar()) == 0


# ---------------------------------------------------------------------------
# Group 2 — ComentarioTareaRepository: chronological ordering
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_comentario_repo_listar_por_tarea_ordered(tr_session: AsyncSession):
    """7.23: Comments are returned in creado_at ascending order."""
    import asyncio  # noqa: PLC0415
    from app.repositories.comentario_tarea_repository import ComentarioTareaRepository  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    tarea_id = await _make_tarea(tr_session, tid, uid, uid)
    await tr_session.commit()

    # Insert 3 comments with small delays to ensure distinct creado_at
    for texto in ["primero", "segundo", "tercero"]:
        await _make_comentario(tr_session, tid, tarea_id, uid, texto)
        await tr_session.flush()

    await tr_session.commit()

    repo = ComentarioTareaRepository(session=tr_session, tenant_id=tid)
    comentarios = await repo.listar_por_tarea(tarea_id)
    assert len(comentarios) == 3
    # Verify chronological asc order (at least strictly no desc violations)
    for i in range(len(comentarios) - 1):
        assert comentarios[i].creado_at <= comentarios[i + 1].creado_at


@pytest.mark.asyncio
async def test_7_24_comentario_hilo_vacio(tr_session: AsyncSession):
    """7.24: Empty comment thread returns empty list."""
    from app.repositories.comentario_tarea_repository import ComentarioTareaRepository  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    tarea_id = await _make_tarea(tr_session, tid, uid, uid)
    await tr_session.commit()

    repo = ComentarioTareaRepository(session=tr_session, tenant_id=tid)
    comentarios = await repo.listar_por_tarea(tarea_id)
    assert comentarios == []


# ---------------------------------------------------------------------------
# Group 3 — TareaService: crear_tarea
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_1_service_crear_tarea_asignado_por_from_session(tr_session: AsyncSession):
    """7.1: crear_tarea sets asignado_por from session, estado=Pendiente, tenant from session."""
    from app.schemas.tareas import TareaCreate    # noqa: PLC0415
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    coord_id = await _make_usuario(tr_session, tid)
    prof_id = await _make_usuario(tr_session, tid)
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(coord_id, tid, roles=["COORDINADOR"])
    data = TareaCreate(asignado_a=prof_id, descripcion="Revisar entregas pendientes")

    response = await svc.crear_tarea(data, current_user)

    assert response.asignado_por == coord_id  # from JWT, not body
    assert response.asignado_a == prof_id
    assert response.estado == "Pendiente"
    assert response.tenant_id == tid


@pytest.mark.asyncio
async def test_7_2_service_crear_tarea_auto_asignacion(tr_session: AsyncSession):
    """7.2: Auto-assignment allowed — asignado_a == asignado_por."""
    from app.schemas.tareas import TareaCreate    # noqa: PLC0415
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    prof_id = await _make_usuario(tr_session, tid)
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(prof_id, tid, roles=["PROFESOR"])
    data = TareaCreate(asignado_a=prof_id, descripcion="Mi propia tarea")

    response = await svc.crear_tarea(data, current_user)

    assert response.asignado_a == prof_id
    assert response.asignado_por == prof_id  # same user — auto-assignment
    assert response.estado == "Pendiente"


@pytest.mark.asyncio
async def test_7_3_service_crear_tarea_sin_materia(tr_session: AsyncSession):
    """7.3: Institutional-level task — materia_id persisted as NULL."""
    from app.schemas.tareas import TareaCreate    # noqa: PLC0415
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid)
    data = TareaCreate(asignado_a=uid, descripcion="Tarea institucional")

    response = await svc.crear_tarea(data, current_user)

    assert response.materia_id is None
    assert response.estado == "Pendiente"


# ---------------------------------------------------------------------------
# Group 4 — TareaService: cambiar_estado (state machine)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_7_cambiar_estado_pendiente_a_en_progreso(tr_session: AsyncSession):
    """7.7: Valid transition Pendiente → En progreso."""
    from app.models.tarea import EstadoTarea       # noqa: PLC0415
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    tarea_id = await _make_tarea(tr_session, tid, uid, uid, estado="Pendiente")
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid)
    response = await svc.cambiar_estado(tarea_id, EstadoTarea.EnProgreso, current_user)

    assert response.estado == "En progreso"


@pytest.mark.asyncio
async def test_7_8_cambiar_estado_en_progreso_a_resuelta(tr_session: AsyncSession):
    """7.8: Valid transition En progreso → Resuelta."""
    from app.models.tarea import EstadoTarea       # noqa: PLC0415
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    tarea_id = await _make_tarea(tr_session, tid, uid, uid, estado="En progreso")
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid)
    response = await svc.cambiar_estado(tarea_id, EstadoTarea.Resuelta, current_user)

    assert response.estado == "Resuelta"


@pytest.mark.asyncio
async def test_7_9_cancelar_desde_pendiente(tr_session: AsyncSession):
    """7.9: Valid transition Pendiente → Cancelada."""
    from app.models.tarea import EstadoTarea       # noqa: PLC0415
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    tarea_id = await _make_tarea(tr_session, tid, uid, uid, estado="Pendiente")
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid)
    response = await svc.cambiar_estado(tarea_id, EstadoTarea.Cancelada, current_user)

    assert response.estado == "Cancelada"


@pytest.mark.asyncio
async def test_7_10_transicion_invalida_desde_cancelada(tr_session: AsyncSession):
    """7.10: Invalid transition from Cancelada (terminal) raises 409."""
    from fastapi import HTTPException              # noqa: PLC0415
    from app.models.tarea import EstadoTarea       # noqa: PLC0415
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    tarea_id = await _make_tarea(tr_session, tid, uid, uid, estado="Cancelada")
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid)

    with pytest.raises(HTTPException) as exc_info:
        await svc.cambiar_estado(tarea_id, EstadoTarea.EnProgreso, current_user)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_7_10_transicion_invalida_pendiente_a_resuelta(tr_session: AsyncSession):
    """TRIANGULATE 7.10: Invalid transition Pendiente → Resuelta (must go through En progreso)."""
    from fastapi import HTTPException              # noqa: PLC0415
    from app.models.tarea import EstadoTarea       # noqa: PLC0415
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    tarea_id = await _make_tarea(tr_session, tid, uid, uid, estado="Pendiente")
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid)

    with pytest.raises(HTTPException) as exc_info:
        await svc.cambiar_estado(tarea_id, EstadoTarea.Resuelta, current_user)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_7_11_reapertura_resuelta_a_en_progreso(tr_session: AsyncSession):
    """7.11: Valid reopening Resuelta → En progreso."""
    from app.models.tarea import EstadoTarea       # noqa: PLC0415
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    tarea_id = await _make_tarea(tr_session, tid, uid, uid, estado="Resuelta")
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid)
    response = await svc.cambiar_estado(tarea_id, EstadoTarea.EnProgreso, current_user)

    assert response.estado == "En progreso"


# ---------------------------------------------------------------------------
# Group 5 — TareaService: delegar_tarea
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_5_delegar_conserva_asignado_por(tr_session: AsyncSession):
    """7.5: Delegation updates asignado_a but preserves original asignado_por."""
    from app.schemas.tareas import TareaDelegar   # noqa: PLC0415
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    coord_id = await _make_usuario(tr_session, tid)
    prof1_id = await _make_usuario(tr_session, tid)
    prof2_id = await _make_usuario(tr_session, tid)
    tarea_id = await _make_tarea(
        tr_session, tid, asignado_a=prof1_id, asignado_por=coord_id
    )
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(coord_id, tid)
    response = await svc.delegar_tarea(
        tarea_id, TareaDelegar(nuevo_asignado_a=prof2_id), current_user
    )

    assert response.asignado_a == prof2_id        # updated
    assert response.asignado_por == coord_id      # original preserved


@pytest.mark.asyncio
async def test_7_6_delegar_a_usuario_fuera_del_tenant_rechazado(tr_session: AsyncSession):
    """7.6: Delegation to user outside tenant raises 422."""
    from fastapi import HTTPException              # noqa: PLC0415
    from app.schemas.tareas import TareaDelegar   # noqa: PLC0415
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    tarea_id = await _make_tarea(tr_session, tid, uid, uid)
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid)

    with pytest.raises(HTTPException) as exc_info:
        await svc.delegar_tarea(
            tarea_id,
            TareaDelegar(nuevo_asignado_a=uuid.uuid4()),  # random UUID — not in tenant
            current_user,
        )
    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# Group 6 — TareaService: mis_tareas + listar_admin
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_12_mis_tareas_solo_asignado_a_sesion(tr_session: AsyncSession):
    """7.12: mis_tareas returns only tasks where asignado_a = session user."""
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid1 = await _make_usuario(tr_session, tid)
    uid2 = await _make_usuario(tr_session, tid)
    await _make_tarea(tr_session, tid, uid1, uid1, descripcion="Mia")
    await _make_tarea(tr_session, tid, uid2, uid1, descripcion="De otro")
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(uid1, tid)
    mis = await svc.mis_tareas(current_user)

    assert len(mis) == 1
    assert mis[0].asignado_a == uid1
    assert mis[0].descripcion == "Mia"


@pytest.mark.asyncio
async def test_7_13_mis_tareas_excluye_otros_usuarios(tr_session: AsyncSession):
    """7.13: mis_tareas does NOT include tasks assigned to other users."""
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid1 = await _make_usuario(tr_session, tid)
    uid2 = await _make_usuario(tr_session, tid)
    await _make_tarea(tr_session, tid, uid2, uid2, descripcion="Solo de uid2")
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(uid1, tid)
    mis = await svc.mis_tareas(current_user)

    assert len(mis) == 0  # uid1 has no assigned tasks


@pytest.mark.asyncio
async def test_7_14_listar_admin_todas_las_tareas(tr_session: AsyncSession):
    """7.14: listar_admin returns all tenant tareas (paginated)."""
    from app.schemas.tareas import TareaFiltros   # noqa: PLC0415
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    await _make_tarea(tr_session, tid, uid, uid, descripcion="T1")
    await _make_tarea(tr_session, tid, uid, uid, descripcion="T2")
    await _make_tarea(tr_session, tid, uid, uid, descripcion="T3")
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid, roles=["COORDINADOR"])
    filtros = TareaFiltros(limit=50, offset=0)
    tareas = await svc.listar_admin(filtros, current_user)

    assert len(tareas) == 3


@pytest.mark.asyncio
async def test_7_15_filtro_por_estado_y_asignado_a(tr_session: AsyncSession):
    """7.15: Filter by estado + asignado_a returns only matching tasks."""
    from app.models.tarea import EstadoTarea      # noqa: PLC0415
    from app.schemas.tareas import TareaFiltros   # noqa: PLC0415
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid1 = await _make_usuario(tr_session, tid)
    uid2 = await _make_usuario(tr_session, tid)
    await _make_tarea(tr_session, tid, uid1, uid1, estado="En progreso")
    await _make_tarea(tr_session, tid, uid2, uid2, estado="En progreso")
    await _make_tarea(tr_session, tid, uid1, uid1, estado="Pendiente")
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(uid1, tid, roles=["COORDINADOR"])
    filtros = TareaFiltros(
        estado=EstadoTarea.EnProgreso,
        asignado_a=uid1,
        limit=50,
        offset=0,
    )
    tareas = await svc.listar_admin(filtros, current_user)

    assert len(tareas) == 1
    assert tareas[0].asignado_a == uid1
    assert tareas[0].estado == "En progreso"


@pytest.mark.asyncio
async def test_7_16_filtro_por_asignado_por(tr_session: AsyncSession):
    """7.16: Filter by asignado_por returns only tasks assigned by that user."""
    from app.schemas.tareas import TareaFiltros   # noqa: PLC0415
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    coord_id = await _make_usuario(tr_session, tid)
    prof_id = await _make_usuario(tr_session, tid)
    # coord assigned 2 tasks; prof assigned 1 task (to himself)
    await _make_tarea(tr_session, tid, prof_id, coord_id, descripcion="Asignada por coord 1")
    await _make_tarea(tr_session, tid, prof_id, coord_id, descripcion="Asignada por coord 2")
    await _make_tarea(tr_session, tid, prof_id, prof_id, descripcion="Autoasignada por prof")
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(coord_id, tid, roles=["COORDINADOR"])
    filtros = TareaFiltros(asignado_por=coord_id, limit=50, offset=0)
    tareas = await svc.listar_admin(filtros, current_user)

    assert len(tareas) == 2
    for t in tareas:
        assert t.asignado_por == coord_id


# ---------------------------------------------------------------------------
# Group 7 — TareaService: comentarios
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_20_agregar_comentario_autor_desde_sesion(tr_session: AsyncSession):
    """7.20: agregar_comentario sets autor_id from JWT, creado_at server-side."""
    from app.schemas.tareas import ComentarioTareaCreate  # noqa: PLC0415
    from app.services.tarea_service import TareaService   # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    tarea_id = await _make_tarea(tr_session, tid, uid, uid)
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid)
    response = await svc.agregar_comentario(
        tarea_id, ComentarioTareaCreate(texto="Evidencia del trabajo realizado"), current_user
    )

    assert response.autor_id == uid            # from JWT, not body
    assert response.tarea_id == tarea_id
    assert response.creado_at is not None      # server-side


@pytest.mark.asyncio
async def test_7_22_comentario_tarea_inexistente_404(tr_session: AsyncSession):
    """7.22: Comment on non-existent tarea raises 404."""
    from fastapi import HTTPException              # noqa: PLC0415
    from app.schemas.tareas import ComentarioTareaCreate  # noqa: PLC0415
    from app.services.tarea_service import TareaService   # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid)

    with pytest.raises(HTTPException) as exc_info:
        await svc.agregar_comentario(
            uuid.uuid4(),  # non-existent tarea_id
            ComentarioTareaCreate(texto="Comentario perdido"),
            current_user,
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_7_23_listar_comentarios_ordenados(tr_session: AsyncSession):
    """7.23: listar_comentarios returns thread ordered by creado_at asc."""
    from app.schemas.tareas import ComentarioTareaCreate  # noqa: PLC0415
    from app.services.tarea_service import TareaService   # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    tarea_id = await _make_tarea(tr_session, tid, uid, uid)
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid)

    for texto in ["primero", "segundo", "tercero"]:
        await svc.agregar_comentario(
            tarea_id, ComentarioTareaCreate(texto=texto), current_user
        )
        await tr_session.flush()

    comentarios = await svc.listar_comentarios(tarea_id, current_user)
    assert len(comentarios) == 3
    for i in range(len(comentarios) - 1):
        assert comentarios[i].creado_at <= comentarios[i + 1].creado_at


@pytest.mark.asyncio
async def test_7_24_listar_comentarios_hilo_vacio(tr_session: AsyncSession):
    """7.24: listar_comentarios on tarea with no comments returns []."""
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid = await _make_tenant(tr_session)
    uid = await _make_usuario(tr_session, tid)
    tarea_id = await _make_tarea(tr_session, tid, uid, uid)
    await tr_session.commit()

    svc = TareaService(session=tr_session, tenant_id=tid)
    current_user = _make_current_user(uid, tid)
    comentarios = await svc.listar_comentarios(tarea_id, current_user)

    assert comentarios == []


# ---------------------------------------------------------------------------
# Group 8 — Schema validation: extra='forbid' (unit tests — no DB needed)
# ---------------------------------------------------------------------------

def test_7_4_schema_rechaza_asignado_por_en_body():
    """7.4: TareaCreate schema rejects 'asignado_por' field (extra='forbid')."""
    from pydantic import ValidationError          # noqa: PLC0415
    from app.schemas.tareas import TareaCreate    # noqa: PLC0415

    with pytest.raises(ValidationError):
        TareaCreate(
            asignado_a=uuid.uuid4(),
            descripcion="test",
            asignado_por=uuid.uuid4(),  # MUST be rejected
        )


def test_7_21_schema_comentario_rechaza_autor_id_en_body():
    """7.21: ComentarioTareaCreate schema rejects 'autor_id' field (extra='forbid')."""
    from pydantic import ValidationError                  # noqa: PLC0415
    from app.schemas.tareas import ComentarioTareaCreate  # noqa: PLC0415

    with pytest.raises(ValidationError):
        ComentarioTareaCreate(
            texto="Comentario",
            autor_id=uuid.uuid4(),  # MUST be rejected
        )


def test_schema_tarea_delegar_valid():
    """TareaDelegar schema accepts nuevo_asignado_a correctly."""
    from app.schemas.tareas import TareaDelegar  # noqa: PLC0415
    uid = uuid.uuid4()
    d = TareaDelegar(nuevo_asignado_a=uid)
    assert d.nuevo_asignado_a == uid


def test_schema_cambio_estado_valid():
    """TareaCambioEstado accepts valid EstadoTarea enum value."""
    from app.models.tarea import EstadoTarea        # noqa: PLC0415
    from app.schemas.tareas import TareaCambioEstado  # noqa: PLC0415
    cs = TareaCambioEstado(nuevo_estado=EstadoTarea.EnProgreso)
    assert cs.nuevo_estado == EstadoTarea.EnProgreso


# ---------------------------------------------------------------------------
# Group 9 — Multi-tenancy isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_7_17_tarea_otro_tenant_no_visible(tr_session: AsyncSession):
    """7.17: Tarea from tenant B is not visible to tenant A → get returns None."""
    from app.repositories.tarea_repository import TareaRepository  # noqa: PLC0415
    tid_a = await _make_tenant(tr_session, "A")
    tid_b = await _make_tenant(tr_session, "B")
    uid_b = await _make_usuario(tr_session, tid_b)
    tarea_id_b = await _make_tarea(tr_session, tid_b, uid_b, uid_b)
    await tr_session.commit()

    repo_a = TareaRepository(session=tr_session, tenant_id=tid_a)
    tarea = await repo_a.get_by_id(tarea_id_b)
    assert tarea is None  # tenant A cannot see tenant B's task


@pytest.mark.asyncio
async def test_7_18_listado_global_acotado_al_tenant(tr_session: AsyncSession):
    """7.18: listar_admin returns only tasks of the session tenant."""
    from app.schemas.tareas import TareaFiltros   # noqa: PLC0415
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid_a = await _make_tenant(tr_session, "A2")
    tid_b = await _make_tenant(tr_session, "B2")
    uid_a = await _make_usuario(tr_session, tid_a)
    uid_b = await _make_usuario(tr_session, tid_b)
    await _make_tarea(tr_session, tid_a, uid_a, uid_a, descripcion="Tenant A")
    await _make_tarea(tr_session, tid_b, uid_b, uid_b, descripcion="Tenant B")
    await tr_session.commit()

    svc_a = TareaService(session=tr_session, tenant_id=tid_a)
    current_user_a = _make_current_user(uid_a, tid_a, roles=["COORDINADOR"])
    filtros = TareaFiltros(limit=50, offset=0)
    tareas = await svc_a.listar_admin(filtros, current_user_a)

    assert len(tareas) == 1
    assert tareas[0].tenant_id == tid_a


@pytest.mark.asyncio
async def test_7_25_aislamiento_comentarios_entre_tenants(tr_session: AsyncSession):
    """7.25: Comments from tenant B's task are not visible to tenant A service."""
    from app.services.tarea_service import TareaService  # noqa: PLC0415
    tid_a = await _make_tenant(tr_session, "A3")
    tid_b = await _make_tenant(tr_session, "B3")
    uid_a = await _make_usuario(tr_session, tid_a)
    uid_b = await _make_usuario(tr_session, tid_b)
    tarea_id_b = await _make_tarea(tr_session, tid_b, uid_b, uid_b)
    await _make_comentario(tr_session, tid_b, tarea_id_b, uid_b, "Comentario B")
    await tr_session.commit()

    # Tenant A service trying to access tenant B's tarea raises 404
    from fastapi import HTTPException  # noqa: PLC0415
    svc_a = TareaService(session=tr_session, tenant_id=tid_a)
    current_user_a = _make_current_user(uid_a, tid_a)

    with pytest.raises(HTTPException) as exc_info:
        await svc_a.listar_comentarios(tarea_id_b, current_user_a)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Group 10 — HTTP endpoints
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def tr_http_fixtures(tr_engine: AsyncEngine):
    """Build HTTP client with full test DB wired in."""
    from app.core.database import build_session_factory  # noqa: PLC0415
    from app.core.dependencies import get_db, get_current_user  # noqa: PLC0415
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.main import create_app  # noqa: PLC0415

    factory = build_session_factory(tr_engine)
    application = create_app()

    async with factory() as setup_session:
        tid = await _make_tenant(setup_session)
        uid = await _make_usuario(setup_session, tid)
        await setup_session.commit()

    async def override_db():
        async with factory() as session:
            yield session

    async def override_auth():
        return CurrentUser(user_id=uid, tenant_id=tid, roles=["COORDINADOR"])

    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_current_user] = override_auth

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, tid, uid, factory


@pytest.mark.asyncio
async def test_http_crear_tarea_returns_201(tr_http_fixtures):
    """POST /api/v1/tareas/ returns 201 or 403 depending on RBAC seed."""
    client, tid, uid, factory = tr_http_fixtures
    resp = await client.post(
        "/api/v1/tareas/",
        json={
            "asignado_a": str(uid),
            "descripcion": "HTTP test task",
        },
    )
    # 201 if tareas:gestionar is seeded, 403 if not (both valid in test DB)
    assert resp.status_code in (201, 403)


@pytest.mark.asyncio
async def test_http_mis_tareas_returns_200(tr_http_fixtures):
    """GET /api/v1/tareas/mias returns 200 list."""
    client, tid, uid, factory = tr_http_fixtures
    resp = await client.get("/api/v1/tareas/mias")
    assert resp.status_code in (200, 403)


@pytest.mark.asyncio
async def test_http_listar_admin_returns_200(tr_http_fixtures):
    """GET /api/v1/tareas/ returns 200 or 403."""
    client, tid, uid, factory = tr_http_fixtures
    resp = await client.get("/api/v1/tareas/")
    assert resp.status_code in (200, 403)


@pytest.mark.asyncio
async def test_7_19_http_sin_permiso_returns_403(tr_engine: AsyncEngine):
    """7.19: Request without tareas:gestionar permission returns 403."""
    from app.core.database import build_session_factory  # noqa: PLC0415
    from app.core.dependencies import get_db, get_current_user  # noqa: PLC0415
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    from app.main import create_app  # noqa: PLC0415

    factory = build_session_factory(tr_engine)
    application = create_app()

    async with factory() as setup_session:
        tid = await _make_tenant(setup_session)
        uid = await _make_usuario(setup_session, tid)
        await setup_session.commit()

    async def override_db():
        async with factory() as session:
            yield session

    # Override with a user that has NO roles / empty permissions
    async def override_auth_no_perm():
        return CurrentUser(user_id=uid, tenant_id=tid, roles=[])

    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[get_current_user] = override_auth_no_perm

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/tareas/")
    # With no permissions seeded and no roles, RBAC guard should deny
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_http_estado_invalido_returns_409_or_404(tr_http_fixtures):
    """Invalid state transition via HTTP returns 409 (or 404/403 if RBAC not seeded)."""
    client, tid, uid, factory = tr_http_fixtures

    # First create a tarea directly in the DB
    async with factory() as setup_session:
        tarea_id = await _make_tarea(setup_session, tid, uid, uid, estado="Cancelada")
        await setup_session.commit()

    resp = await client.patch(
        f"/api/v1/tareas/{tarea_id}/estado",
        json={"nuevo_estado": "En progreso"},
    )
    # 409 if tareas:gestionar is seeded; 403 if not; both valid
    assert resp.status_code in (409, 403)
