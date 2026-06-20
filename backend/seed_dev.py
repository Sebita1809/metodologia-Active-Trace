"""
seed_dev.py — Bootstrap mínimo para desarrollo local.

Crea:
  - 1 tenant  : slug="demo", nombre="Institución Demo"
  - 1 user    : admin@demo.com / Admin1234!
  - RBAC seed : roles + permisos + matriz para el tenant
  - 1 usuario : perfil ADMIN ligado al user anterior

Uso (dentro del container):
    python seed_dev.py

Idempotente: si el tenant/usuario ya existe, no falla.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date

import sys

sys.path.insert(0, "/app")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import get_settings
from app.core.crypto import CryptoService
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User
from app.models.usuario import Usuario
from app.models.asignacion import Asignacion
from app.services.rbac_seed import seed_rbac_for_tenant

SEED_EMAIL = "admin@demo.com"
SEED_PASSWORD = "Admin1234!"
SEED_NOMBRE = "Admin"
SEED_APELLIDOS = "Demo"
TENANT_SLUG = "demo"
TENANT_NOMBRE = "Institución Demo"


async def main() -> None:
    cfg = get_settings()
    engine = create_async_engine(cfg.database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    crypto = CryptoService(cfg.encryption_key)

    async with Session() as session:
        # ── 1. Tenant ───────────────────────────────────────────────────────
        result = await session.execute(
            select(Tenant).where(Tenant.slug == TENANT_SLUG)
        )
        tenant = result.scalar_one_or_none()
        if tenant:
            tenant_id = tenant.id
            print(f"[skip] Tenant '{TENANT_SLUG}' ya existe: {tenant_id}")
        else:
            tenant = Tenant(slug=TENANT_SLUG, nombre=TENANT_NOMBRE)
            session.add(tenant)
            await session.flush()
            tenant_id = tenant.id
            print(f"[ok]   Tenant creado: {tenant_id}")

        # ── 2. RBAC seed ─────────────────────────────────────────────────────
        conn = await session.connection()
        await conn.run_sync(seed_rbac_for_tenant, tenant_id)
        print("[ok]   RBAC seeded")

        # ── 3. Auth user ────────────────────────────────────────────────────
        result = await session.execute(
            select(User).where(
                User.tenant_id == tenant_id, User.email == SEED_EMAIL
            )
        )
        user = result.scalar_one_or_none()
        if user:
            user_id = user.id
            print(f"[skip] User '{SEED_EMAIL}' ya existe: {user_id}")
        else:
            user_id = uuid.uuid4()
            pw_hash = hash_password(SEED_PASSWORD)
            user = User(
                id=user_id,
                tenant_id=tenant_id,
                email=SEED_EMAIL,
                password_hash=pw_hash,
                is_active=True,
            )
            session.add(user)
            await session.flush()
            print(f"[ok]   User creado: {user_id}")

        # ── 4. Usuario (perfil de dominio) ──────────────────────────────────
        email_hash = crypto.hash_deterministic(SEED_EMAIL)
        result = await session.execute(
            select(Usuario).where(
                Usuario.tenant_id == tenant_id,
                Usuario.email_hash == email_hash,
            )
        )
        usuario = result.scalar_one_or_none()
        if usuario:
            usuario_id = usuario.id
            print(f"[skip] Usuario ya existe: {usuario_id}")
        else:
            usuario_id = uuid.uuid4()
            email_enc = crypto.encrypt(SEED_EMAIL)
            usuario = Usuario(
                id=usuario_id,
                tenant_id=tenant_id,
                nombre=SEED_NOMBRE,
                apellidos=SEED_APELLIDOS,
                email=email_enc,
                email_hash=email_hash,
            )
            session.add(usuario)
            await session.flush()
            print(f"[ok]   Usuario creado: {usuario_id}")

        # ── 5. Asignación ADMIN ─────────────────────────────────────────────
        result = await session.execute(
            select(Asignacion).where(
                Asignacion.tenant_id == tenant_id,
                Asignacion.usuario_id == usuario_id,
                Asignacion.rol == "ADMIN",
                Asignacion.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none():
            print("[skip] Asignación ADMIN ya existe")
        else:
            asignacion = Asignacion(
                tenant_id=tenant_id,
                usuario_id=usuario_id,
                rol="ADMIN",
                desde=date.today(),
            )
            session.add(asignacion)
            print("[ok]   Asignación ADMIN creada")

        await session.commit()

    await engine.dispose()

    print()
    print("=" * 50)
    print("  CREDENCIALES DE ACCESO")
    print("=" * 50)
    print(f"  Email   : {SEED_EMAIL}")
    print(f"  Password: {SEED_PASSWORD}")
    print(f"  Tenant  : {TENANT_SLUG}")
    print(f"  Rol     : ADMIN")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
