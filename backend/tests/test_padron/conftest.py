"""Test fixtures for the padron module (C-09)."""

import hashlib
import hmac
import uuid
from datetime import date

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import EstadoGenerico
from app.core.security import AESCipher, create_access_token
from app.models.domain.asignacion import Asignacion
from app.models.domain.carrera import Carrera
from app.models.domain.cohorte import Cohorte
from app.models.domain.entrada_padron import EntradaPadron
from app.models.domain.materia import Materia
from app.models.domain.usuario import Usuario
from app.models.domain.version_padron import VersionPadron


@pytest_asyncio.fixture
async def carrera_create(db_session: AsyncSession, tenant_a) -> Carrera:
    carrera = Carrera(
        tenant_id=tenant_a.id,
        codigo="CARR-001",
        nombre="Ingeniería en Sistemas",
        estado=EstadoGenerico.ACTIVA.value,
    )
    db_session.add(carrera)
    await db_session.commit()
    await db_session.refresh(carrera)
    return carrera


@pytest_asyncio.fixture
async def cohorte_create(db_session: AsyncSession, tenant_a, carrera_create) -> Cohorte:
    cohorte = Cohorte(
        tenant_id=tenant_a.id,
        carrera_id=carrera_create.id,
        nombre="2026",
        anio=2026,
        estado=EstadoGenerico.ACTIVA.value,
        vig_desde=date(2026, 1, 1),
    )
    db_session.add(cohorte)
    await db_session.commit()
    await db_session.refresh(cohorte)
    return cohorte


@pytest_asyncio.fixture
async def materia_create(db_session: AsyncSession, tenant_a) -> Materia:
    materia = Materia(
        tenant_id=tenant_a.id,
        codigo="MAT-001",
        nombre="Matemáticas",
        estado=EstadoGenerico.ACTIVA.value,
    )
    db_session.add(materia)
    await db_session.commit()
    await db_session.refresh(materia)
    return materia


@pytest_asyncio.fixture
async def materia_create_b(db_session: AsyncSession, tenant_a) -> Materia:
    materia = Materia(
        tenant_id=tenant_a.id,
        codigo="MAT-002",
        nombre="Física",
        estado=EstadoGenerico.ACTIVA.value,
    )
    db_session.add(materia)
    await db_session.commit()
    await db_session.refresh(materia)
    return materia


@pytest_asyncio.fixture
async def usuario_create(db_session: AsyncSession, tenant_a) -> Usuario:
    key = get_settings().ENCRYPTION_KEY.encode("utf-8")
    email = "test.user@example.com"
    email_hash = hmac.new(
        key, email.lower().strip().encode("utf-8"), hashlib.sha256
    ).hexdigest()

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
async def usuario_create_b(db_session: AsyncSession, tenant_b) -> Usuario:
    key = get_settings().ENCRYPTION_KEY.encode("utf-8")
    email = "test.user.b@example.com"
    email_hash = hmac.new(
        key, email.lower().strip().encode("utf-8"), hashlib.sha256
    ).hexdigest()

    usuario = Usuario(
        tenant_id=tenant_b.id,
        nombre="TestB",
        apellidos="UserB",
        email=AESCipher.encrypt(email),
        email_hash=email_hash,
        estado=EstadoGenerico.ACTIVA.value,
    )
    db_session.add(usuario)
    await db_session.commit()
    await db_session.refresh(usuario)
    return usuario


@pytest_asyncio.fixture
async def asignacion_profesor(
    db_session: AsyncSession, tenant_a, usuario_create, materia_create
) -> Asignacion:
    asignacion = Asignacion(
        tenant_id=tenant_a.id,
        usuario_id=usuario_create.id,
        rol="PROFESOR",
        materia_id=materia_create.id,
        comisiones=[],
        desde=date(2026, 1, 1),
    )
    db_session.add(asignacion)
    await db_session.commit()
    await db_session.refresh(asignacion)
    return asignacion


@pytest_asyncio.fixture
async def version_padron_create(
    db_session: AsyncSession,
    tenant_a,
    materia_create,
    cohorte_create,
    usuario_create,
) -> VersionPadron:
    version = VersionPadron(
        tenant_id=tenant_a.id,
        materia_id=materia_create.id,
        cohorte_id=cohorte_create.id,
        activa=False,
        origen="archivo",
        cargado_por=usuario_create.id,
    )
    db_session.add(version)
    await db_session.commit()
    await db_session.refresh(version)
    return version


@pytest_asyncio.fixture
async def entrada_padron_create(
    db_session: AsyncSession, version_padron_create
) -> EntradaPadron:
    entrada = EntradaPadron(
        tenant_id=version_padron_create.tenant_id,
        version_id=version_padron_create.id,
        nombre="Juan",
        apellidos="Pérez",
        email="juan.perez@example.com",
        comision="A",
        regional="Córdoba",
    )
    db_session.add(entrada)
    await db_session.commit()
    await db_session.refresh(entrada)
    return entrada


@pytest_asyncio.fixture
async def auth_headers(usuario_create, tenant_a) -> dict:
    token = create_access_token(
        user_id=str(usuario_create.id),
        tenant_id=str(tenant_a.id),
        roles=["ADMIN"],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def profesor_auth_headers(usuario_create, tenant_a) -> dict:
    token = create_access_token(
        user_id=str(usuario_create.id),
        tenant_id=str(tenant_a.id),
        roles=["PROFESOR"],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def coordinador_auth_headers(usuario_create, tenant_a) -> dict:
    token = create_access_token(
        user_id=str(usuario_create.id),
        tenant_id=str(tenant_a.id),
        roles=["COORDINADOR"],
    )
    return {"Authorization": f"Bearer {token}"}
