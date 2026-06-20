"""
tests/test_usuarios_modelos.py — TDD tests for Usuario and Asignacion models and repos.

Group 8 tests (tasks 8.1–8.7): models, constraints, soft-delete, tenant isolation.

Requires TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import os
import uuid
from datetime import date

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import build_engine, Base

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping usuario model tests",
)

# A fixed test encryption key (64 hex chars = 32 bytes)
_TEST_KEY = "a" * 64


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def usr_engine() -> AsyncEngine:
    """Function-scoped engine with the full schema including usuario tables."""
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
async def usr_session(usr_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(usr_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


async def _make_tenant(session: AsyncSession, *, slug_prefix: str = "usr") -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(
        slug=f"{slug_prefix}-{uuid.uuid4().hex[:8]}",
        nombre="Usuario Test Tenant",
        activo=True,
    )
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t.id


def _make_crypto():
    from app.core.crypto import CryptoService  # noqa: PLC0415
    return CryptoService(_TEST_KEY)


# ---------------------------------------------------------------------------
# Group 8: Model and repository tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_8_1_create_usuario_persists_with_defaults(usr_session: AsyncSession):
    """8.1 Create Usuario → persists with estado='Activo'; email column stores ciphertext."""
    from app.models.usuario import Usuario  # noqa: PLC0415
    from app.repositories.usuario_repository import UsuarioRepository  # noqa: PLC0415

    tid = await _make_tenant(usr_session)
    crypto = _make_crypto()
    repo = UsuarioRepository(session=usr_session, tenant_id=tid)

    plaintext_email = "test@example.com"
    email_hash = crypto.hash_deterministic(plaintext_email)

    usuario = Usuario(
        tenant_id=tid,
        nombre="Juan",
        apellidos="Pérez",
        email=crypto.encrypt(plaintext_email),
        email_hash=email_hash,
    )
    created = await repo.create(usuario)

    assert created.id is not None
    assert created.tenant_id == tid
    assert created.estado == "Activo"
    assert created.deleted_at is None
    # email column must NOT equal the plaintext
    assert created.email != plaintext_email
    # Must be decryptable
    assert crypto.decrypt(created.email) == plaintext_email


@pytest.mark.asyncio
async def test_8_2_unique_email_hash_per_tenant_raises_integrity_error(usr_session: AsyncSession):
    """8.2 UNIQUE(tenant_id, email_hash) → second insert with same hash raises IntegrityError."""
    from app.models.usuario import Usuario  # noqa: PLC0415

    tid = await _make_tenant(usr_session)
    crypto = _make_crypto()
    email_hash = crypto.hash_deterministic("dup@example.com")

    u1 = Usuario(
        tenant_id=tid,
        nombre="Juan",
        apellidos="Uno",
        email=crypto.encrypt("dup@example.com"),
        email_hash=email_hash,
    )
    usr_session.add(u1)
    await usr_session.flush()

    u2 = Usuario(
        tenant_id=tid,
        nombre="Pedro",
        apellidos="Dos",
        email=crypto.encrypt("dup@example.com"),
        email_hash=email_hash,
    )
    usr_session.add(u2)

    with pytest.raises(IntegrityError):
        await usr_session.flush()

    await usr_session.rollback()


@pytest.mark.asyncio
async def test_8_3_soft_delete_usuario(usr_session: AsyncSession):
    """8.3 Soft delete Usuario → deleted_at set; not returned by repo.list()."""
    from app.models.usuario import Usuario  # noqa: PLC0415
    from app.repositories.usuario_repository import UsuarioRepository  # noqa: PLC0415

    tid = await _make_tenant(usr_session)
    crypto = _make_crypto()
    repo = UsuarioRepository(session=usr_session, tenant_id=tid)

    usuario = Usuario(
        tenant_id=tid,
        nombre="Para",
        apellidos="Borrar",
        email=crypto.encrypt("del@example.com"),
        email_hash=crypto.hash_deterministic("del@example.com"),
    )
    created = await repo.create(usuario)
    assert created.deleted_at is None

    deleted = await repo.soft_delete(created.id)
    assert deleted is True

    # Should not appear in list
    all_usuarios = await repo.list()
    ids = [u.id for u in all_usuarios]
    assert created.id not in ids

    # deleted_at should be set via including-deleted query
    stmt = repo._base_query_including_deleted().where(
        __import__("app.models.usuario", fromlist=["Usuario"]).Usuario.id == created.id
    )
    result = await usr_session.execute(stmt)
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.deleted_at is not None


@pytest.mark.asyncio
async def test_8_4_usuario_repr_does_not_expose_pii(usr_session: AsyncSession):
    """8.4 Usuario.__repr__ must not expose PII fields."""
    from app.models.usuario import Usuario  # noqa: PLC0415

    tid = await _make_tenant(usr_session)
    crypto = _make_crypto()

    pii_email = "secret@example.com"
    pii_dni = "12345678"
    pii_cuil = "20-12345678-9"
    pii_cbu = "0000003100012345678901"
    pii_alias = "mi.alias.cbu"

    usuario = Usuario(
        tenant_id=tid,
        nombre="Secreto",
        apellidos="Total",
        email=crypto.encrypt(pii_email),
        email_hash=crypto.hash_deterministic(pii_email),
        dni=crypto.encrypt(pii_dni),
        cuil=crypto.encrypt(pii_cuil),
        cbu=crypto.encrypt(pii_cbu),
        alias_cbu=crypto.encrypt(pii_alias),
    )
    usr_session.add(usuario)
    await usr_session.flush()
    await usr_session.refresh(usuario)

    repr_str = repr(usuario)

    # Repr must NOT contain PII values (plaintext or as visible ciphertext label)
    assert pii_email not in repr_str
    assert pii_dni not in repr_str
    assert pii_cuil not in repr_str
    assert pii_cbu not in repr_str
    assert pii_alias not in repr_str
    # Should only expose id and tenant_id
    assert "id=" in repr_str
    assert "tenant_id=" in repr_str


@pytest.mark.asyncio
async def test_8_5_create_asignacion_persists_with_defaults(usr_session: AsyncSession):
    """8.5 Create Asignacion → persists with FK to Usuario, comisiones=[] by default, responsable_id nullable."""
    from app.models.usuario import Usuario  # noqa: PLC0415
    from app.models.asignacion import Asignacion  # noqa: PLC0415
    from app.repositories.asignacion_repository import AsignacionRepository  # noqa: PLC0415

    tid = await _make_tenant(usr_session)
    crypto = _make_crypto()

    usuario = Usuario(
        tenant_id=tid,
        nombre="Docente",
        apellidos="Test",
        email=crypto.encrypt("docente@example.com"),
        email_hash=crypto.hash_deterministic("docente@example.com"),
    )
    usr_session.add(usuario)
    await usr_session.flush()
    await usr_session.refresh(usuario)

    repo = AsignacionRepository(session=usr_session, tenant_id=tid)
    asignacion = Asignacion(
        tenant_id=tid,
        usuario_id=usuario.id,
        rol="PROFESOR",
        desde=date(2024, 3, 1),
    )
    created = await repo.create(asignacion)

    assert created.id is not None
    assert created.usuario_id == usuario.id
    assert created.responsable_id is None
    assert created.comisiones == [] or created.comisiones is None or created.comisiones == []
    assert created.deleted_at is None


@pytest.mark.asyncio
async def test_8_6_asignacion_self_reference_responsable(usr_session: AsyncSession):
    """8.6 Asignacion with responsable_id (self-ref) → persists correctly."""
    from app.models.usuario import Usuario  # noqa: PLC0415
    from app.models.asignacion import Asignacion  # noqa: PLC0415
    from app.repositories.asignacion_repository import AsignacionRepository  # noqa: PLC0415

    tid = await _make_tenant(usr_session)
    crypto = _make_crypto()

    responsable = Usuario(
        tenant_id=tid,
        nombre="Coordinador",
        apellidos="Test",
        email=crypto.encrypt("coord@example.com"),
        email_hash=crypto.hash_deterministic("coord@example.com"),
    )
    docente = Usuario(
        tenant_id=tid,
        nombre="Docente",
        apellidos="Test",
        email=crypto.encrypt("doc@example.com"),
        email_hash=crypto.hash_deterministic("doc@example.com"),
    )
    usr_session.add_all([responsable, docente])
    await usr_session.flush()
    await usr_session.refresh(responsable)
    await usr_session.refresh(docente)

    repo = AsignacionRepository(session=usr_session, tenant_id=tid)
    asignacion = Asignacion(
        tenant_id=tid,
        usuario_id=docente.id,
        rol="TUTOR",
        desde=date(2024, 3, 1),
        responsable_id=responsable.id,
    )
    created = await repo.create(asignacion)

    assert created.responsable_id == responsable.id
    assert created.usuario_id == docente.id


@pytest.mark.asyncio
async def test_8_7_usuario_repo_tenant_isolation(usr_session: AsyncSession):
    """8.7 UsuarioRepository scoped to tenant A does not return usuarios from tenant B."""
    from app.models.usuario import Usuario  # noqa: PLC0415
    from app.repositories.usuario_repository import UsuarioRepository  # noqa: PLC0415

    tid_a = await _make_tenant(usr_session, slug_prefix="usr-a")
    tid_b = await _make_tenant(usr_session, slug_prefix="usr-b")
    crypto = _make_crypto()

    u_a = Usuario(
        tenant_id=tid_a,
        nombre="Solo",
        apellidos="TenantA",
        email=crypto.encrypt("only_a@example.com"),
        email_hash=crypto.hash_deterministic("only_a@example.com"),
    )
    u_b = Usuario(
        tenant_id=tid_b,
        nombre="Solo",
        apellidos="TenantB",
        email=crypto.encrypt("only_b@example.com"),
        email_hash=crypto.hash_deterministic("only_b@example.com"),
    )
    usr_session.add_all([u_a, u_b])
    await usr_session.flush()
    await usr_session.refresh(u_a)
    await usr_session.refresh(u_b)

    repo_a = UsuarioRepository(session=usr_session, tenant_id=tid_a)
    results = await repo_a.list()
    ids = [u.id for u in results]

    assert u_a.id in ids
    assert u_b.id not in ids
