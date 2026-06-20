"""
tests/test_encuentro_service.py — TDD integration tests for EncuentroService.

Tasks covered:
  4.1 crear_slot_recurrente with cant_semanas=4 → 4 Programado instancias
  4.2 bulk insert via repository
  4.3 TRIANGULATE: cant_semanas > 52 → DomainError; desalineada fecha_inicio
  4.4 RN-13 exlcusivity: both modes → DomainError; neither → DomainError
  4.5 REFACTOR: already split (helpers/service/guardia)
  5.1 crear_encuentro_unico → 1 instancia slot_id=NULL; missing fecha_unica → DomainError
  5.2 editar_instancia marks Realizado + video_url (RN-14)
  5.3 editar_instancia operates ONLY on instancia (not slot)
  5.4 TRIANGULATE: Cancelado keeps fecha/hora; meet_url / comentario edit
  5.5 (RBAC is tested in endpoint tests; service access control skipped here)
  6.1 generar_html_asignacion returns HTML fragment
  6.2 listar_admin_encuentros returns all tenant instancias; no cross-tenant leak

These tests require TEST_DATABASE_URL (real DB — no DB mocks per project rules).

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

import os
import uuid
from datetime import date, time

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import Base, build_engine
from app.models.instancia_encuentro import EstadoInstancia
from app.services.encuentro_service import DomainError, EncuentroService

_requires_db = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping encuentro service integration tests",
)

pytestmark = _requires_db


# ---------------------------------------------------------------------------
# Schema fixtures
# ---------------------------------------------------------------------------

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


@pytest_asyncio.fixture(scope="module")
async def encuentro_engine() -> AsyncEngine:
    import app.models.tenant            # noqa: F401
    import app.models.user              # noqa: F401
    import app.models.rol               # noqa: F401
    import app.models.permiso           # noqa: F401
    import app.models.rol_permiso       # noqa: F401
    import app.models.usuario_rol       # noqa: F401
    import app.models.audit_log         # noqa: F401
    import app.models.carrera           # noqa: F401
    import app.models.cohorte           # noqa: F401
    import app.models.materia           # noqa: F401
    import app.models.usuario           # noqa: F401
    import app.models.asignacion        # noqa: F401
    import app.models.version_padron    # noqa: F401
    import app.models.entrada_padron    # noqa: F401
    import app.models.umbral_materia    # noqa: F401
    import app.models.calificacion      # noqa: F401
    import app.models.slot_encuentro    # noqa: F401
    import app.models.instancia_encuentro  # noqa: F401
    import app.models.guardia           # noqa: F401
    import app.features.auth.models     # noqa: F401

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


@pytest_asyncio.fixture
async def encuentro_session(encuentro_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(encuentro_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

async def _seed_tenant(session: AsyncSession) -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(slug=f"test-{uuid.uuid4().hex[:8]}", nombre="Test Tenant", activo=True)
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _seed_materia(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    from app.models.materia import Materia  # noqa: PLC0415
    m = Materia(
        tenant_id=tenant_id,
        nombre="Algoritmos",
        codigo="ALG-01",
    )
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m.id


async def _seed_usuario(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    from app.models.usuario import Usuario  # noqa: PLC0415
    u = Usuario(
        tenant_id=tenant_id,
        nombre="Prof",
        apellido="Test",
        email=f"prof-{uuid.uuid4().hex[:6]}@test.com",
        legajo="L001",
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u.id


async def _seed_asignacion(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    usuario_id: uuid.UUID,
    materia_id: uuid.UUID,
) -> uuid.UUID:
    from app.models.asignacion import Asignacion  # noqa: PLC0415
    a = Asignacion(
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        rol="PROFESOR",
        materia_id=materia_id,
        desde=date(2024, 1, 1),
    )
    session.add(a)
    await session.flush()
    await session.refresh(a)
    return a.id


# ---------------------------------------------------------------------------
# Safety Net: no prior tests for this module — skip straight to RED
# ---------------------------------------------------------------------------

# Task 4.1 — RED+GREEN: crear_slot_recurrente generates 4 Programado instancias

@pytest.mark.asyncio
async def test_crear_slot_recurrente_genera_4_instancias(encuentro_session: AsyncSession):
    """Task 4.1 RED→GREEN: cant_semanas=4 → 4 InstanciaEncuentro in Programado state."""
    tenant_id = await _seed_tenant(encuentro_session)
    materia_id = await _seed_materia(encuentro_session, tenant_id)
    usuario_id = await _seed_usuario(encuentro_session, tenant_id)
    asignacion_id = await _seed_asignacion(
        encuentro_session, tenant_id, usuario_id, materia_id
    )

    svc = EncuentroService(session=encuentro_session, tenant_id=tenant_id)

    slot, instancias = await svc.crear_slot_recurrente(
        asignacion_id=asignacion_id,
        materia_id=materia_id,
        titulo="Clase semanal",
        dia_semana="Lunes",
        fecha_inicio=date(2024, 1, 1),
        cant_semanas=4,
        hora=time(10, 0),
        current_user_id=usuario_id,
        current_user_roles=["PROFESOR"],
    )

    assert slot.id is not None
    assert slot.tenant_id == tenant_id
    assert len(instancias) == 4
    for inst in instancias:
        assert inst.estado == EstadoInstancia.Programado
        assert inst.slot_id == slot.id
        assert inst.tenant_id == tenant_id


# Task 4.3 — TRIANGULATE: cant_semanas > 52 → DomainError

@pytest.mark.asyncio
async def test_crear_slot_cant_semanas_supera_maximo(encuentro_session: AsyncSession):
    """Task 4.3 TRIANGULATE: cant_semanas=53 → DomainError."""
    tenant_id = await _seed_tenant(encuentro_session)
    materia_id = await _seed_materia(encuentro_session, tenant_id)
    usuario_id = await _seed_usuario(encuentro_session, tenant_id)
    asignacion_id = await _seed_asignacion(
        encuentro_session, tenant_id, usuario_id, materia_id
    )

    svc = EncuentroService(session=encuentro_session, tenant_id=tenant_id)

    with pytest.raises(DomainError, match="cant_semanas"):
        await svc.crear_slot_recurrente(
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            titulo="Slot largo",
            dia_semana="Martes",
            fecha_inicio=date(2024, 1, 1),
            cant_semanas=53,
            hora=time(9, 0),
            current_user_id=usuario_id,
            current_user_roles=["PROFESOR"],
        )


# Task 4.3 — TRIANGULATE: desalineada fecha_inicio → dates correct

@pytest.mark.asyncio
async def test_crear_slot_fecha_inicio_desalineada(encuentro_session: AsyncSession):
    """Task 4.3 TRIANGULATE: fecha_inicio (Monday) + dia_semana=Miércoles → aligns to Wed."""
    tenant_id = await _seed_tenant(encuentro_session)
    materia_id = await _seed_materia(encuentro_session, tenant_id)
    usuario_id = await _seed_usuario(encuentro_session, tenant_id)
    asignacion_id = await _seed_asignacion(
        encuentro_session, tenant_id, usuario_id, materia_id
    )

    svc = EncuentroService(session=encuentro_session, tenant_id=tenant_id)

    # 2024-01-01 is Monday; Miércoles should start on 2024-01-03
    _, instancias = await svc.crear_slot_recurrente(
        asignacion_id=asignacion_id,
        materia_id=materia_id,
        titulo="Clase miércoles",
        dia_semana="Miércoles",
        fecha_inicio=date(2024, 1, 1),
        cant_semanas=2,
        hora=time(14, 0),
        current_user_id=usuario_id,
        current_user_roles=["PROFESOR"],
    )

    assert instancias[0].fecha == date(2024, 1, 3)
    assert instancias[1].fecha == date(2024, 1, 10)


# Task 4.4 — RED+GREEN: RN-13 exclusivity

@pytest.mark.asyncio
async def test_rn13_ambos_modos_simultaneos_error(encuentro_session: AsyncSession):
    """Task 4.4 RED→GREEN: cant_semanas > 0 AND fecha_unica → DomainError (RN-13)."""
    tenant_id = await _seed_tenant(encuentro_session)
    materia_id = await _seed_materia(encuentro_session, tenant_id)
    usuario_id = await _seed_usuario(encuentro_session, tenant_id)
    asignacion_id = await _seed_asignacion(
        encuentro_session, tenant_id, usuario_id, materia_id
    )

    svc = EncuentroService(session=encuentro_session, tenant_id=tenant_id)

    with pytest.raises(DomainError, match="RN-13"):
        await svc.crear_slot_recurrente(
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            titulo="Slot mixto",
            dia_semana="Lunes",
            fecha_inicio=date(2024, 1, 1),
            cant_semanas=4,
            hora=time(10, 0),
            fecha_unica=date(2024, 3, 15),  # both modes set!
            current_user_id=usuario_id,
            current_user_roles=["PROFESOR"],
        )


@pytest.mark.asyncio
async def test_rn13_ningun_modo_error():
    """Task 4.4 GREEN: neither mode set → DomainError (RN-13)."""
    # Pure function call: validar_modo_exclusivo accessible via static method
    with pytest.raises(DomainError, match="RN-13"):
        EncuentroService._validar_modo_exclusivo(cant_semanas=0, fecha_unica=None)


# Task 5.1 — crear_encuentro_unico (RN-13.2)

@pytest.mark.asyncio
async def test_crear_encuentro_unico_slot_id_null(encuentro_session: AsyncSession):
    """Task 5.1 RED→GREEN: unique encounter → 1 instancia with slot_id=NULL."""
    tenant_id = await _seed_tenant(encuentro_session)
    materia_id = await _seed_materia(encuentro_session, tenant_id)
    usuario_id = await _seed_usuario(encuentro_session, tenant_id)

    svc = EncuentroService(session=encuentro_session, tenant_id=tenant_id)

    instancia = await svc.crear_encuentro_unico(
        materia_id=materia_id,
        titulo="Clase de repaso único",
        fecha_unica=date(2024, 5, 20),
        hora=time(11, 0),
        meet_url="https://meet.example.com/repaso",
        current_user_id=usuario_id,
        current_user_roles=["PROFESOR"],
    )

    assert instancia.slot_id is None
    assert instancia.tenant_id == tenant_id
    assert instancia.fecha == date(2024, 5, 20)
    assert instancia.estado == EstadoInstancia.Programado


@pytest.mark.asyncio
async def test_crear_encuentro_unico_sin_fecha_unica_error(encuentro_session: AsyncSession):
    """Task 5.1 TRIANGULATE: missing fecha_unica → DomainError."""
    tenant_id = await _seed_tenant(encuentro_session)
    materia_id = await _seed_materia(encuentro_session, tenant_id)
    usuario_id = await _seed_usuario(encuentro_session, tenant_id)

    svc = EncuentroService(session=encuentro_session, tenant_id=tenant_id)

    with pytest.raises(DomainError, match="fecha_unica"):
        await svc.crear_encuentro_unico(
            materia_id=materia_id,
            titulo="Sin fecha",
            fecha_unica=None,  # type: ignore[arg-type]
            hora=time(11, 0),
            current_user_id=usuario_id,
            current_user_roles=["PROFESOR"],
        )


# Task 5.2 / 5.3 — editar_instancia (RN-14)

@pytest.mark.asyncio
async def test_editar_instancia_marca_realizado_video_url(encuentro_session: AsyncSession):
    """Task 5.2 RED→GREEN: editar_instancia marks Realizado + sets video_url."""
    tenant_id = await _seed_tenant(encuentro_session)
    materia_id = await _seed_materia(encuentro_session, tenant_id)
    usuario_id = await _seed_usuario(encuentro_session, tenant_id)
    asignacion_id = await _seed_asignacion(
        encuentro_session, tenant_id, usuario_id, materia_id
    )

    svc = EncuentroService(session=encuentro_session, tenant_id=tenant_id)

    _, instancias = await svc.crear_slot_recurrente(
        asignacion_id=asignacion_id,
        materia_id=materia_id,
        titulo="Slot para editar",
        dia_semana="Jueves",
        fecha_inicio=date(2024, 1, 4),
        cant_semanas=3,
        hora=time(16, 0),
        current_user_id=usuario_id,
        current_user_roles=["PROFESOR"],
    )

    target_id = instancias[0].id
    # Edit only the first instancia
    updated = await svc.editar_instancia(
        target_id,
        estado=EstadoInstancia.Realizado,
        video_url="https://drive.google.com/video/abc",
    )

    assert updated.estado == EstadoInstancia.Realizado
    assert updated.video_url == "https://drive.google.com/video/abc"


@pytest.mark.asyncio
async def test_editar_instancia_no_toca_slot_ni_hermanas(encuentro_session: AsyncSession):
    """Task 5.3 GREEN: editing one instancia leaves slot + siblings unchanged (RN-14)."""
    from app.repositories.instancia_encuentro_repository import (  # noqa: PLC0415
        InstanciaEncuentroRepository,
    )
    from app.repositories.slot_encuentro_repository import (  # noqa: PLC0415
        SlotEncuentroRepository,
    )

    tenant_id = await _seed_tenant(encuentro_session)
    materia_id = await _seed_materia(encuentro_session, tenant_id)
    usuario_id = await _seed_usuario(encuentro_session, tenant_id)
    asignacion_id = await _seed_asignacion(
        encuentro_session, tenant_id, usuario_id, materia_id
    )

    svc = EncuentroService(session=encuentro_session, tenant_id=tenant_id)

    slot, instancias = await svc.crear_slot_recurrente(
        asignacion_id=asignacion_id,
        materia_id=materia_id,
        titulo="Slot RN-14 test",
        dia_semana="Viernes",
        fecha_inicio=date(2024, 2, 2),
        cant_semanas=3,
        hora=time(15, 0),
        current_user_id=usuario_id,
        current_user_roles=["PROFESOR"],
    )

    original_slot_titulo = slot.titulo
    sibling_ids = [inst.id for inst in instancias[1:]]

    # Edit only the first instancia
    await svc.editar_instancia(
        instancias[0].id,
        estado=EstadoInstancia.Cancelado,
    )

    # Slot must remain unchanged
    slot_repo = SlotEncuentroRepository(
        session=encuentro_session, tenant_id=tenant_id
    )
    slot_after = await slot_repo.get(slot.id)
    assert slot_after is not None
    assert slot_after.titulo == original_slot_titulo

    # Sibling instancias must still be Programado
    inst_repo = InstanciaEncuentroRepository(
        session=encuentro_session, tenant_id=tenant_id
    )
    for sib_id in sibling_ids:
        sib = await inst_repo.get(sib_id)
        assert sib is not None
        assert sib.estado == EstadoInstancia.Programado


# Task 5.4 — TRIANGULATE: Cancelado, comentario

@pytest.mark.asyncio
async def test_editar_instancia_cancelado_conserva_fecha_hora(
    encuentro_session: AsyncSession,
):
    """Task 5.4 TRIANGULATE: transition to Cancelado keeps fecha/hora intact."""
    tenant_id = await _seed_tenant(encuentro_session)
    materia_id = await _seed_materia(encuentro_session, tenant_id)
    usuario_id = await _seed_usuario(encuentro_session, tenant_id)

    svc = EncuentroService(session=encuentro_session, tenant_id=tenant_id)

    instancia = await svc.crear_encuentro_unico(
        materia_id=materia_id,
        titulo="Clase a cancelar",
        fecha_unica=date(2024, 6, 10),
        hora=time(9, 0),
        current_user_id=usuario_id,
        current_user_roles=["PROFESOR"],
    )

    updated = await svc.editar_instancia(
        instancia.id,
        estado=EstadoInstancia.Cancelado,
        comentario="Docente ausente",
    )

    assert updated.estado == EstadoInstancia.Cancelado
    assert updated.fecha == date(2024, 6, 10)  # unchanged
    assert updated.hora == time(9, 0)          # unchanged
    assert updated.comentario == "Docente ausente"


# Task 6.1 — generar_html_asignacion

@pytest.mark.asyncio
async def test_generar_html_asignacion_fragmento(encuentro_session: AsyncSession):
    """Task 6.1 RED→GREEN: generar_html_asignacion returns HTML fragment."""
    tenant_id = await _seed_tenant(encuentro_session)
    materia_id = await _seed_materia(encuentro_session, tenant_id)
    usuario_id = await _seed_usuario(encuentro_session, tenant_id)

    svc = EncuentroService(session=encuentro_session, tenant_id=tenant_id)

    await svc.crear_encuentro_unico(
        materia_id=materia_id,
        titulo="Clase HTML test",
        fecha_unica=date(2024, 4, 15),
        hora=time(10, 0),
        meet_url="https://meet.google.com/test",
        current_user_id=usuario_id,
        current_user_roles=["PROFESOR"],
    )

    html = await svc.generar_html_asignacion(materia_id)

    assert "<div" in html
    assert "Clase HTML test" in html
    assert "meet.google.com" in html


# Task 6.2 — listar_admin_encuentros (tenant isolation)

@pytest.mark.asyncio
async def test_listar_admin_encuentros_no_devuelve_otro_tenant(
    encuentro_session: AsyncSession,
):
    """Task 6.2 RED→GREEN: listar_admin returns only this tenant's instancias."""
    tenant_a = await _seed_tenant(encuentro_session)
    tenant_b = await _seed_tenant(encuentro_session)

    materia_a = await _seed_materia(encuentro_session, tenant_a)
    materia_b = await _seed_materia(encuentro_session, tenant_b)
    usuario_a = await _seed_usuario(encuentro_session, tenant_a)
    usuario_b = await _seed_usuario(encuentro_session, tenant_b)

    svc_a = EncuentroService(session=encuentro_session, tenant_id=tenant_a)
    svc_b = EncuentroService(session=encuentro_session, tenant_id=tenant_b)

    await svc_a.crear_encuentro_unico(
        materia_id=materia_a,
        titulo="Tenant A encounter",
        fecha_unica=date(2024, 7, 1),
        hora=time(8, 0),
        current_user_id=usuario_a,
        current_user_roles=["PROFESOR"],
    )
    await svc_b.crear_encuentro_unico(
        materia_id=materia_b,
        titulo="Tenant B encounter",
        fecha_unica=date(2024, 7, 2),
        hora=time(9, 0),
        current_user_id=usuario_b,
        current_user_roles=["PROFESOR"],
    )

    instancias_a = await svc_a.listar_admin_encuentros()

    # Tenant A can only see its own instancias
    tenant_ids_returned = {str(i.tenant_id) for i in instancias_a}
    assert str(tenant_a) in tenant_ids_returned
    assert str(tenant_b) not in tenant_ids_returned
