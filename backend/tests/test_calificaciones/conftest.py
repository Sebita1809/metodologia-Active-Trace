"""Test fixtures for the calificaciones module (C-10)."""
from __future__ import annotations

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
from app.models.domain.calificacion import Calificacion, OrigenCalificacion
from app.models.domain.carrera import Carrera
from app.models.domain.cohorte import Cohorte
from app.models.domain.entrada_padron import EntradaPadron
from app.models.domain.materia import Materia
from app.models.domain.umbral_materia import UmbralMateria
from app.models.domain.usuario import Usuario
from app.models.domain.version_padron import VersionPadron


@pytest_asyncio.fixture
async def carrera_create(db_session: AsyncSession, tenant_a) -> Carrera:
    carrera = Carrera(
        tenant_id=tenant_a.id,
        codigo="CARR-CAL-001",
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
        codigo="MAT-CAL-001",
        nombre="Matemáticas",
        estado=EstadoGenerico.ACTIVA.value,
    )
    db_session.add(materia)
    await db_session.commit()
    await db_session.refresh(materia)
    return materia


@pytest_asyncio.fixture
async def usuario_create(db_session: AsyncSession, tenant_a) -> Usuario:
    key = get_settings().ENCRYPTION_KEY.encode("utf-8")
    email = "profesor.cal@example.com"
    email_hash = hmac.new(
        key, email.lower().strip().encode("utf-8"), hashlib.sha256
    ).hexdigest()

    usuario = Usuario(
        tenant_id=tenant_a.id,
        nombre="Profe",
        apellidos="Cal",
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
async def umbral_data(
    db_session: AsyncSession,
    tenant_a,
    materia_create,
    asignacion_profesor,
) -> UmbralMateria:
    umbral = UmbralMateria(
        tenant_id=tenant_a.id,
        asignacion_id=asignacion_profesor.id,
        materia_id=materia_create.id,
        umbral_pct=60,
        valores_aprobatorios=["Aprobado", "Satisfactorio"],
    )
    db_session.add(umbral)
    await db_session.commit()
    await db_session.refresh(umbral)
    return umbral


@pytest_asyncio.fixture
async def version_padron_activa(
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
        activa=True,
        origen="archivo",
        cargado_por=usuario_create.id,
    )
    db_session.add(version)
    await db_session.commit()
    await db_session.refresh(version)
    return version


@pytest_asyncio.fixture
async def entrada_padron_data(
    db_session: AsyncSession,
    tenant_a,
    version_padron_activa,
) -> list[EntradaPadron]:
    entradas_data = [
        {"nombre": "Juan", "apellidos": "Pérez", "email": "juan.perez@example.com", "comision": "A"},
        {"nombre": "María", "apellidos": "García", "email": "maria.garcia@example.com", "comision": "A"},
    ]
    entradas = []
    for data in entradas_data:
        e = EntradaPadron(
            tenant_id=tenant_a.id,
            version_id=version_padron_activa.id,
            nombre=data["nombre"],
            apellidos=data["apellidos"],
            email=data["email"],
            comision=data.get("comision"),
        )
        db_session.add(e)
        entradas.append(e)
    await db_session.commit()
    for e in entradas:
        await db_session.refresh(e)
    return entradas


@pytest_asyncio.fixture
async def calificacion_data(
    db_session: AsyncSession,
    tenant_a,
    materia_create,
    entrada_padron_data,
) -> list[Calificacion]:
    califs = []
    for entrada in entrada_padron_data:
        c = Calificacion(
            tenant_id=tenant_a.id,
            entrada_padron_id=entrada.id,
            materia_id=materia_create.id,
            actividad="Examen Parcial",
            nota_numerica=75,
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add(c)
        califs.append(c)
    await db_session.commit()
    for c in califs:
        await db_session.refresh(c)
    return califs


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
