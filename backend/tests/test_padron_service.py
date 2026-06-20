"""
tests/test_padron_service.py — TDD tests for PadronService (tasks 4.1-4.12).

Tests cover:
  4.1 — preview does NOT persist any VersionPadron/EntradaPadron
  4.3 — confirmar creates activa=True and deactivates previous
  4.4 — confirmar encrypts email (persisted value ≠ plaintext)
  4.5 — email_hash match sets usuario_id; no match → NULL
  4.7 — confirmar emits PADRON_CARGAR audit event
  4.9 — ver_padron_activo returns decrypted email entries
  4.11 — vaciar only soft-deletes its scope; others unaffected

Requires TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import csv
import io
import os
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import build_engine, Base

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping padron service tests",
)

_TEST_KEY = "a" * 64


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def svc_engine() -> AsyncEngine:
    import app.models.tenant         # noqa: F401
    import app.models.user           # noqa: F401
    import app.models.rol            # noqa: F401
    import app.models.permiso        # noqa: F401
    import app.models.rol_permiso    # noqa: F401
    import app.models.usuario_rol    # noqa: F401
    import app.models.audit_log      # noqa: F401
    import app.models.carrera        # noqa: F401
    import app.models.cohorte        # noqa: F401
    import app.models.materia        # noqa: F401
    import app.models.usuario        # noqa: F401
    import app.models.asignacion     # noqa: F401
    import app.models.version_padron  # noqa: F401
    import app.models.entrada_padron  # noqa: F401
    import app.features.auth.models  # noqa: F401

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
async def svc_session(svc_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(svc_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# DB Helpers
# ---------------------------------------------------------------------------

async def _make_tenant(session: AsyncSession, suffix: str = "") -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(slug=f"ps-{uuid.uuid4().hex[:8]}{suffix}", nombre="PadronSvc Test", activo=True)
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


async def _make_materia(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.materia import Materia  # noqa: PLC0415
    m = Materia(tenant_id=tid, codigo=f"MAT_{uuid.uuid4().hex[:6]}", nombre="Mat Test")
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m.id


async def _make_cohorte(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.carrera import Carrera  # noqa: PLC0415
    from app.models.cohorte import Cohorte  # noqa: PLC0415
    c = Carrera(tenant_id=tid, codigo=f"CAR_{uuid.uuid4().hex[:6]}", nombre="Car")
    session.add(c)
    await session.flush()
    await session.refresh(c)
    cohorte = Cohorte(
        tenant_id=tid, carrera_id=c.id,
        nombre=f"COH_{uuid.uuid4().hex[:6]}", anio=2024, vig_desde=date.today(),
    )
    session.add(cohorte)
    await session.flush()
    await session.refresh(cohorte)
    return cohorte.id


async def _make_domain_usuario(session: AsyncSession, tid: uuid.UUID, email: str | None = None) -> tuple[uuid.UUID, str]:
    """Create a domain Usuario and return (id, plaintext_email)."""
    from app.models.usuario import Usuario  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415
    crypto = CryptoService(_TEST_KEY)
    if email is None:
        email = f"usr_{uuid.uuid4().hex[:8]}@example.com"
    u = Usuario(
        tenant_id=tid, nombre="Test", apellidos="User",
        email=crypto.encrypt(email),
        email_hash=crypto.hash_deterministic(email),
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u.id, email


async def _make_auth_user(session: AsyncSession, tid: uuid.UUID) -> uuid.UUID:
    from app.models.user import User  # noqa: PLC0415
    u = User(tenant_id=tid, email=f"au_{uuid.uuid4().hex[:8]}@test.com", password_hash="x")
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u.id


def _build_csv(rows: list[dict]) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["nombre", "apellidos", "email", "comision", "regional"])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def _make_service(session: AsyncSession, tenant_id: uuid.UUID):
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.services.audit_service import AuditService  # noqa: PLC0415
    from app.services.padron_service import PadronService  # noqa: PLC0415

    crypto = CryptoService(_TEST_KEY)
    audit_svc = AuditService(session=session, tenant_id=tenant_id)
    return PadronService(session=session, tenant_id=tenant_id, crypto=crypto, audit_svc=audit_svc)


def _make_current_user(user_id: uuid.UUID, tenant_id: uuid.UUID):
    from app.core.auth_context import CurrentUser  # noqa: PLC0415
    return CurrentUser(user_id=user_id, tenant_id=tenant_id, roles=[])


# ---------------------------------------------------------------------------
# Task 4.1 — preview does NOT persist
# ---------------------------------------------------------------------------

async def test_preview_no_persiste(svc_session: AsyncSession):
    """preview() returns parsed entries but does NOT create any DB rows."""
    from app.models.version_padron import VersionPadron  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    uid, _ = await _make_domain_usuario(svc_session, tid)
    await svc_session.commit()

    svc = _make_service(svc_session, tid)
    csv_data = _build_csv([
        {"nombre": "Ana", "apellidos": "García", "email": "ana@test.com", "comision": "A1", "regional": ""},
    ])

    result = await svc.preview(file_data=csv_data, content_type="text/csv")

    assert len(result.entradas) == 1
    assert result.total_errores == 0

    # Nothing persisted — no VersionPadron rows
    count = await svc_session.scalar(
        sa.select(sa.func.count()).select_from(VersionPadron).where(VersionPadron.tenant_id == tid)
    )
    assert count == 0


# ---------------------------------------------------------------------------
# Task 4.3 — confirmar creates version activa=True and deactivates previous
# ---------------------------------------------------------------------------

async def test_confirmar_deactiva_version_previa(svc_session: AsyncSession):
    """confirmar() creates a new active version and deactivates the previous one."""
    from app.models.version_padron import VersionPadron  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    uid, _ = await _make_domain_usuario(svc_session, tid)
    auth_uid = await _make_auth_user(svc_session, tid)
    materia = await _make_materia(svc_session, tid)
    cohorte = await _make_cohorte(svc_session, tid)
    await svc_session.commit()

    current_user = _make_current_user(uid, tid)
    svc = _make_service(svc_session, tid)
    csv_data = _build_csv([{"nombre": "A", "apellidos": "B", "email": "a@test.com", "comision": "", "regional": ""}])

    # First confirmar
    resp1 = await svc.confirmar(
        current_user=current_user, materia_id=materia, cohorte_id=cohorte,
        file_data=csv_data, content_type="text/csv",
    )
    await svc_session.commit()

    # Second confirmar — should deactivate the first
    resp2 = await svc.confirmar(
        current_user=current_user, materia_id=materia, cohorte_id=cohorte,
        file_data=csv_data, content_type="text/csv",
    )
    await svc_session.commit()

    # First version should be inactive
    from app.repositories.version_padron_repository import VersionPadronRepository  # noqa: PLC0415
    repo = VersionPadronRepository(session=svc_session, tenant_id=tid)
    versiones = await repo.list_versiones(materia, cohorte)
    assert len(versiones) == 2

    activas = [v for v in versiones if v.activa]
    assert len(activas) == 1
    assert activas[0].id == resp2.version.id


# ---------------------------------------------------------------------------
# Task 4.4 — confirmar encrypts email in DB
# ---------------------------------------------------------------------------

async def test_confirmar_cifra_email_en_db(svc_session: AsyncSession):
    """Email stored in DB is NOT the plaintext value."""
    from app.models.entrada_padron import EntradaPadron  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    uid, _ = await _make_domain_usuario(svc_session, tid)
    materia = await _make_materia(svc_session, tid)
    cohorte = await _make_cohorte(svc_session, tid)
    await svc_session.commit()

    plaintext_email = "test_cifrado@example.com"
    current_user = _make_current_user(uid, tid)
    svc = _make_service(svc_session, tid)
    csv_data = _build_csv([
        {"nombre": "X", "apellidos": "Y", "email": plaintext_email, "comision": "", "regional": ""}
    ])

    await svc.confirmar(
        current_user=current_user, materia_id=materia, cohorte_id=cohorte,
        file_data=csv_data, content_type="text/csv",
    )
    await svc_session.commit()

    # Read raw email from DB
    row = await svc_session.scalar(
        sa.select(EntradaPadron).where(EntradaPadron.tenant_id == tid)
    )
    assert row is not None
    assert row.email != plaintext_email, "Email must be stored as ciphertext, not plaintext"
    # The ciphertext should be decodable back to the plaintext
    from app.core.crypto import CryptoService  # noqa: PLC0415
    crypto = CryptoService(_TEST_KEY)
    assert crypto.decrypt(row.email) == plaintext_email


# ---------------------------------------------------------------------------
# Task 4.5 — email_hash match sets usuario_id; no match → NULL
# ---------------------------------------------------------------------------

async def test_confirmar_resuelve_usuario_id(svc_session: AsyncSession):
    """Email matching an existing Usuario sets usuario_id; unknown email → NULL."""
    tid = await _make_tenant(svc_session)
    known_email = "known@example.com"
    uid, _ = await _make_domain_usuario(svc_session, tid, email=known_email)
    materia = await _make_materia(svc_session, tid)
    cohorte = await _make_cohorte(svc_session, tid)
    await svc_session.commit()

    current_user = _make_current_user(uid, tid)
    svc = _make_service(svc_session, tid)
    csv_data = _build_csv([
        {"nombre": "Known", "apellidos": "User", "email": known_email, "comision": "", "regional": ""},
        {"nombre": "Unknown", "apellidos": "User", "email": "unknown_never@x.com", "comision": "", "regional": ""},
    ])

    resp = await svc.confirmar(
        current_user=current_user, materia_id=materia, cohorte_id=cohorte,
        file_data=csv_data, content_type="text/csv",
    )
    await svc_session.commit()

    from app.models.entrada_padron import EntradaPadron  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415
    crypto = CryptoService(_TEST_KEY)

    rows = await svc_session.scalars(
        sa.select(EntradaPadron).where(EntradaPadron.tenant_id == tid)
    )
    entries = list(rows)
    assert len(entries) == 2

    for e in entries:
        decrypted = crypto.decrypt(e.email)
        if decrypted == known_email:
            assert e.usuario_id == uid, "Known email must have usuario_id set"
        else:
            assert e.usuario_id is None, "Unknown email must have usuario_id = NULL"

    assert resp.entradas_sin_match == 1


# ---------------------------------------------------------------------------
# Task 4.7 — confirmar emits PADRON_CARGAR audit event
# ---------------------------------------------------------------------------

async def test_confirmar_emite_audit_padron_cargar(svc_session: AsyncSession):
    """confirmar() writes a PADRON_CARGAR audit log entry."""
    from app.models.audit_log import AuditLog  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    uid, _ = await _make_domain_usuario(svc_session, tid)
    materia = await _make_materia(svc_session, tid)
    cohorte = await _make_cohorte(svc_session, tid)
    await svc_session.commit()

    current_user = _make_current_user(uid, tid)
    svc = _make_service(svc_session, tid)
    csv_data = _build_csv([{"nombre": "A", "apellidos": "B", "email": "a@test.com", "comision": "", "regional": ""}])

    await svc.confirmar(
        current_user=current_user, materia_id=materia, cohorte_id=cohorte,
        file_data=csv_data, content_type="text/csv",
    )
    await svc_session.commit()

    audit_row = await svc_session.scalar(
        sa.select(AuditLog)
        .where(AuditLog.tenant_id == tid)
        .where(AuditLog.accion == "PADRON_CARGAR")
    )
    assert audit_row is not None
    assert audit_row.filas_afectadas == 1


# ---------------------------------------------------------------------------
# Task 4.9 — ver_padron_activo returns decrypted email entries
# ---------------------------------------------------------------------------

async def test_ver_padron_activo_devuelve_email_descifrado(svc_session: AsyncSession):
    """ver_padron_activo returns entries with plaintext email."""
    tid = await _make_tenant(svc_session)
    uid, _ = await _make_domain_usuario(svc_session, tid)
    materia = await _make_materia(svc_session, tid)
    cohorte = await _make_cohorte(svc_session, tid)
    await svc_session.commit()

    plaintext_email = "visible@test.com"
    current_user = _make_current_user(uid, tid)
    svc = _make_service(svc_session, tid)
    csv_data = _build_csv([
        {"nombre": "Visible", "apellidos": "User", "email": plaintext_email, "comision": "", "regional": ""}
    ])

    await svc.confirmar(
        current_user=current_user, materia_id=materia, cohorte_id=cohorte,
        file_data=csv_data, content_type="text/csv",
    )
    await svc_session.commit()

    entradas = await svc.ver_padron_activo(materia_id=materia, cohorte_id=cohorte)
    assert len(entradas) == 1
    assert entradas[0].email == plaintext_email


# ---------------------------------------------------------------------------
# Task 4.11 — vaciar only soft-deletes its scope
# ---------------------------------------------------------------------------

async def test_vaciar_scope_isolation(svc_session: AsyncSession):
    """vaciar(A, X) does NOT affect (B, X) or (A, Y)."""
    tid = await _make_tenant(svc_session)
    uid, _ = await _make_domain_usuario(svc_session, tid)
    materia_a = await _make_materia(svc_session, tid)
    materia_b = await _make_materia(svc_session, tid)
    cohorte_x = await _make_cohorte(svc_session, tid)
    cohorte_y = await _make_cohorte(svc_session, tid)
    await svc_session.commit()

    current_user = _make_current_user(uid, tid)
    svc = _make_service(svc_session, tid)
    csv_row = [{"nombre": "A", "apellidos": "B", "email": "a@test.com", "comision": "", "regional": ""}]

    for mat, coh in [(materia_a, cohorte_x), (materia_b, cohorte_x), (materia_a, cohorte_y)]:
        await svc.confirmar(
            current_user=current_user, materia_id=mat, cohorte_id=coh,
            file_data=_build_csv(csv_row), content_type="text/csv",
        )
    await svc_session.commit()

    # Vaciar only (A, X)
    eliminadas = await svc.vaciar(materia_id=materia_a, cohorte_id=cohorte_x)
    await svc_session.commit()

    assert eliminadas >= 1

    # (B, X) and (A, Y) must still have active versions
    bx = await svc.ver_padron_activo(materia_id=materia_b, cohorte_id=cohorte_x)
    ay = await svc.ver_padron_activo(materia_id=materia_a, cohorte_id=cohorte_y)
    ax = await svc.ver_padron_activo(materia_id=materia_a, cohorte_id=cohorte_x)

    assert len(bx) > 0, "(B, X) should still have entries"
    assert len(ay) > 0, "(A, Y) should still have entries"
    assert ax == [], "(A, X) should be empty after vaciar"
