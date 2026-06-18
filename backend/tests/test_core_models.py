"""Tests for core-models-y-tenancy: BaseModel, Tenant, BaseRepository, AESCipher.

Tasks 7.6–7.8 are pure unit tests (no DB).
Tasks 7.1–7.5, 7.9–7.11 require a real PostgreSQL.
"""

import os
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AESCipher
from app.models.base import BaseModel
from app.models.tenant import Tenant, TenantEstado
from app.repositories.base import BaseRepository

# ── DB availability check ──────────────────────────────────
_HAS_REAL_DB = bool(os.getenv("_TEST_DB_AVAILABLE")) or os.getenv("CI")
requires_db = pytest.mark.skipif(
    not _HAS_REAL_DB,
    reason="No real PostgreSQL available — set _TEST_DB_AVAILABLE=1 or CI=1 with a live DATABASE_URL",
)

# ═══════════════════════════════════════════════════════════
# AESCipher — pure unit tests (no DB needed)
# ═══════════════════════════════════════════════════════════


class TestAESCipher:
    """7.6, 7.7, 7.8 — AESCipher encryption / decryption."""

    def test_aes_round_trip(self) -> None:
        """7.6 — encrypt then decrypt returns original plaintext."""
        plain = "Hello, activia-trace! 123"
        encrypted = AESCipher.encrypt(plain)
        assert encrypted != plain
        decrypted = AESCipher.decrypt(encrypted)
        assert decrypted == plain

    def test_aes_empty_string(self) -> None:
        """7.7 — empty string round-trips correctly."""
        encrypted = AESCipher.encrypt("")
        assert AESCipher.decrypt(encrypted) == ""

    def test_aes_none_raises(self) -> None:
        """7.7 — encrypt / decrypt with None raises ValueError."""
        with pytest.raises(ValueError, match="None"):
            AESCipher.encrypt(None)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="None"):
            AESCipher.decrypt(None)  # type: ignore[arg-type]

    def test_aes_tampered_ciphertext(self) -> None:
        """7.8 — corrupted ciphertext raises on decrypt."""
        encrypted = AESCipher.encrypt("secret data")
        corrupted = encrypted[:-1] + ("X" if encrypted[-1] != "X" else "Y")
        with pytest.raises(Exception):
            AESCipher.decrypt(corrupted)


# ═══════════════════════════════════════════════════════════
# BaseModel mixin
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
@requires_db
async def test_base_model_has_columns(db_session: AsyncSession) -> None:
    """7.2 — Tenant (via BaseModel) has id, tenant_id, created_at,
    updated_at, deleted_at. UUID is auto-generated, timestamps are
    timezone-aware."""
    tenant = Tenant(nombre="Column Test", codigo="COLUMNS")
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    assert isinstance(tenant.id, uuid.UUID)
    assert tenant.tenant_id is None
    assert tenant.created_at is not None
    assert tenant.created_at.tzinfo is not None
    assert tenant.updated_at is not None
    assert tenant.updated_at.tzinfo is not None
    assert tenant.deleted_at is None


@pytest.mark.asyncio
@requires_db
async def test_base_model_updated_at_changes(db_session: AsyncSession) -> None:
    """7.2 — updated_at advances after a field mutation + commit."""
    tenant = Tenant(nombre="Initial", codigo="UPDATED_AT")
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    original = tenant.updated_at
    tenant.nombre = "Changed"
    await db_session.commit()
    await db_session.refresh(tenant)

    assert tenant.updated_at > original


# ═══════════════════════════════════════════════════════════
# Tenant model
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
@requires_db
async def test_tenant_create(db_session: AsyncSession) -> None:
    """7.3 — create Tenant with nombre, codigo; default estado=ACTIVO."""
    tenant = Tenant(nombre="Test Tenant", codigo="CREATE_TENANT")
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    assert tenant.nombre == "Test Tenant"
    assert tenant.codigo == "CREATE_TENANT"
    assert tenant.estado == TenantEstado.ACTIVO
    assert tenant.tenant_id is None


@pytest.mark.asyncio
@requires_db
async def test_tenant_unique_code(db_session: AsyncSession) -> None:
    """7.3 — duplicate codigo raises IntegrityError."""
    tenant1 = Tenant(nombre="First", codigo="UNIQUE_CODE")
    db_session.add(tenant1)
    await db_session.commit()

    tenant2 = Tenant(nombre="Second", codigo="UNIQUE_CODE")
    db_session.add(tenant2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    # clean up the original so subsequent runs don't conflict
    await db_session.execute(
        text("DELETE FROM tenant WHERE codigo = 'UNIQUE_CODE'")
    )
    await db_session.commit()


@pytest.mark.asyncio
@requires_db
async def test_tenant_deactivate(db_session: AsyncSession) -> None:
    """7.3 — change estado from ACTIVO to INACTIVO."""
    tenant = Tenant(nombre="Active", codigo="DEACTIVATE")
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    assert tenant.estado == TenantEstado.ACTIVO

    tenant.estado = TenantEstado.INACTIVO
    await db_session.commit()
    await db_session.refresh(tenant)
    assert tenant.estado == TenantEstado.INACTIVO


# ═══════════════════════════════════════════════════════════
# Multi-tenant isolation (via repository)
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
@requires_db
async def test_multi_tenant_isolation(
    db_session: AsyncSession,
    tenant_a: Tenant,
    tenant_b: Tenant,
) -> None:
    """7.4 — repository scoped to tenant A cannot see tenant B's
    records and vice-versa."""
    repo_a = BaseRepository(db=db_session, tenant_id=tenant_a.id, model=Tenant)
    repo_b = BaseRepository(db=db_session, tenant_id=tenant_b.id, model=Tenant)

    record = await repo_a.create(
        {"nombre": "A's Record", "codigo": "RECORD_A"}
    )

    # Tenant B cannot see it
    assert await repo_b.get(record.id) is None

    # Tenant A can see it
    records_a = await repo_a.list()
    ids_a = [r.id for r in records_a]
    assert record.id in ids_a

    # Tenant B's list is empty (only has itself, not A's record)
    records_b = await repo_b.list()
    ids_b = [r.id for r in records_b]
    assert record.id not in ids_b

    # Cleanup
    await db_session.execute(text("DELETE FROM tenant WHERE codigo = 'RECORD_A'"))
    await db_session.commit()


# ═══════════════════════════════════════════════════════════
# Soft delete
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
@requires_db
async def test_soft_delete(
    db_session: AsyncSession,
    tenant_a: Tenant,
) -> None:
    """7.5 — soft delete hides record from get / list but
    get(include_deleted=True) still returns it."""
    repo = BaseRepository(db=db_session, tenant_id=tenant_a.id, model=Tenant)

    record = await repo.create(
        {"nombre": "To Delete", "codigo": "SOFT_DEL"}
    )
    assert await repo.get(record.id) is not None

    deleted = await repo.delete(record.id)
    assert deleted is True

    assert await repo.get(record.id) is None

    ids = [r.id for r in await repo.list()]
    assert record.id not in ids

    # include_deleted bypasses the filter
    found = await repo.get(record.id, include_deleted=True)
    assert found is not None
    assert found.deleted_at is not None

    # Cleanup
    await db_session.execute(text("DELETE FROM tenant WHERE codigo = 'SOFT_DEL'"))
    await db_session.commit()


# ═══════════════════════════════════════════════════════════
# BaseRepository CRUD — happy path
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
@requires_db
async def test_repository_create_and_get(
    db_session: AsyncSession,
    tenant_a: Tenant,
) -> None:
    """7.9 — create returns entity with id; get retrieves it."""
    repo = BaseRepository(db=db_session, tenant_id=tenant_a.id, model=Tenant)

    entity = await repo.create({"nombre": "CRUD", "codigo": "CRUD_1"})
    assert entity.id is not None
    assert entity.nombre == "CRUD"

    fetched = await repo.get(entity.id)
    assert fetched is not None
    assert fetched.id == entity.id
    assert fetched.nombre == "CRUD"

    # Cleanup
    await db_session.execute(text("DELETE FROM tenant WHERE codigo = 'CRUD_1'"))
    await db_session.commit()


@pytest.mark.asyncio
@requires_db
async def test_repository_list(
    db_session: AsyncSession,
    tenant_a: Tenant,
) -> None:
    """7.9 — list returns all entities scoped to the tenant."""
    repo = BaseRepository(db=db_session, tenant_id=tenant_a.id, model=Tenant)

    await repo.create({"nombre": "List A", "codigo": "LIST_A"})
    await repo.create({"nombre": "List B", "codigo": "LIST_B"})

    entities = await repo.list()
    codigos = [e.codigo for e in entities]
    assert "LIST_A" in codigos
    assert "LIST_B" in codigos

    # Cleanup
    await db_session.execute(
        text("DELETE FROM tenant WHERE codigo IN ('LIST_A', 'LIST_B')")
    )
    await db_session.commit()


@pytest.mark.asyncio
@requires_db
async def test_repository_update(
    db_session: AsyncSession,
    tenant_a: Tenant,
) -> None:
    """7.9 — update modifies fields and persists them."""
    repo = BaseRepository(db=db_session, tenant_id=tenant_a.id, model=Tenant)

    entity = await repo.create({"nombre": "Old Name", "codigo": "UPDATE_1"})
    updated = await repo.update(entity.id, {"nombre": "New Name"})
    assert updated is not None
    assert updated.nombre == "New Name"

    fetched = await repo.get(entity.id)
    assert fetched is not None
    assert fetched.nombre == "New Name"

    # Cleanup
    await db_session.execute(text("DELETE FROM tenant WHERE codigo = 'UPDATE_1'"))
    await db_session.commit()


@pytest.mark.asyncio
@requires_db
async def test_repository_update_nonexistent_returns_none(
    db_session: AsyncSession,
    tenant_a: Tenant,
) -> None:
    """7.9 — update on non-existent id returns None."""
    repo = BaseRepository(db=db_session, tenant_id=tenant_a.id, model=Tenant)
    result = await repo.update(uuid.uuid4(), {"nombre": "Nope"})
    assert result is None


@pytest.mark.asyncio
@requires_db
async def test_repository_delete_nonexistent_returns_false(
    db_session: AsyncSession,
    tenant_a: Tenant,
) -> None:
    """7.9 — delete on non-existent id returns False."""
    repo = BaseRepository(db=db_session, tenant_id=tenant_a.id, model=Tenant)
    result = await repo.delete(uuid.uuid4())
    assert result is False


# ═══════════════════════════════════════════════════════════
# Cross-tenant isolation
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
@requires_db
async def test_cross_tenant_get_returns_none(
    db_session: AsyncSession,
    tenant_a: Tenant,
    tenant_b: Tenant,
) -> None:
    """7.10 — get from a different tenant's repository returns None."""
    repo_a = BaseRepository(db=db_session, tenant_id=tenant_a.id, model=Tenant)
    repo_b = BaseRepository(db=db_session, tenant_id=tenant_b.id, model=Tenant)

    entity = await repo_a.create({"nombre": "Secret", "codigo": "CROSS_GET"})

    assert await repo_b.get(entity.id) is None

    # Cleanup
    await db_session.execute(text("DELETE FROM tenant WHERE codigo = 'CROSS_GET'"))
    await db_session.commit()


@pytest.mark.asyncio
@requires_db
async def test_cross_tenant_list_is_empty(
    db_session: AsyncSession,
    tenant_a: Tenant,
    tenant_b: Tenant,
) -> None:
    """7.10 — list from a different tenant is empty for those records."""
    repo_a = BaseRepository(db=db_session, tenant_id=tenant_a.id, model=Tenant)
    repo_b = BaseRepository(db=db_session, tenant_id=tenant_b.id, model=Tenant)

    await repo_a.create({"nombre": "Secret", "codigo": "CROSS_LIST"})

    b_codigos = [e.codigo for e in await repo_b.list()]
    assert "CROSS_LIST" not in b_codigos

    # Cleanup
    await db_session.execute(text("DELETE FROM tenant WHERE codigo = 'CROSS_LIST'"))
    await db_session.commit()


# ═══════════════════════════════════════════════════════════
# get_by_id_without_tenant
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
@requires_db
async def test_get_by_id_without_tenant_bypasses_scope(
    db_session: AsyncSession,
    tenant_a: Tenant,
    tenant_b: Tenant,
) -> None:
    """7.11 — get_by_id_without_tenant returns the entity regardless
    of the repository's tenant scope, while normal get returns None."""
    repo_a = BaseRepository(db=db_session, tenant_id=tenant_a.id, model=Tenant)
    repo_b = BaseRepository(db=db_session, tenant_id=tenant_b.id, model=Tenant)

    entity = await repo_a.create({"nombre": "Admin", "codigo": "BYPASS"})

    # Normal get — blocked by tenant scope
    assert await repo_b.get(entity.id) is None

    # Bypass — works across tenants
    bypassed = await repo_b.get_by_id_without_tenant(entity.id)
    assert bypassed is not None
    assert bypassed.id == entity.id
    assert bypassed.nombre == "Admin"

    # Cleanup
    await db_session.execute(text("DELETE FROM tenant WHERE codigo = 'BYPASS'"))
    await db_session.commit()
