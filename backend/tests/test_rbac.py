"""Tests for C-04 RBAC: seed data integrity, permission resolution,
HTTP guard behaviour (require_permission), and DB constraints.

All tests are integration tests using the real PostgreSQL via conftest fixtures.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import resolve_user_permissions
from app.core.security import create_access_token
from app.models.permiso import Permiso
from app.models.rol import Rol
from app.models.rol_permiso import RolPermiso
from app.models.tenant import Tenant

pytestmark = pytest.mark.asyncio

# ── Test endpoint for RBAC guard ────────────────────────────────
from fastapi import APIRouter, Depends

from app.core.dependencies import UserContext, get_current_user, require_permission
from app.main import app

_test_router = APIRouter()


@_test_router.get("/api/v1/test-rbac/protected")
async def _protected_endpoint(
    current_user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission("calificaciones:importar")),
):
    return {"status": "ok", "user_id": str(current_user.user_id)}


_existing_paths = {r.path for r in app.routes if hasattr(r, 'path')}
if "/api/v1/test-rbac/protected" not in _existing_paths:
    app.include_router(_test_router)

# ── Helpers ─────────────────────────────────────────────────────


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════════
# 4.1 Seed Data Integrity
# ═══════════════════════════════════════════════════════════════════


class TestSeedData:
    async def test_seed_has_7_roles(self, db_session: AsyncSession) -> None:
        """WHEN migration 003 is applied THEN 7 seed roles exist (tenant_id=NULL)."""
        result = await db_session.execute(
            text("SELECT nombre FROM rol WHERE tenant_id IS NULL ORDER BY nombre")
        )
        role_names = {row[0] for row in result.all()}
        assert len(role_names) >= 7
        assert role_names == {
            "ALUMNO",
            "TUTOR",
            "PROFESOR",
            "COORDINADOR",
            "NEXO",
            "ADMIN",
            "FINANZAS",
        }

    async def test_seed_has_20_permissions(self, db_session: AsyncSession) -> None:
        """WHEN all permissions are queried THEN 20 permission codes exist (seed from 003 + 007)."""
        result = await db_session.execute(text("SELECT codigo FROM permiso WHERE deleted_at IS NULL"))
        perm_codes = {row[0] for row in result.all()}
        expected = {
            "calificaciones:importar",
            "atrasados:ver",
            "comunicacion:enviar",
            "comunicacion:aprobar",
            "equipos:asignar",
            "encuentros:gestionar",
            "encuentros:ver",
            "guardias:registrar",
            "tareas:gestionar",
            "avisos:publicar",
            "estructura:gestionar",
            "usuarios:gestionar",
            "auditoria:ver",
            "liquidaciones:gestionar",
            "liquidaciones:cerrar",
            "facturas:gestionar",
            "salarios:gestionar",
            "configuracion:gestionar",
            "impersonacion:usar",
            "padron:importar",
        }
        assert perm_codes == expected

    async def test_admin_has_estructura_gestionar(self, db_session: AsyncSession) -> None:
        """WHEN querying ADMIN permissions THEN includes estructura:gestionar."""
        result = await db_session.execute(
            text("""
                SELECT p.codigo
                FROM rol_permiso rp
                JOIN rol r ON rp.rol_id = r.id
                JOIN permiso p ON rp.permiso_id = p.id
                WHERE r.nombre = 'ADMIN'
            """)
        )
        admin_perms = {row[0] for row in result.all()}
        assert "estructura:gestionar" in admin_perms

    async def test_profesor_has_atrasados_ver_but_not_estructura_gestionar(
        self, db_session: AsyncSession
    ) -> None:
        """WHEN querying PROFESOR permissions THEN has atrasados:ver NOT estructura:gestionar."""
        result = await db_session.execute(
            text("""
                SELECT p.codigo
                FROM rol_permiso rp
                JOIN rol r ON rp.rol_id = r.id
                JOIN permiso p ON rp.permiso_id = p.id
                WHERE r.nombre = 'PROFESOR'
            """)
        )
        prof_perms = {row[0] for row in result.all()}
        assert "atrasados:ver" in prof_perms
        assert "estructura:gestionar" not in prof_perms

    async def test_alumno_has_no_permissions(
        self, db_session: AsyncSession
    ) -> None:
        """WHEN querying ALUMNO permissions THEN no permissions are assigned."""
        result = await db_session.execute(
            text("""
                SELECT p.codigo
                FROM rol_permiso rp
                JOIN rol r ON rp.rol_id = r.id
                JOIN permiso p ON rp.permiso_id = p.id
                WHERE r.nombre = 'ALUMNO'
            """)
        )
        alumno_perms = {row[0] for row in result.all()}
        assert len(alumno_perms) == 0


# ═══════════════════════════════════════════════════════════════════
# 4.2 & 4.3 & 4.6  require_permission HTTP Guard
# ═══════════════════════════════════════════════════════════════════


class TestRequirePermission:
    async def test_user_with_permission_gets_200(
        self,
        async_client: AsyncClient,
        tenant_a: Tenant,
    ) -> None:
        """WHEN ADMIN has calificaciones:importar THEN protected endpoint returns 200."""
        token = create_access_token(
            user_id=str(uuid.uuid4()),
            tenant_id=str(tenant_a.id),
            roles=["ADMIN"],
        )
        resp = await async_client.get(
            "/api/v1/test-rbac/protected",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_user_without_permission_gets_403(
        self,
        async_client: AsyncClient,
        tenant_a: Tenant,
    ) -> None:
        """WHEN ALUMNO lacks calificaciones:importar THEN protected endpoint returns 403."""
        token = create_access_token(
            user_id=str(uuid.uuid4()),
            tenant_id=str(tenant_a.id),
            roles=["ALUMNO"],
        )
        resp = await async_client.get(
            "/api/v1/test-rbac/protected",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 403
        assert "Missing required permission" in resp.json()["detail"]

    async def test_unauthorized_no_token_gets_401(
        self,
        async_client: AsyncClient,
    ) -> None:
        """WHEN no Authorization header THEN endpoint returns 401."""
        resp = await async_client.get("/api/v1/test-rbac/protected")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Not authenticated"


# ═══════════════════════════════════════════════════════════════════
# 4.4 Multi-role Inheritance
# ═══════════════════════════════════════════════════════════════════


class TestMultiRoleInheritance:
    async def test_multi_role_profesor_mas_coordinador_union(
        self,
        db_session: AsyncSession,
    ) -> None:
        """WHEN user has PROFESOR + COORDINADOR THEN perms are union (incl avisos:publicar)."""
        perms = await resolve_user_permissions(
            user_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            roles=["PROFESOR", "COORDINADOR"],
            db=db_session,
        )
        assert "avisos:publicar" in perms
        assert "atrasados:ver" in perms
        assert "estructura:gestionar" not in perms

    async def test_single_role_profesor_no_avisos(
        self,
        db_session: AsyncSession,
    ) -> None:
        """WHEN user has only PROFESOR THEN avisos:publicar is NOT resolved."""
        perms = await resolve_user_permissions(
            user_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            roles=["PROFESOR"],
            db=db_session,
        )
        assert "avisos:publicar" not in perms

    async def test_empty_roles_returns_empty_set(
        self,
        db_session: AsyncSession,
    ) -> None:
        """WHEN user has no roles THEN resolve_user_permissions returns empty set."""
        perms = await resolve_user_permissions(
            user_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            roles=[],
            db=db_session,
        )
        assert perms == set()

    async def test_unknown_role_returns_empty_set(
        self,
        db_session: AsyncSession,
    ) -> None:
        """WHEN user has a role that does not exist in DB THEN empty set returned."""
        perms = await resolve_user_permissions(
            user_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            roles=["NONEXISTENT_ROLE"],
            db=db_session,
        )
        assert perms == set()


# ═══════════════════════════════════════════════════════════════════
# 4.5 Tenant Isolation
# ═══════════════════════════════════════════════════════════════════


class TestTenantIsolation:
    async def test_tenant_specific_role_not_visible_to_other_tenant(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
    ) -> None:
        """GIVEN a role scoped to tenant_b WHEN resolving for tenant_a THEN it is invisible."""
        role_b = Rol(
            nombre="TENANT_B_ROLE",
            descripcion="Specific to tenant B",
            tenant_id=tenant_b.id,
        )
        db_session.add(role_b)
        await db_session.commit()
        await db_session.refresh(role_b)

        try:
            perms_a = await resolve_user_permissions(
                user_id=uuid.uuid4(),
                tenant_id=tenant_a.id,
                roles=["TENANT_B_ROLE"],
                db=db_session,
            )
            assert perms_a == set()

            perms_b = await resolve_user_permissions(
                user_id=uuid.uuid4(),
                tenant_id=tenant_b.id,
                roles=["TENANT_B_ROLE"],
                db=db_session,
            )
            # same: no permission assignments on TENANT_B_ROLE, but role WAS found
            assert perms_b == set()
        finally:
            await db_session.execute(
                text("DELETE FROM rol WHERE nombre = 'TENANT_B_ROLE'")
            )
            await db_session.commit()

    async def test_tenant_specific_role_with_perm_only_visible_to_its_tenant(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
    ) -> None:
        """GIVEN a role in tenant_b with a permission WHEN resolving for tenant_a THEN perm not visible."""
        result = await db_session.execute(
            text("SELECT id FROM permiso WHERE codigo = 'configuracion:gestionar' LIMIT 1")
        )
        perm_id = result.scalar_one()

        role_b = Rol(
            nombre="TENANT_B_ADMIN",
            descripcion="Tenant B custom admin",
            tenant_id=tenant_b.id,
        )
        db_session.add(role_b)
        await db_session.commit()
        await db_session.refresh(role_b)

        rp = RolPermiso(rol_id=role_b.id, permiso_id=perm_id)
        db_session.add(rp)
        await db_session.commit()

        try:
            perms_a = await resolve_user_permissions(
                user_id=uuid.uuid4(),
                tenant_id=tenant_a.id,
                roles=["TENANT_B_ADMIN"],
                db=db_session,
            )
            assert "configuracion:gestionar" not in perms_a

            perms_b = await resolve_user_permissions(
                user_id=uuid.uuid4(),
                tenant_id=tenant_b.id,
                roles=["TENANT_B_ADMIN"],
                db=db_session,
            )
            assert "configuracion:gestionar" in perms_b
        finally:
            await db_session.execute(
                text("DELETE FROM rol_permiso WHERE rol_id = :rid"),
                {"rid": role_b.id},
            )
            await db_session.execute(
                text("DELETE FROM rol WHERE nombre IN ('TENANT_B_ADMIN')")
            )
            await db_session.commit()

    async def test_global_role_visible_to_all_tenants(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
    ) -> None:
        """GIVEN a global role (tenant_id=NULL) WHEN resolving for any tenant THEN it is visible."""
        perms_a = await resolve_user_permissions(
            user_id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            roles=["ADMIN"],
            db=db_session,
        )
        perms_b = await resolve_user_permissions(
            user_id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            roles=["ADMIN"],
            db=db_session,
        )
        assert len(perms_a) > 0
        assert perms_a == perms_b
        assert "estructura:gestionar" in perms_a


# ═══════════════════════════════════════════════════════════════════
# 4.7 Uniqueness Constraints
# ═══════════════════════════════════════════════════════════════════


class TestUniquenessConstraints:
    async def test_duplicate_rol_name_same_tenant_raises(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
    ) -> None:
        """WHEN creating two roles with same nombre in same tenant THEN IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        rol1 = Rol(nombre="UNIQUE_TEST", tenant_id=tenant_a.id)
        db_session.add(rol1)
        await db_session.commit()

        try:
            rol2 = Rol(nombre="UNIQUE_TEST", tenant_id=tenant_a.id)
            db_session.add(rol2)
            with pytest.raises(IntegrityError):
                await db_session.commit()
            await db_session.rollback()
        finally:
            await db_session.execute(
                text("DELETE FROM rol WHERE nombre = 'UNIQUE_TEST'")
            )
            await db_session.commit()

    async def test_duplicate_rol_name_different_tenant_allowed(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
    ) -> None:
        """GIVEN a rol in tenant_a WHEN same nombre in tenant_b THEN allowed."""
        rol_a = Rol(nombre="SAME_NAME", tenant_id=tenant_a.id)
        db_session.add(rol_a)
        await db_session.commit()

        try:
            rol_b = Rol(nombre="SAME_NAME", tenant_id=tenant_b.id)
            db_session.add(rol_b)
            await db_session.commit()
        finally:
            await db_session.execute(
                text("DELETE FROM rol WHERE nombre = 'SAME_NAME'")
            )
            await db_session.commit()

    async def test_duplicate_permiso_codigo_raises(
        self,
        db_session: AsyncSession,
    ) -> None:
        """WHEN creating two permissions with same codigo THEN IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        perm1 = Permiso(codigo="TEST:duplicate", modulo="TEST", accion="duplicate")
        db_session.add(perm1)
        await db_session.commit()

        try:
            perm2 = Permiso(codigo="TEST:duplicate", modulo="TEST", accion="duplicate")
            db_session.add(perm2)
            with pytest.raises(IntegrityError):
                await db_session.commit()
            await db_session.rollback()
        finally:
            await db_session.execute(
                text("DELETE FROM permiso WHERE codigo = 'TEST:duplicate'")
            )
            await db_session.commit()

    async def test_duplicate_rol_permiso_raises(
        self,
        db_session: AsyncSession,
    ) -> None:
        """WHEN creating duplicate (rol_id, permiso_id) THEN IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        result = await db_session.execute(
            text("SELECT id FROM rol WHERE nombre = 'ADMIN' LIMIT 1")
        )
        admin_rol_id = result.scalar_one()

        # Use a UUID suffix to avoid collisions from previous test runs
        suffix = uuid.uuid4().hex[:8]
        codigo = f"test:dup_{suffix}"
        temp_perm = Permiso(codigo=codigo, modulo="test", accion="duplicate")
        db_session.add(temp_perm)
        await db_session.commit()
        await db_session.refresh(temp_perm)
        temp_perm_id = temp_perm.id  # save before any rollback to avoid MissingGreenlet

        try:
            rp1 = RolPermiso(rol_id=admin_rol_id, permiso_id=temp_perm_id)
            db_session.add(rp1)
            await db_session.commit()

            rp2 = RolPermiso(rol_id=admin_rol_id, permiso_id=temp_perm_id)
            db_session.add(rp2)
            with pytest.raises(IntegrityError):
                await db_session.commit()
            await db_session.rollback()
        finally:
            await db_session.execute(
                text("DELETE FROM rol_permiso WHERE permiso_id = :pid"),
                {"pid": temp_perm_id},
            )
            await db_session.execute(
                text("DELETE FROM permiso WHERE id = :pid"),
                {"pid": temp_perm_id},
            )
            await db_session.commit()


# ═══════════════════════════════════════════════════════════════════
# 4.8 Foreign Key Constraints
# ═══════════════════════════════════════════════════════════════════


class TestForeignKeyConstraints:
    async def test_rol_permiso_invalid_rol_id_raises(
        self,
        db_session: AsyncSession,
    ) -> None:
        """WHEN creating RolPermiso with non-existent rol_id THEN IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        fake_rol_id = uuid.uuid4()
        result = await db_session.execute(
            text(
                "SELECT id FROM permiso WHERE codigo = 'calificaciones:importar' LIMIT 1"
            )
        )
        perm_id = result.scalar_one()

        rp = RolPermiso(rol_id=fake_rol_id, permiso_id=perm_id)
        db_session.add(rp)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_rol_permiso_invalid_permiso_id_raises(
        self,
        db_session: AsyncSession,
    ) -> None:
        """WHEN creating RolPermiso with non-existent permiso_id THEN IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        result = await db_session.execute(
            text("SELECT id FROM rol WHERE nombre = 'ADMIN' LIMIT 1")
        )
        admin_rol_id = result.scalar_one()

        fake_perm_id = uuid.uuid4()
        rp = RolPermiso(rol_id=admin_rol_id, permiso_id=fake_perm_id)
        db_session.add(rp)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
