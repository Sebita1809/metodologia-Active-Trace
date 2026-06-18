"""Test fixtures for usuario and asignacion tests."""
import uuid

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import EstadoGenerico
from app.models.domain.usuario import Usuario


@pytest_asyncio.fixture
async def usuario_data_valido() -> dict:
    return {
        "nombre": "Juan",
        "apellidos": "Pérez",
        "email": "juan.perez@example.com",
        "dni": "12345678",
        "cuil": "20-12345678-9",
        "legajo": "LEG-001",
    }


@pytest_asyncio.fixture
async def usuario_data_sin_pii() -> dict:
    return {
        "nombre": "María",
        "apellidos": "García",
        "email": "maria.garcia@example.com",
    }


@pytest_asyncio.fixture
async def usuario_create(
    db_session: AsyncSession, tenant_a
) -> Usuario:
    """Create a minimal Usuario in tenant_a directly via DB."""
    import hashlib
    import hmac
    from app.core.config import get_settings
    from app.core.security import AESCipher

    key = get_settings().ENCRYPTION_KEY.encode("utf-8")
    email = "test.user@example.com"
    email_hash = hmac.new(key, email.lower().strip().encode("utf-8"), hashlib.sha256).hexdigest()

    usuario = Usuario(
        tenant_id=tenant_a.id,
        nombre="Test",
        apellidos="User",
        email=AESCipher.encrypt(email),
        email_hash=email_hash,
        estado=EstadoGenerico.ACTIVA.value,
    )
    db_session.add(usuario)
    await db_session.commit()
    await db_session.refresh(usuario)
    return usuario


@pytest_asyncio.fixture
async def asignacion_data_valida(usuario_create, db_session, tenant_a) -> dict:
    """Return valid asignacion data referencing existing models."""
    from datetime import date
    return {
        "usuario_id": usuario_create.id,
        "rol": "PROFESOR",
        "desde": date(2026, 1, 1),
        "hasta": date(2026, 12, 31),
    }


@pytest_asyncio.fixture
async def asignacion_create(db_session: AsyncSession, usuario_create) -> Usuario:
    """Create a minimal Asignacion directly via DB."""
    from datetime import date
    from app.models.domain.asignacion import Asignacion

    asignacion = Asignacion(
        tenant_id=usuario_create.tenant_id,
        usuario_id=usuario_create.id,
        rol="PROFESOR",
        desde=date(2026, 1, 1),
        hasta=date(2026, 12, 31),
    )
    db_session.add(asignacion)
    await db_session.commit()
    await db_session.refresh(asignacion)
    return asignacion
