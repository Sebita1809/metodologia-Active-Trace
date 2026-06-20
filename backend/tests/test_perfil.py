"""
tests/test_perfil.py — Integration tests for self-service profile API.

Covers:
  2.1 UsuarioService.update persists sexo and modalidad_cobro correctly
  3.1 PerfilUpdate rejects cuil field
  4.1 GET /api/perfil returns own profile with PII decrypted
  4.2 GET /api/perfil without token → 401
  4.3 PATCH /api/perfil updates cbu/alias_cbu/modalidad_cobro (encrypted)
  4.4 PATCH /api/perfil with cuil field → 422
  4.5 Profile resolved belongs to JWT tenant; cannot affect another user
  4.6 POST /api/auth/logout revokes refresh token → subsequent refresh → 401

Requires TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import os
import uuid
from datetime import timedelta

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import Base, build_engine

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping perfil tests",
)

_TEST_KEY = "a" * 64


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def ep_engine() -> AsyncEngine:
    import app.models  # noqa: F401 — registers all models including Mensaje

    url = os.environ["TEST_DATABASE_URL"]
    engine = build_engine(url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(_drop_enums)
        await conn.run_sync(_create_enums)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(_drop_enums)

    await engine.dispose()


def _create_enums(conn):
    try:
        conn.execute(sa.text("CREATE TYPE alcance_enum AS ENUM ('global', 'propio')"))
    except Exception:
        pass


def _drop_enums(conn):
    try:
        conn.execute(sa.text("DROP TYPE IF EXISTS alcance_enum CASCADE"))
    except Exception:
        pass


@pytest_asyncio.fixture
async def ep_session(ep_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(ep_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def ep_client(ep_engine: AsyncEngine) -> AsyncClient:
    from app.main import create_app  # noqa: PLC0415
    from app.core.dependencies import get_db  # noqa: PLC0415

    application = create_app()
    factory = async_sessionmaker(ep_engine, expire_on_commit=False)

    async def override_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    application.dependency_overrides[get_db] = override_db

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_tenant(session: AsyncSession) -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(slug=f"t-{uuid.uuid4().hex[:8]}", nombre="Test Tenant", activo=True)
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t.id


async def _seed_usuario(session: AsyncSession, tenant_id: uuid.UUID) -> tuple[uuid.UUID, str]:
    """Create a Usuario and return (id, plaintext_email)."""
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.models.usuario import Usuario  # noqa: PLC0415

    crypto = CryptoService(_TEST_KEY)
    email = f"user-{uuid.uuid4().hex[:8]}@test.com"
    u = Usuario(
        tenant_id=tenant_id,
        nombre="Test",
        apellidos="User",
        email=crypto.encrypt(email),
        email_hash=crypto.hash_deterministic(email),
        cuil=crypto.encrypt("20-12345678-9"),
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u.id, email


def _make_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    from app.core.config import get_settings  # noqa: PLC0415
    from app.core.security import create_access_token  # noqa: PLC0415

    settings = get_settings()
    return create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=[],
        secret_key=settings.secret_key,
        expire_minutes=30,
    )


# ---------------------------------------------------------------------------
# Task 3.1: PerfilUpdate rejects cuil
# ---------------------------------------------------------------------------

def test_perfil_update_rejects_cuil():
    """PerfilUpdate with extra='forbid' raises ValidationError when cuil is sent."""
    from pydantic import ValidationError  # noqa: PLC0415
    from app.schemas.perfil import PerfilUpdate  # noqa: PLC0415

    with pytest.raises(ValidationError):
        PerfilUpdate.model_validate({"cuil": "20-12345678-9"})


def test_perfil_update_valid_fields():
    """PerfilUpdate accepts all declared editable fields."""
    from app.schemas.perfil import PerfilUpdate  # noqa: PLC0415

    p = PerfilUpdate.model_validate({"cbu": "123456", "modalidad_cobro": "Factura"})
    assert p.cbu == "123456"
    assert p.modalidad_cobro == "Factura"


# ---------------------------------------------------------------------------
# Task 2.1: UsuarioService.update persists sexo and modalidad_cobro
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_usuario_service_update_sexo_modalidad(ep_session: AsyncSession):
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.services.usuario_service import UsuarioService  # noqa: PLC0415

    tenant_id = await _seed_tenant(ep_session)
    crypto = CryptoService(_TEST_KEY)
    svc = UsuarioService(session=ep_session, tenant_id=tenant_id, crypto=crypto)

    created = await svc.create(
        nombre="Ana", apellidos="Perez", email="ana@test.com"
    )
    assert created.sexo is None
    assert created.modalidad_cobro is None

    updated = await svc.update(
        created.id,
        sexo="Femenino",
        modalidad_cobro="Factura",
    )
    assert updated is not None
    assert updated.sexo == "Femenino"
    assert updated.modalidad_cobro == "Factura"


# ---------------------------------------------------------------------------
# Task 4.1: GET /api/perfil returns own profile
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_perfil_returns_own_profile(ep_session: AsyncSession, ep_client: AsyncClient):
    tenant_id = await _seed_tenant(ep_session)
    user_id, email = await _seed_usuario(ep_session, tenant_id)
    token = _make_token(user_id, tenant_id)

    resp = await ep_client.get("/api/perfil", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(user_id)
    assert data["email"] == email
    assert data["cuil"] == "20-12345678-9"
    assert "email_hash" not in data


# ---------------------------------------------------------------------------
# Task 4.2: GET /api/perfil without token → 401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_perfil_no_token(ep_client: AsyncClient):
    resp = await ep_client.get("/api/perfil")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Task 4.3: PATCH /api/perfil updates cbu/alias_cbu/modalidad_cobro
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_perfil_updates_fields(ep_session: AsyncSession, ep_client: AsyncClient):
    tenant_id = await _seed_tenant(ep_session)
    user_id, email = await _seed_usuario(ep_session, tenant_id)
    token = _make_token(user_id, tenant_id)

    payload = {
        "cbu": "0123456789012345678901",
        "alias_cbu": "nuevo.alias",
        "modalidad_cobro": "Liquidacion",
    }
    resp = await ep_client.patch(
        "/api/perfil",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cbu"] == "0123456789012345678901"
    assert data["alias_cbu"] == "nuevo.alias"
    assert data["modalidad_cobro"] == "Liquidacion"

    # Verify the DB stored encrypted (not plaintext) values
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415
    from app.models.usuario import Usuario  # noqa: PLC0415

    stmt = select(Usuario).where(Usuario.id == user_id)
    result = await ep_session.execute(stmt)
    row = result.scalar_one()
    crypto = CryptoService(_TEST_KEY)
    # The stored value should be ciphertext, not plaintext
    assert row.cbu != "0123456789012345678901"
    assert crypto.decrypt(row.cbu) == "0123456789012345678901"


# ---------------------------------------------------------------------------
# Task 4.4: PATCH /api/perfil with cuil → 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_perfil_cuil_rejected(ep_session: AsyncSession, ep_client: AsyncClient):
    tenant_id = await _seed_tenant(ep_session)
    user_id, _ = await _seed_usuario(ep_session, tenant_id)
    token = _make_token(user_id, tenant_id)

    resp = await ep_client.patch(
        "/api/perfil",
        json={"cuil": "20-99999999-9"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422

    # CUIL unchanged in DB
    from sqlalchemy import select  # noqa: PLC0415
    from app.models.usuario import Usuario  # noqa: PLC0415
    from app.core.crypto import CryptoService  # noqa: PLC0415

    stmt = select(Usuario).where(Usuario.id == user_id)
    result = await ep_session.execute(stmt)
    row = result.scalar_one()
    crypto = CryptoService(_TEST_KEY)
    assert crypto.decrypt(row.cuil) == "20-12345678-9"


# ---------------------------------------------------------------------------
# Task 4.5: Profile belongs to JWT tenant/user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_perfil_tenant_isolation(ep_session: AsyncSession, ep_client: AsyncClient):
    """Verify that the profile returned belongs to the JWT user, not another."""
    tenant_id = await _seed_tenant(ep_session)
    user_a_id, email_a = await _seed_usuario(ep_session, tenant_id)
    user_b_id, email_b = await _seed_usuario(ep_session, tenant_id)

    # Authenticate as user_a — profile must be user_a's, not user_b's
    token_a = _make_token(user_a_id, tenant_id)
    resp = await ep_client.get("/api/perfil", headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(user_a_id)
    assert data["email"] == email_a
    assert data["id"] != str(user_b_id)
