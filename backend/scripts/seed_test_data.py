"""Seed test data: demo tenant + users for manual endpoint testing.

Usage:
    python scripts/seed_test_data.py

Requires DATABASE_URL env var (defaults to local dev PostgreSQL).
"""

import asyncio
import os
import sys
import uuid

# Ensure app/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from argon2 import PasswordHasher
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

import hmac
from datetime import date, timezone
from hashlib import sha256

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.security import AESCipher, create_access_token
from app.models.auth_user import AuthUser
from app.models.domain.asignacion import Asignacion
from app.models.domain.usuario import Usuario
from app.models.tenant import Tenant

# ── Configuration ──────────────────────────────────────────────────────────

DEMO_TENANT_CODIGO = "DEMO"
DEMO_TENANT_NOMBRE = "Demo Tenant"

ADMIN_EMAIL = "admin@demo.com"
ADMIN_PASSWORD = "Admin_123"

TARGET_EMAIL = "target@demo.com"
TARGET_PASSWORD = "Target_123"

# The ADMIN role UUID from migration 003 (deterministic)
ADMIN_ROLE_UUID = "a6666666-6666-6666-6666-666666666666"

# ── Helpers ────────────────────────────────────────────────────────────────


async def seed(session: AsyncSession) -> None:
    ph = PasswordHasher()

    # ── 1. Create / find tenant ───────────────────────────────────────────
    result = await session.execute(
        select(Tenant).where(Tenant.codigo == DEMO_TENANT_CODIGO)
    )
    tenant: Tenant | None = result.scalar_one_or_none()

    if tenant is None:
        tenant = Tenant(nombre=DEMO_TENANT_NOMBRE, codigo=DEMO_TENANT_CODIGO)
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
        print(f"[OK] Tenant created: {tenant.nombre} (codigo={tenant.codigo}, id={tenant.id})")
    else:
        print(f"[i] Tenant already exists: {tenant.nombre} (id={tenant.id})")

    # ── 2. Create admin user ──────────────────────────────────────────────
    result = await session.execute(
        select(AuthUser).where(
            AuthUser.email == ADMIN_EMAIL,
            AuthUser.tenant_id == tenant.id,
        )
    )
    admin = result.scalar_one_or_none()
    if admin is None:
        admin = AuthUser(
            tenant_id=tenant.id,
            email=ADMIN_EMAIL,
            password_hash=ph.hash(ADMIN_PASSWORD),
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        print(f"[OK] Admin created: {admin.email} (id={admin.id})")
    else:
        print(f"[i] Admin already exists: {admin.email} (id={admin.id})")

    # ── 3. Create Usuario + Asignacion for admin (so AuthService can resolve roles) ─
    key = get_settings().ENCRYPTION_KEY.encode("utf-8")
    email_hash = hmac.new(key, ADMIN_EMAIL.lower().strip().encode("utf-8"), sha256).hexdigest()
    result = await session.execute(
        select(Usuario).where(
            Usuario.tenant_id == tenant.id,
            Usuario.email_hash == email_hash,
        )
    )
    usuario = result.scalar_one_or_none()
    if usuario is None:
        usuario = Usuario(
            tenant_id=tenant.id,
            nombre="Admin",
            apellidos="Demo",
            email=AESCipher.encrypt(ADMIN_EMAIL),
            email_hash=email_hash,
        )
        session.add(usuario)
        await session.commit()
        await session.refresh(usuario)
        print(f"[OK] Usuario created: {usuario.nombre} {usuario.apellidos} (id={usuario.id})")
    else:
        print(f"[i] Usuario already exists: {usuario.nombre} {usuario.apellidos} (id={usuario.id})")

    # ── 3b. Create Asignacion ADMIN for this usuario ──
    result = await session.execute(
        select(Asignacion).where(
            Asignacion.usuario_id == usuario.id,
            Asignacion.rol == "ADMIN",
            Asignacion.deleted_at.is_(None),
        )
    )
    asignacion = result.scalar_one_or_none()
    if asignacion is None:
        asignacion = Asignacion(
            tenant_id=tenant.id,
            usuario_id=usuario.id,
            rol="ADMIN",
            desde=date.today(),
        )
        session.add(asignacion)
        await session.commit()
        await session.refresh(asignacion)
        print(f"[OK] Asignacion ADMIN created (id={asignacion.id})")
    else:
        print(f"[i] Asignacion ADMIN already exists (id={asignacion.id})")

    # ── 4. Create target user (for impersonation) ─────────────────────────
    result = await session.execute(
        select(AuthUser).where(
            AuthUser.email == TARGET_EMAIL,
            AuthUser.tenant_id == tenant.id,
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        target = AuthUser(
            tenant_id=tenant.id,
            email=TARGET_EMAIL,
            password_hash=ph.hash(TARGET_PASSWORD),
        )
        session.add(target)
        await session.commit()
        await session.refresh(target)
        print(f"[OK] Target user created: {target.email} (id={target.id})")
    else:
        print(f"[i] Target user already exists: {target.email} (id={target.id})")

    # ── 4. Generate tokens ────────────────────────────────────────────────
    admin_token = create_access_token(
        user_id=str(admin.id),
        tenant_id=str(tenant.id),
        roles=["ADMIN"],
        expires_delta=None,  # default 15 min
    )

    target_token = create_access_token(
        user_id=str(target.id),
        tenant_id=str(tenant.id),
        roles=["ALUMNO"],
        expires_delta=None,
    )

    print()
    print("=" * 60)
    print("  TEST DATA SUMMARY")
    print("=" * 60)
    print(f"  Tenant ID:      {tenant.id}")
    print(f"  Tenant codigo:  {tenant.codigo}")
    print()
    print(f"  Admin:          {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"  Admin ID:       {admin.id}")
    print(f"  Target:         {TARGET_EMAIL} / {TARGET_PASSWORD}")
    print(f"  Target ID:      {target.id}")
    print()
    print("-" * 60)
    print("  ADMIN TOKEN (has impersonacion:usar)")
    print("-" * 60)
    print(admin_token)
    print()
    print("-" * 60)
    print("  TARGET TOKEN (ALUMNO, no permissions)")
    print("-" * 60)
    print(target_token)
    print()
    print("=" * 60)
    print("  IMPERSONATION TEST FLOW")
    print("=" * 60)
    print()
    print(f"  1. POST /api/v1/impersonacion/iniciar")
    print(f"     Body: {{\"usuario_id\": \"{target.id}\"}}")
    print(f"     Headers: Authorization: Bearer <admin_token>")
    print()
    print(f"  2. POST /api/v1/impersonacion/finalizar")
    print(f"     Headers: Authorization: Bearer <impersonation_token>")
    print()


async def clean(session: AsyncSession) -> None:
    """Remove demo data (idempotent)."""
    for email in [ADMIN_EMAIL, TARGET_EMAIL]:
        result = await session.execute(
            select(AuthUser).where(AuthUser.email == email)
        )
        user = result.scalar_one_or_none()
        if user:
            await session.delete(user)
            print(f"[DEL] Deleted user: {email}")
    result = await session.execute(
        select(Tenant).where(Tenant.codigo == DEMO_TENANT_CODIGO)
    )
    tenant = result.scalar_one_or_none()
    if tenant:
        await session.delete(tenant)
        print(f"[DEL] Deleted tenant: {tenant.codigo}")
    await session.commit()


async def main() -> None:
    action = "seed"
    if len(sys.argv) > 1 and sys.argv[1] == "--clean":
        action = "clean"

    factory = get_session_factory()
    async with factory() as session:
        if action == "clean":
            await clean(session)
            print("Done. Demo data removed.")
        else:
            await seed(session)
            print("Done. Demo data ready.")


if __name__ == "__main__":
    asyncio.run(main())
