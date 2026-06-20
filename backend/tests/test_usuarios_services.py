"""
tests/test_usuarios_services.py — TDD tests for UsuarioService and AsignacionService.

Group 9 tests (tasks 9.1–9.10): encryption, hashing, vigencia, validation.

Requires TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import os
import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import build_engine, Base

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping usuario service tests",
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
            await session.rollback()
            await session.close()


async def _make_tenant(session: AsyncSession, *, slug_prefix: str = "usrsvc") -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(
        slug=f"{slug_prefix}-{uuid.uuid4().hex[:8]}",
        nombre="UsuarioSvc Test Tenant",
        activo=True,
    )
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


def _make_crypto():
    from app.core.crypto import CryptoService  # noqa: PLC0415
    return CryptoService(_TEST_KEY)


def _make_usuario_svc(session: AsyncSession, tenant_id: uuid.UUID):
    from app.services.usuario_service import UsuarioService  # noqa: PLC0415
    return UsuarioService(session=session, tenant_id=tenant_id, crypto=_make_crypto())


def _make_asignacion_svc(session: AsyncSession, tenant_id: uuid.UUID):
    from app.services.asignacion_service import AsignacionService  # noqa: PLC0415
    return AsignacionService(session=session, tenant_id=tenant_id)


# ---------------------------------------------------------------------------
# Group 9: Service and business-rule tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_9_1_usuario_create_email_stored_as_ciphertext(svc_session: AsyncSession):
    """9.1 UsuarioService.create → email column stored differs from plaintext (encrypted)."""
    from app.repositories.usuario_repository import UsuarioRepository  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    svc = _make_usuario_svc(svc_session, tid)

    plaintext_email = "crypt@example.com"
    await svc.create(nombre="Test", apellidos="User", email=plaintext_email)

    # Fetch raw from DB
    repo = UsuarioRepository(session=svc_session, tenant_id=tid)
    all_usuarios = await repo.list()
    assert len(all_usuarios) == 1
    stored_email = all_usuarios[0].email

    assert stored_email != plaintext_email


@pytest.mark.asyncio
async def test_9_2_usuario_create_email_hash_is_hmac_not_plaintext(svc_session: AsyncSession):
    """9.2 UsuarioService.create → email_hash is HMAC of normalized email, not the email itself."""
    from app.repositories.usuario_repository import UsuarioRepository  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    svc = _make_usuario_svc(svc_session, tid)
    crypto = _make_crypto()

    plaintext_email = "  Hash@Example.COM  "
    normalized = "hash@example.com"
    expected_hash = crypto.hash_deterministic(normalized)

    await svc.create(nombre="Test", apellidos="User", email=plaintext_email)

    repo = UsuarioRepository(session=svc_session, tenant_id=tid)
    all_usuarios = await repo.list()
    assert len(all_usuarios) == 1
    stored_hash = all_usuarios[0].email_hash

    assert stored_hash == expected_hash
    assert stored_hash != plaintext_email
    assert len(stored_hash) == 64  # HMAC-SHA256 hex = 64 chars


@pytest.mark.asyncio
async def test_9_3_usuario_get_pii_decrypted_matches_original(svc_session: AsyncSession):
    """9.3 UsuarioService.get → PII fields decrypted in response match original create values."""
    tid = await _make_tenant(svc_session)
    svc = _make_usuario_svc(svc_session, tid)

    created = await svc.create(
        nombre="Ana",
        apellidos="García",
        email="ana@example.com",
        dni="87654321",
        cuil="27-87654321-5",
        cbu="0000003100087654321001",
        alias_cbu="ana.garcia.cbu",
    )

    fetched = await svc.get(created.id)
    assert fetched is not None
    assert fetched.email == "ana@example.com"
    assert fetched.dni == "87654321"
    assert fetched.cuil == "27-87654321-5"
    assert fetched.cbu == "0000003100087654321001"
    assert fetched.alias_cbu == "ana.garcia.cbu"


@pytest.mark.asyncio
async def test_9_4_usuario_create_dup_email_same_tenant_raises_value_error(svc_session: AsyncSession):
    """9.4 UsuarioService.create duplicate email same tenant → raises ValueError (router → 409)."""
    tid = await _make_tenant(svc_session)
    svc = _make_usuario_svc(svc_session, tid)

    await svc.create(nombre="First", apellidos="User", email="dup@example.com")

    with pytest.raises(ValueError, match="ya existe"):
        await svc.create(nombre="Second", apellidos="User", email="dup@example.com")


@pytest.mark.asyncio
async def test_9_5_usuario_create_dup_email_different_tenant_succeeds(svc_session: AsyncSession):
    """9.5 UsuarioService.create duplicate email different tenant → success (no conflict)."""
    tid_a = await _make_tenant(svc_session, slug_prefix="svc-a")
    tid_b = await _make_tenant(svc_session, slug_prefix="svc-b")

    svc_a = _make_usuario_svc(svc_session, tid_a)
    svc_b = _make_usuario_svc(svc_session, tid_b)

    await svc_a.create(nombre="UserA", apellidos="Tenant", email="shared@example.com")
    # Must not raise — different tenant
    result_b = await svc_b.create(nombre="UserB", apellidos="Tenant", email="shared@example.com")

    assert result_b.id is not None
    assert result_b.tenant_id == tid_b


@pytest.mark.asyncio
async def test_9_6_email_hash_not_in_usuario_response(svc_session: AsyncSession):
    """9.6 email_hash must not appear in any field of UsuarioResponse."""
    from app.schemas.usuario import UsuarioResponse  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    svc = _make_usuario_svc(svc_session, tid)
    crypto = _make_crypto()

    created_dto = await svc.create(nombre="Test", apellidos="Hash", email="nohash@example.com")
    response = UsuarioResponse.model_validate(created_dto)

    # email_hash must not be a field in UsuarioResponse
    response_dict = response.model_dump()
    assert "email_hash" not in response_dict

    # Also verify the model fields list does not include email_hash
    assert "email_hash" not in UsuarioResponse.model_fields


@pytest.mark.asyncio
async def test_9_7_asignacion_vigente_with_past_desde_future_hasta(svc_session: AsyncSession):
    """9.7 AsignacionService: desde past, hasta future → estado_vigencia='Vigente'."""
    from app.models.usuario import Usuario  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    crypto = _make_crypto()

    usuario = Usuario(
        tenant_id=tid,
        nombre="Test",
        apellidos="Vigente",
        email=crypto.encrypt("vigente@example.com"),
        email_hash=crypto.hash_deterministic("vigente@example.com"),
    )
    svc_session.add(usuario)
    await svc_session.flush()
    await svc_session.refresh(usuario)

    svc = _make_asignacion_svc(svc_session, tid)
    today = date.today()
    dto = await svc.create(
        usuario_id=usuario.id,
        rol="PROFESOR",
        desde=today - timedelta(days=10),
        hasta=today + timedelta(days=30),
    )

    assert dto.estado_vigencia == "Vigente"


@pytest.mark.asyncio
async def test_9_8_asignacion_vencida_with_past_hasta(svc_session: AsyncSession):
    """9.8 AsignacionService: hasta in the past → estado_vigencia='Vencida'."""
    from app.models.usuario import Usuario  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    crypto = _make_crypto()

    usuario = Usuario(
        tenant_id=tid,
        nombre="Test",
        apellidos="Vencida",
        email=crypto.encrypt("vencida@example.com"),
        email_hash=crypto.hash_deterministic("vencida@example.com"),
    )
    svc_session.add(usuario)
    await svc_session.flush()
    await svc_session.refresh(usuario)

    svc = _make_asignacion_svc(svc_session, tid)
    today = date.today()
    dto = await svc.create(
        usuario_id=usuario.id,
        rol="TUTOR",
        desde=today - timedelta(days=60),
        hasta=today - timedelta(days=10),  # past
    )

    assert dto.estado_vigencia == "Vencida"


@pytest.mark.asyncio
async def test_9_9_asignacion_vigente_with_null_hasta(svc_session: AsyncSession):
    """9.9 AsignacionService: hasta=None → estado_vigencia='Vigente' (open-ended)."""
    from app.models.usuario import Usuario  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    crypto = _make_crypto()

    usuario = Usuario(
        tenant_id=tid,
        nombre="Test",
        apellidos="OpenEnded",
        email=crypto.encrypt("open@example.com"),
        email_hash=crypto.hash_deterministic("open@example.com"),
    )
    svc_session.add(usuario)
    await svc_session.flush()
    await svc_session.refresh(usuario)

    svc = _make_asignacion_svc(svc_session, tid)
    today = date.today()
    dto = await svc.create(
        usuario_id=usuario.id,
        rol="COORDINADOR",
        desde=today - timedelta(days=5),
        hasta=None,
    )

    assert dto.estado_vigencia == "Vigente"


@pytest.mark.asyncio
async def test_9_10_asignacion_create_invalid_rol_raises_422(svc_session: AsyncSession):
    """9.10 AsignacionService.create with rol='INVALIDO' → raises HTTPException(422)."""
    from app.models.usuario import Usuario  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    crypto = _make_crypto()

    usuario = Usuario(
        tenant_id=tid,
        nombre="Test",
        apellidos="Invalid",
        email=crypto.encrypt("invalid@example.com"),
        email_hash=crypto.hash_deterministic("invalid@example.com"),
    )
    svc_session.add(usuario)
    await svc_session.flush()
    await svc_session.refresh(usuario)

    svc = _make_asignacion_svc(svc_session, tid)

    with pytest.raises(HTTPException) as exc_info:
        await svc.create(
            usuario_id=usuario.id,
            rol="INVALIDO",
            desde=date.today(),
        )

    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# Group 11: Roles in UsuarioResponse + empty-string normalization
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_11_1_usuario_response_includes_roles_from_asignacion(
    svc_session: AsyncSession,
):
    """11.1 UsuarioResponse.roles contains items from Asignacion."""
    from app.schemas.usuario import UsuarioResponse  # noqa: PLC0415
    from app.services.asignacion_service import AsignacionService  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    svc = _make_usuario_svc(svc_session, tid)

    created = await svc.create(
        nombre="Rol",
        apellidos="Test",
        email="roltest@example.com",
    )

    asig_svc = AsignacionService(session=svc_session, tenant_id=tid)
    today = date.today()
    await asig_svc.create(
        usuario_id=created.id,
        rol="PROFESOR",
        desde=today - timedelta(days=10),
        hasta=today + timedelta(days=30),
    )
    await asig_svc.create(
        usuario_id=created.id,
        rol="TUTOR",
        desde=today - timedelta(days=5),
        hasta=None,
    )

    fetched = await svc.get(created.id)
    assert fetched is not None
    assert len(fetched.roles) == 2

    rol_names = {r["rol"] for r in fetched.roles}
    assert "PROFESOR" in rol_names
    assert "TUTOR" in rol_names

    response = UsuarioResponse.model_validate(fetched)
    assert len(response.roles) == 2
    assert response.roles[0].rol in ("PROFESOR", "TUTOR")
    # vigencia computed correctly
    for r in response.roles:
        assert r.vigencia in ("Vigente", "Vencida")


@pytest.mark.asyncio
async def test_11_2_usuario_response_roles_empty_when_no_asignaciones(
    svc_session: AsyncSession,
):
    """11.2 UsuarioResponse.roles is empty list when user has no Asignacion."""
    from app.schemas.usuario import UsuarioResponse  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    svc = _make_usuario_svc(svc_session, tid)

    created = await svc.create(
        nombre="NoRole",
        apellidos="User",
        email="norole@example.com",
    )

    fetched = await svc.get(created.id)
    assert fetched is not None
    assert fetched.roles == []

    response = UsuarioResponse.model_validate(fetched)
    assert response.roles == []


@pytest.mark.asyncio
async def test_11_3_patch_with_empty_cbu_does_not_update_encrypted_field(
    svc_session: AsyncSession,
):
    """11.3 PATCH set cbu="" → normalized to None, encrypted field not changed."""
    from app.repositories.usuario_repository import UsuarioRepository  # noqa: PLC0415

    tid = await _make_tenant(svc_session)
    svc = _make_usuario_svc(svc_session, tid)

    created = await svc.create(
        nombre="Cbu",
        apellidos="Patch",
        email="cbu@example.com",
        cbu="0000003100087654321001",
    )
    assert created.cbu == "0000003100087654321001"

    # Update with empty string — should NOT change CBU
    updated = await svc.update(created.id, cbu="")
    assert updated is not None
    assert updated.cbu == "0000003100087654321001"

    # Verify raw DB still has ciphertext (not "") for cbu
    repo = UsuarioRepository(session=svc_session, tenant_id=tid)
    raw = await repo.get(created.id)
    assert raw is not None
    assert raw.cbu is not None
    assert raw.cbu != ""


@pytest.mark.asyncio
async def test_11_4_patch_with_empty_alias_cbu_does_not_update(
    svc_session: AsyncSession,
):
    """11.4 PATCH set alias_cbu="" → normalized to None, not updated."""
    tid = await _make_tenant(svc_session)
    svc = _make_usuario_svc(svc_session, tid)

    created = await svc.create(
        nombre="Alias",
        apellidos="Patch",
        email="alias@example.com",
        alias_cbu="mi.alias.cbu",
    )
    assert created.alias_cbu == "mi.alias.cbu"

    updated = await svc.update(created.id, alias_cbu="")
    assert updated is not None
    assert updated.alias_cbu == "mi.alias.cbu"
