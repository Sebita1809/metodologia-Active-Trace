"""
seed_completo.py — Seed completo de desarrollo para activia-trace.

Puebla TODAS las tablas del sistema con datos de prueba realistas.
Idempotente: si un registro ya existe, lo saltea.

Uso (dentro del container):
    python seed_completo.py
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, time, timedelta, timezone

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
from app.models.usuario_rol import UsuarioRol
from app.models.rol import Rol
from app.models.carrera import Carrera
from app.models.cohorte import Cohorte
from app.models.materia import Materia
from app.models.version_padron import VersionPadron
from app.models.entrada_padron import EntradaPadron
from app.models.calificacion import Calificacion
from app.models.evaluacion import Evaluacion
from app.models.reserva_evaluacion import ReservaEvaluacion
from app.models.resultado_evaluacion import ResultadoEvaluacion
from app.models.slot_encuentro import SlotEncuentro
from app.models.instancia_encuentro import InstanciaEncuentro
from app.models.guardia import Guardia
from app.models.aviso import Aviso
from app.models.acknowledgment_aviso import AcknowledgmentAviso
from app.models.comunicacion import Comunicacion
from app.models.tarea import Tarea
from app.models.comentario_tarea import ComentarioTarea
from app.models.salario_base import SalarioBase
from app.models.salario_plus import SalarioPlus
from app.models.liquidacion import Liquidacion
from app.models.factura import Factura
from app.models.audit_log import AuditLog
from app.models.mensaje import Mensaje
from app.models.umbral_materia import UmbralMateria
from app.models.programa_materia import ProgramaMateria
from app.models.fecha_academica import FechaAcademica
from app.services.rbac_seed import seed_rbac_for_tenant

TENANT_SLUG = "demo"
TENANT_NOMBRE = "Institución Demo"
SEED_PASSWORD = "Demo1234!"


def _email_data(crypto: CryptoService, email: str) -> tuple[str, str]:
    encrypted = crypto.encrypt(email)
    ehash = crypto.hash_deterministic(email)
    return encrypted, ehash


def _pii(crypto: CryptoService, value: str) -> str:
    return crypto.encrypt(value)


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _get_or_create_tenant(session) -> uuid.UUID:
    result = await session.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
    tenant = result.scalar_one_or_none()
    if tenant:
        print(f"[skip] Tenant '{TENANT_SLUG}' ya existe: {tenant.id}")
        return tenant.id
    tenant = Tenant(slug=TENANT_SLUG, nombre=TENANT_NOMBRE)
    session.add(tenant)
    await session.flush()
    print(f"[ok]   Tenant creado: {tenant.id}")
    return tenant.id


async def _seed_rbac(session, tenant_id: uuid.UUID) -> None:
    conn = await session.connection()
    await conn.run_sync(seed_rbac_for_tenant, tenant_id)
    print("[ok]   RBAC seeded")


async def _get_rol_id(session, tenant_id: uuid.UUID, nombre: str) -> uuid.UUID:
    result = await session.execute(
        select(Rol).where(Rol.tenant_id == tenant_id, Rol.nombre == nombre)
    )
    rol = result.scalar_one_or_none()
    if not rol:
        raise ValueError(f"Rol '{nombre}' not found — run RBAC seed first")
    return rol.id


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _months_ago(n: int) -> datetime:
    return _now() - timedelta(days=30 * n)


# ── Data definitions ─────────────────────────────────────────────────────────

CARRERAS_DATA = [
    {"codigo": "ISI", "nombre": "Ingeniería en Sistemas de Información"},
    {"codigo": "LC", "nombre": "Licenciatura en Ciencias de la Computación"},
    {"codigo": "LI", "nombre": "Licenciatura en Informática"},
]

COHORTES_DATA: list[dict] = [
    {"codigo_carrera": "ISI", "nombre": "2023", "anio": 2023, "vig_desde": date(2023, 3, 1)},
    {"codigo_carrera": "ISI", "nombre": "2024", "anio": 2024, "vig_desde": date(2024, 3, 1)},
    {"codigo_carrera": "ISI", "nombre": "2025", "anio": 2025, "vig_desde": date(2025, 3, 1)},
    {"codigo_carrera": "LC", "nombre": "2023", "anio": 2023, "vig_desde": date(2023, 3, 1)},
    {"codigo_carrera": "LC", "nombre": "2024", "anio": 2024, "vig_desde": date(2024, 3, 1)},
    {"codigo_carrera": "LI", "nombre": "2024", "anio": 2024, "vig_desde": date(2024, 3, 1)},
    {"codigo_carrera": "LI", "nombre": "2025", "anio": 2025, "vig_desde": date(2025, 3, 1)},
]

MATERIAS_DATA: list[dict] = [
    {"codigo": "MAT101", "nombre": "Matemática I", "codigo_carrera": "ISI", "clave_plus": None},
    {"codigo": "PRO101", "nombre": "Programación I", "codigo_carrera": "ISI", "clave_plus": "PROG"},
    {"codigo": "ARQ101", "nombre": "Arquitectura de Computadoras", "codigo_carrera": "ISI", "clave_plus": None},
    {"codigo": "SIS101", "nombre": "Sistemas de Información I", "codigo_carrera": "ISI", "clave_plus": None},
    {"codigo": "MAT102", "nombre": "Matemática II", "codigo_carrera": "ISI", "clave_plus": None},
    {"codigo": "PRO102", "nombre": "Programación II", "codigo_carrera": "ISI", "clave_plus": "PROG"},
    {"codigo": "BD101", "nombre": "Base de Datos I", "codigo_carrera": "ISI", "clave_plus": "BD"},
    {"codigo": "RED101", "nombre": "Redes I", "codigo_carrera": "ISI", "clave_plus": "REDES"},
    {"codigo": "LOG101", "nombre": "Lógica y Computabilidad", "codigo_carrera": "LC", "clave_plus": None},
    {"codigo": "ALG101", "nombre": "Álgebra Lineal", "codigo_carrera": "LC", "clave_plus": None},
    {"codigo": "ORG101", "nombre": "Organización de Datos", "codigo_carrera": "LI", "clave_plus": None},
]

USUARIO_DATA: list[dict] = [
    # email, nombre, apellidos, rol, dni, cuil, legajo, banco, cbu, facturador, regional
    {"email": "admin@demo.com", "nombre": "Admin", "apellidos": "Sistema", "rol": "ADMIN", "dni": None, "cuil": None, "legajo": None, "banco": None, "cbu": None, "facturador": False, "regional": None, "skip_existing": True},
    {"email": "coord@demo.com", "nombre": "María", "apellidos": "González", "rol": "COORDINADOR", "dni": "28901234", "cuil": "27-28901234-3", "legajo": "LEG-001", "banco": "Banco Nación", "cbu": "0110599520000001234567", "facturador": False, "regional": "CABA"},
    {"email": "finanzas@demo.com", "nombre": "Carlos", "apellidos": "Rodríguez", "rol": "FINANZAS", "dni": "30123456", "cuil": "20-30123456-7", "legajo": "LEG-002", "banco": "Banco Santander", "cbu": "0720599520000001234567", "facturador": False, "regional": "CABA"},
    {"email": "nexo@demo.com", "nombre": "Laura", "apellidos": "Martínez", "rol": "NEXO", "dni": "27123456", "cuil": "27-27123456-1", "legajo": "LEG-003", "banco": None, "cbu": None, "facturador": False, "regional": "Córdoba"},
    {"email": "prof1@demo.com", "nombre": "Roberto", "apellidos": "Fernández", "rol": "PROFESOR", "dni": "18234567", "cuil": "20-18234567-2", "legajo": "LEG-004", "banco": "Banco Galicia", "cbu": "0070599520000001234567", "facturador": False, "regional": "CABA"},
    {"email": "prof2@demo.com", "nombre": "Ana", "apellidos": "López", "rol": "PROFESOR", "dni": "21234567", "cuil": "27-21234567-4", "legajo": "LEG-005", "banco": "Banco Macro", "cbu": "0150599520000001234567", "facturador": True, "regional": "Rosario"},
    {"email": "prof3@demo.com", "nombre": "Diego", "apellidos": "Ramírez", "rol": "PROFESOR", "dni": "25123456", "cuil": "20-25123456-9", "legajo": "LEG-006", "banco": None, "cbu": None, "facturador": False, "regional": "La Plata"},
    {"email": "prof4@demo.com", "nombre": "Valeria", "apellidos": "Castro", "rol": "PROFESOR", "dni": "23567890", "cuil": "27-23567890-5", "legajo": "LEG-007", "banco": "Banco Ciudad", "cbu": "0290599520000001234567", "facturador": False, "regional": "CABA"},
    {"email": "tutor1@demo.com", "nombre": "Sofía", "apellidos": "Torres", "rol": "TUTOR", "dni": "31123456", "cuil": "27-31123456-8", "legajo": "LEG-008", "banco": None, "cbu": None, "facturador": False, "regional": "CABA"},
    {"email": "tutor2@demo.com", "nombre": "Pablo", "apellidos": "Acosta", "rol": "TUTOR", "dni": "32456789", "cuil": "20-32456789-3", "legajo": "LEG-009", "banco": "Banco Provincia", "cbu": "0140599520000001234567", "facturador": False, "regional": "Mar del Plata"},
    {"email": "tutor3@demo.com", "nombre": "Florencia", "apellidos": "Mendoza", "rol": "TUTOR", "dni": "33789123", "cuil": "27-33789123-7", "legajo": "LEG-010", "banco": None, "cbu": None, "facturador": False, "regional": "Rosario"},
    {"email": "alumno1@demo.com", "nombre": "Juan", "apellidos": "Pérez", "rol": "ALUMNO", "dni": "40123456", "cuil": "20-40123456-1", "legajo": "ALU-001", "banco": None, "cbu": None, "facturador": False, "regional": "CABA"},
    {"email": "alumno2@demo.com", "nombre": "Lucía", "apellidos": "Gómez", "rol": "ALUMNO", "dni": "41456789", "cuil": "27-41456789-4", "legajo": "ALU-002", "banco": None, "cbu": None, "facturador": False, "regional": "CABA"},
    {"email": "alumno3@demo.com", "nombre": "Martín", "apellidos": "Díaz", "rol": "ALUMNO", "dni": "42789123", "cuil": "20-42789123-2", "legajo": "ALU-003", "banco": None, "cbu": None, "facturador": False, "regional": "Gran Buenos Aires"},
    {"email": "alumno4@demo.com", "nombre": "Camila", "apellidos": "Álvarez", "rol": "ALUMNO", "dni": "43123456", "cuil": "27-43123456-9", "legajo": "ALU-004", "banco": None, "cbu": None, "facturador": False, "regional": "CABA"},
    {"email": "alumno5@demo.com", "nombre": "Nicolás", "apellidos": "Romero", "rol": "ALUMNO", "dni": "44567890", "cuil": "20-44567890-5", "legajo": "ALU-005", "banco": None, "cbu": None, "facturador": False, "regional": "La Plata"},
    {"email": "alumno6@demo.com", "nombre": "Valentina", "apellidos": "Sosa", "rol": "ALUMNO", "dni": "45123456", "cuil": "27-45123456-3", "legajo": "ALU-006", "banco": None, "cbu": None, "facturador": False, "regional": "Córdoba"},
    {"email": "alumno7@demo.com", "nombre": "Facundo", "apellidos": "Morales", "rol": "ALUMNO", "dni": "46789123", "cuil": "20-46789123-7", "legajo": "ALU-007", "banco": None, "cbu": None, "facturador": False, "regional": "Rosario"},
    {"email": "alumno8@demo.com", "nombre": "Agustina", "apellidos": "Medina", "rol": "ALUMNO", "dni": "47123456", "cuil": "27-47123456-1", "legajo": "ALU-008", "banco": None, "cbu": None, "facturador": False, "regional": "CABA"},
    {"email": "alumno9@demo.com", "nombre": "Santiago", "apellidos": "Castillo", "rol": "ALUMNO", "dni": "48567890", "cuil": "20-48567890-6", "legajo": "ALU-009", "banco": None, "cbu": None, "facturador": False, "regional": "Mar del Plata"},
    {"email": "alumno10@demo.com", "nombre": "Julieta", "apellidos": "Rodríguez", "rol": "ALUMNO", "dni": "49123456", "cuil": "27-49123456-4", "legajo": "ALU-010", "banco": None, "cbu": None, "facturador": False, "regional": "CABA"},
]

# which carrera and cohorte each alumno belongs to
ALUMNO_COHORTE_MAP: dict[str, tuple[str, str]] = {
    "alumno1@demo.com": ("ISI", "2024"),
    "alumno2@demo.com": ("ISI", "2024"),
    "alumno3@demo.com": ("ISI", "2024"),
    "alumno4@demo.com": ("ISI", "2025"),
    "alumno5@demo.com": ("ISI", "2025"),
    "alumno6@demo.com": ("LC", "2024"),
    "alumno7@demo.com": ("LC", "2024"),
    "alumno8@demo.com": ("LI", "2024"),
    "alumno9@demo.com": ("LI", "2024"),
    "alumno10@demo.com": ("LI", "2025"),
}

# materias each professor teaches
PROFESOR_MATERIAS: dict[str, list[tuple[str, str, list[str]]]] = {
    "prof1@demo.com": [("MAT101", "ISI", ["COM-A", "COM-B"]), ("MAT102", "ISI", ["COM-A"])],
    "prof2@demo.com": [("PRO101", "ISI", ["COM-A", "COM-B"]), ("PRO102", "ISI", ["COM-A"])],
    "prof3@demo.com": [("ARQ101", "ISI", ["COM-A"]), ("RED101", "ISI", ["COM-A", "COM-B"])],
    "prof4@demo.com": [("BD101", "ISI", ["COM-A"]), ("SIS101", "ISI", ["COM-A"])],
}

# materias each tutor supports
TUTOR_MATERIAS: dict[str, list[tuple[str, str, list[str]]]] = {
    "tutor1@demo.com": [("MAT101", "ISI", ["COM-A"])],
    "tutor2@demo.com": [("PRO101", "ISI", ["COM-A", "COM-B"]), ("BD101", "ISI", ["COM-A"])],
    "tutor3@demo.com": [("ARQ101", "ISI", ["COM-A"]), ("MAT102", "ISI", ["COM-A"])],
}

COORDINADOR_CARRERA = ("coord@demo.com", "ISI", ["ISI"])

DEFAULT_UMBRAL_PCT = 60


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main() -> None:
    cfg = get_settings()
    engine = create_async_engine(cfg.database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    crypto = CryptoService(cfg.encryption_key)

    async with Session() as session:
        # ── 1. Tenant ────────────────────────────────────────────────────────
        tenant_id = await _get_or_create_tenant(session)
        print(f"       tenant_id = {tenant_id}")

        # ── 2. RBAC seed ──────────────────────────────────────────────────────
        await _seed_rbac(session, tenant_id)

        # cache rol ids
        admin_rol_id = await _get_rol_id(session, tenant_id, "ADMIN")
        coord_rol_id = await _get_rol_id(session, tenant_id, "COORDINADOR")
        finanzas_rol_id = await _get_rol_id(session, tenant_id, "FINANZAS")
        nexo_rol_id = await _get_rol_id(session, tenant_id, "NEXO")
        prof_rol_id = await _get_rol_id(session, tenant_id, "PROFESOR")
        tutor_rol_id = await _get_rol_id(session, tenant_id, "TUTOR")
        alumno_rol_id = await _get_rol_id(session, tenant_id, "ALUMNO")

        # ── 3. Carreras ──────────────────────────────────────────────────────
        carrera_ids: dict[str, uuid.UUID] = {}
        for cd in CARRERAS_DATA:
            result = await session.execute(
                select(Carrera).where(
                    Carrera.tenant_id == tenant_id,
                    Carrera.codigo == cd["codigo"],
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                carrera_ids[cd["codigo"]] = existing.id
                print(f"[skip] Carrera {cd['codigo']} ya existe")
            else:
                cid = uuid.uuid4()
                carrera_ids[cd["codigo"]] = cid
                session.add(Carrera(id=cid, tenant_id=tenant_id, codigo=cd["codigo"], nombre=cd["nombre"]))
                print(f"[ok]   Carrera {cd['codigo']} creada: {cid}")
        await session.flush()

        # ── 4. Cohortes ──────────────────────────────────────────────────────
        cohorte_ids: dict[str, dict[str, uuid.UUID]] = {}
        for chd in COHORTES_DATA:
            cod_carrera = chd["codigo_carrera"]
            nombre = chd["nombre"]
            result = await session.execute(
                select(Cohorte).where(
                    Cohorte.tenant_id == tenant_id,
                    Cohorte.carrera_id == carrera_ids[cod_carrera],
                    Cohorte.nombre == nombre,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                cohorte_ids.setdefault(cod_carrera, {})[nombre] = existing.id
                print(f"[skip] Cohorte {cod_carrera}/{nombre} ya existe")
            else:
                cid = uuid.uuid4()
                cohorte_ids.setdefault(cod_carrera, {})[nombre] = cid
                session.add(Cohorte(
                    id=cid,
                    tenant_id=tenant_id,
                    carrera_id=carrera_ids[cod_carrera],
                    nombre=nombre,
                    anio=chd["anio"],
                    vig_desde=chd["vig_desde"],
                ))
                print(f"[ok]   Cohorte {cod_carrera}/{nombre} creada: {cid}")
        await session.flush()

        # ── 5. Materias ──────────────────────────────────────────────────────
        materia_ids: dict[str, uuid.UUID] = {}
        for md in MATERIAS_DATA:
            result = await session.execute(
                select(Materia).where(
                    Materia.tenant_id == tenant_id,
                    Materia.codigo == md["codigo"],
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                materia_ids[md["codigo"]] = existing.id
                print(f"[skip] Materia {md['codigo']} ya existe")
            else:
                mid = uuid.uuid4()
                materia_ids[md["codigo"]] = mid
                session.add(Materia(
                    id=mid,
                    tenant_id=tenant_id,
                    codigo=md["codigo"],
                    nombre=md["nombre"],
                    clave_plus=md["clave_plus"],
                ))
                print(f"[ok]   Materia {md['codigo']} creada: {mid}")
        await session.flush()

        # ── 6. Users + Usuarios + Asignaciones + UsuarioRol ──────────────────
        usuario_ids: dict[str, uuid.UUID] = {}
        user_ids: dict[str, uuid.UUID] = {}
        pw_hash = hash_password(SEED_PASSWORD)

        for ud in USUARIO_DATA:
            email = ud["email"]
            email_enc, email_hash = _email_data(crypto, email)

            # check Usuario by email_hash
            result = await session.execute(
                select(Usuario).where(
                    Usuario.tenant_id == tenant_id,
                    Usuario.email_hash == email_hash,
                )
            )
            existing_usuario = result.scalar_one_or_none()

            skip = ud.get("skip_existing", True)

            if existing_usuario and skip:
                usuario_ids[email] = existing_usuario.id
                print(f"[skip] Usuario {email} ya existe")
                # find corresponding user
                result2 = await session.execute(
                    select(User).where(
                        User.tenant_id == tenant_id,
                        User.email == email,
                    )
                )
                existing_user = result2.scalar_one_or_none()
                if existing_user:
                    user_ids[email] = existing_user.id
                continue

            # create User (auth account)
            result2 = await session.execute(
                select(User).where(
                    User.tenant_id == tenant_id,
                    User.email == email,
                )
            )
            existing_user = result2.scalar_one_or_none()
            if existing_user:
                uid = existing_user.id
                user_ids[email] = uid
                print(f"[skip] User {email} ya existe: {uid}")
            else:
                uid = uuid.uuid4()
                user_ids[email] = uid
                session.add(User(id=uid, tenant_id=tenant_id, email=email, password_hash=pw_hash, is_active=True))
                print(f"[ok]   User {email} creado: {uid}")

            # create Usuario (profile)
            if existing_usuario:
                usuario_ids[email] = existing_usuario.id
                print(f"[skip] Usuario {email} ya existe: {existing_usuario.id}")
            else:
                usid = uuid.uuid4()
                usuario_ids[email] = usid

                kwargs = dict(
                    id=usid,
                    tenant_id=tenant_id,
                    nombre=ud["nombre"],
                    apellidos=ud["apellidos"],
                    email=email_enc,
                    email_hash=email_hash,
                    estado="Activo",
                    facturador=ud["facturador"],
                )
                if ud["dni"]:
                    kwargs["dni"] = _pii(crypto, ud["dni"])
                if ud["cuil"]:
                    kwargs["cuil"] = _pii(crypto, ud["cuil"])
                if ud["banco"]:
                    kwargs["banco"] = ud["banco"]
                if ud["cbu"]:
                    kwargs["cbu"] = _pii(crypto, ud["cbu"])
                if ud["legajo"]:
                    kwargs["legajo"] = ud["legajo"]
                if ud["regional"]:
                    kwargs["regional"] = ud["regional"]

                session.add(Usuario(**kwargs))
                print(f"[ok]   Usuario {email} creado: {usid}")

        await session.flush()

        # ── 7. Asignaciones ──────────────────────────────────────────────────
        now_date = date.today()

        # Admin — already exists from seed_dev
        admin_email = "admin@demo.com"
        result = await session.execute(
            select(Asignacion).where(
                Asignacion.tenant_id == tenant_id,
                Asignacion.usuario_id == usuario_ids[admin_email],
                Asignacion.rol == "ADMIN",
                Asignacion.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none():
            print("[skip] Asignación ADMIN ya existe")
        else:
            session.add(Asignacion(tenant_id=tenant_id, usuario_id=usuario_ids[admin_email], rol="ADMIN", desde=now_date))
            print("[ok]   Asignación ADMIN creada")

        # Coordinador → ISI
        coord_email = "coord@demo.com"
        result = await session.execute(
            select(Asignacion).where(
                Asignacion.tenant_id == tenant_id,
                Asignacion.usuario_id == usuario_ids[coord_email],
                Asignacion.rol == "COORDINADOR",
                Asignacion.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none():
            print("[skip] Asignación COORDINADOR ya existe")
        else:
            session.add(Asignacion(
                tenant_id=tenant_id,
                usuario_id=usuario_ids[coord_email],
                rol="COORDINADOR",
                carrera_id=carrera_ids["ISI"],
                desde=now_date,
            ))
            print("[ok]   Asignación COORDINADOR creada")

        # Finanzas
        fin_email = "finanzas@demo.com"
        result = await session.execute(
            select(Asignacion).where(
                Asignacion.tenant_id == tenant_id,
                Asignacion.usuario_id == usuario_ids[fin_email],
                Asignacion.rol == "FINANZAS",
                Asignacion.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none():
            print("[skip] Asignación FINANZAS ya existe")
        else:
            session.add(Asignacion(tenant_id=tenant_id, usuario_id=usuario_ids[fin_email], rol="FINANZAS", desde=now_date))
            print("[ok]   Asignación FINANZAS creada")

        # Nexo
        nexo_email = "nexo@demo.com"
        result = await session.execute(
            select(Asignacion).where(
                Asignacion.tenant_id == tenant_id,
                Asignacion.usuario_id == usuario_ids[nexo_email],
                Asignacion.rol == "NEXO",
                Asignacion.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none():
            print("[skip] Asignación NEXO ya existe")
        else:
            session.add(Asignacion(tenant_id=tenant_id, usuario_id=usuario_ids[nexo_email], rol="NEXO", desde=now_date))
            print("[ok]   Asignación NEXO creada")

        # Profesores
        asignacion_prof_ids: dict[str, uuid.UUID] = {}
        for prof_email, materias in PROFESOR_MATERIAS.items():
            for cod_materia, cod_carrera, comisiones in materias:
                result = await session.execute(
                    select(Asignacion).where(
                        Asignacion.tenant_id == tenant_id,
                        Asignacion.usuario_id == usuario_ids[prof_email],
                        Asignacion.rol == "PROFESOR",
                        Asignacion.materia_id == materia_ids[cod_materia],
                        Asignacion.deleted_at.is_(None),
                    )
                )
                if result.scalar_one_or_none():
                    print(f"[skip] Asignación PROFESOR {prof_email} → {cod_materia} ya existe")
                else:
                    aid = uuid.uuid4()
                    asignacion_prof_ids.setdefault(prof_email, {})[cod_materia] = aid
                    session.add(Asignacion(
                        id=aid,
                        tenant_id=tenant_id,
                        usuario_id=usuario_ids[prof_email],
                        rol="PROFESOR",
                        materia_id=materia_ids[cod_materia],
                        carrera_id=carrera_ids[cod_carrera],
                        comisiones=comisiones,
                        desde=now_date,
                    ))
                    print(f"[ok]   Asignación PROFESOR {prof_email} → {cod_materia} creada: {aid}")

        # Tutores
        asignacion_tutor_ids: dict[str, uuid.UUID] = {}
        for tutor_email, materias in TUTOR_MATERIAS.items():
            for cod_materia, cod_carrera, comisiones in materias:
                result = await session.execute(
                    select(Asignacion).where(
                        Asignacion.tenant_id == tenant_id,
                        Asignacion.usuario_id == usuario_ids[tutor_email],
                        Asignacion.rol == "TUTOR",
                        Asignacion.materia_id == materia_ids[cod_materia],
                        Asignacion.deleted_at.is_(None),
                    )
                )
                if result.scalar_one_or_none():
                    print(f"[skip] Asignación TUTOR {tutor_email} → {cod_materia} ya existe")
                else:
                    aid = uuid.uuid4()
                    asignacion_tutor_ids.setdefault(tutor_email, {})[cod_materia] = aid
                    session.add(Asignacion(
                        id=aid,
                        tenant_id=tenant_id,
                        usuario_id=usuario_ids[tutor_email],
                        rol="TUTOR",
                        materia_id=materia_ids[cod_materia],
                        carrera_id=carrera_ids[cod_carrera],
                        comisiones=comisiones,
                        desde=now_date,
                    ))
                    print(f"[ok]   Asignación TUTOR {tutor_email} → {cod_materia} creada: {aid}")

        # Alumnos
        for alumno_email, (cod_carrera, cod_cohorte) in ALUMNO_COHORTE_MAP.items():
            result = await session.execute(
                select(Asignacion).where(
                    Asignacion.tenant_id == tenant_id,
                    Asignacion.usuario_id == usuario_ids[alumno_email],
                    Asignacion.rol == "ALUMNO",
                    Asignacion.deleted_at.is_(None),
                )
            )
            if result.scalar_one_or_none():
                print(f"[skip] Asignación ALUMNO {alumno_email} ya existe")
            else:
                session.add(Asignacion(
                    tenant_id=tenant_id,
                    usuario_id=usuario_ids[alumno_email],
                    rol="ALUMNO",
                    carrera_id=carrera_ids[cod_carrera],
                    cohorte_id=cohorte_ids[cod_carrera][cod_cohorte],
                    desde=now_date,
                ))
                print(f"[ok]   Asignación ALUMNO {alumno_email} → {cod_carrera}/{cod_cohorte} creada")

        await session.flush()

        # ── 8. UsuarioRol ────────────────────────────────────────────────────
        rol_map: dict[str, uuid.UUID] = {
            "ADMIN": admin_rol_id,
            "COORDINADOR": coord_rol_id,
            "FINANZAS": finanzas_rol_id,
            "NEXO": nexo_rol_id,
            "PROFESOR": prof_rol_id,
            "TUTOR": tutor_rol_id,
            "ALUMNO": alumno_rol_id,
        }

        for ud in USUARIO_DATA:
            email = ud["email"]
            rol_name = ud["rol"]
            result = await session.execute(
                select(UsuarioRol).where(
                    UsuarioRol.tenant_id == tenant_id,
                    UsuarioRol.user_id == user_ids[email],
                    UsuarioRol.rol_id == rol_map[rol_name],
                    UsuarioRol.deleted_at.is_(None),
                )
            )
            if result.scalar_one_or_none():
                print(f"[skip] UsuarioRol {email} → {rol_name} ya existe")
            else:
                session.add(UsuarioRol(
                    tenant_id=tenant_id,
                    user_id=user_ids[email],
                    rol_id=rol_map[rol_name],
                    vigente_desde=_now() - timedelta(days=365),
                ))
                print(f"[ok]   UsuarioRol {email} → {rol_name} creado")
        await session.flush()

        # ── 9. UmbralMateria ────────────────────────────────────────────────
        umbral_configs = [
            ("prof1@demo.com", "MAT101", 60, ["Aprobado", "7", "8", "9", "10"]),
            ("prof1@demo.com", "MAT102", 65, ["Aprobado", "8", "9", "10"]),
            ("prof2@demo.com", "PRO101", 60, ["Aprobado", "6", "7", "8", "9", "10"]),
            ("prof4@demo.com", "BD101", 70, ["Aprobado", "8", "9", "10"]),
        ]
        for prof_email, cod_materia, pct, valores in umbral_configs:
            asig_id = asignacion_prof_ids.get(prof_email, {}).get(cod_materia)
            if not asig_id:
                continue
            result = await session.execute(
                select(UmbralMateria).where(
                    UmbralMateria.tenant_id == tenant_id,
                    UmbralMateria.asignacion_id == asig_id,
                )
            )
            if result.scalar_one_or_none():
                print(f"[skip] UmbralMateria {cod_materia}/{prof_email} ya existe")
            else:
                session.add(UmbralMateria(
                    tenant_id=tenant_id,
                    asignacion_id=asig_id,
                    materia_id=materia_ids[cod_materia],
                    umbral_pct=pct,
                    valores_aprobatorios=valores,
                ))
                print(f"[ok]   UmbralMateria {cod_materia} creado")
        await session.flush()

        # ── 10. VersionPadron + EntradaPadron ────────────────────────────────
        padron_specs = [
            {"cod_materia": "MAT101", "cod_carrera": "ISI", "cod_cohorte": "2024", "alumnos": ["alumno1@demo.com", "alumno2@demo.com", "alumno3@demo.com"], "origen": "moodle", "cargado_por": "prof1@demo.com"},
            {"cod_materia": "PRO101", "cod_carrera": "ISI", "cod_cohorte": "2024", "alumnos": ["alumno1@demo.com", "alumno2@demo.com", "alumno3@demo.com"], "origen": "archivo", "cargado_por": "prof2@demo.com"},
            {"cod_materia": "PRO101", "cod_carrera": "ISI", "cod_cohorte": "2025", "alumnos": ["alumno4@demo.com", "alumno5@demo.com"], "origen": "moodle", "cargado_por": "prof2@demo.com"},
            {"cod_materia": "MAT101", "cod_carrera": "LC", "cod_cohorte": "2024", "alumnos": ["alumno6@demo.com", "alumno7@demo.com"], "origen": "moodle", "cargado_por": "prof1@demo.com"},
        ]

        version_ids: dict[str, uuid.UUID] = {}
        for spec in padron_specs:
            cod_materia = spec["cod_materia"]
            cod_cohorte = spec["cod_cohorte"]
            key = f"{cod_materia}_{cod_cohorte}"

            result = await session.execute(
                select(VersionPadron).where(
                    VersionPadron.tenant_id == tenant_id,
                    VersionPadron.materia_id == materia_ids[cod_materia],
                    VersionPadron.cohorte_id == cohorte_ids[spec["cod_carrera"]][cod_cohorte],
                    VersionPadron.activa.is_(True),
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                version_ids[key] = existing.id
                print(f"[skip] VersionPadron {key} ya existe: {existing.id}")
            else:
                vid = uuid.uuid4()
                version_ids[key] = vid
                session.add(VersionPadron(
                    id=vid,
                    tenant_id=tenant_id,
                    materia_id=materia_ids[cod_materia],
                    cohorte_id=cohorte_ids[spec["cod_carrera"]][cod_cohorte],
                    cargado_por=usuario_ids[spec["cargado_por"]],
                    activa=True,
                    origen=spec["origen"],
                ))
                print(f"[ok]   VersionPadron {key} creada: {vid}")
                # Flush explicitamente para que la VersionPadron exista antes de las Entradas
                await session.flush()

                # EntradaPadron entries
                for alumno_email in spec["alumnos"]:
                    entry_email_enc = crypto.encrypt(alumno_email)
                    entry_nombre = next(
                        (ud["nombre"] for ud in USUARIO_DATA if ud["email"] == alumno_email), "Desconocido"
                    )
                    entry_apellidos = next(
                        (ud["apellidos"] for ud in USUARIO_DATA if ud["email"] == alumno_email), ""
                    )
                    session.add(EntradaPadron(
                        tenant_id=tenant_id,
                        version_id=vid,
                        usuario_id=usuario_ids.get(alumno_email),
                        nombre=entry_nombre,
                        apellidos=entry_apellidos,
                        email=entry_email_enc,
                        comision="COM-A",
                        regional=next(
                            (ud.get("regional") for ud in USUARIO_DATA if ud["email"] == alumno_email), None
                        ),
                    ))
                print(f"  [ok] {len(spec['alumnos'])} EntradaPadron entries for {key}")
        await session.flush()

        # ── 11. Calificacion ─────────────────────────────────────────────────
        calif_data: list[dict] = [
            # MAT101 ISI 2024 — Parcial, TP1, TP2
            {"cod_materia": "MAT101", "cod_cohorte": "2024", "email": "alumno1@demo.com", "actividad": "1er Parcial", "nota": 8.5, "aprobado": True, "origen": "Manual"},
            {"cod_materia": "MAT101", "cod_cohorte": "2024", "email": "alumno2@demo.com", "actividad": "1er Parcial", "nota": 6.0, "aprobado": True, "origen": "Manual"},
            {"cod_materia": "MAT101", "cod_cohorte": "2024", "email": "alumno3@demo.com", "actividad": "1er Parcial", "nota": 4.0, "aprobado": False, "origen": "Manual"},
            {"cod_materia": "MAT101", "cod_cohorte": "2024", "email": "alumno1@demo.com", "actividad": "TP1", "nota": 9.0, "aprobado": True, "origen": "Importado"},
            {"cod_materia": "MAT101", "cod_cohorte": "2024", "email": "alumno2@demo.com", "actividad": "TP1", "nota": 7.5, "aprobado": True, "origen": "Importado"},
            {"cod_materia": "MAT101", "cod_cohorte": "2024", "email": "alumno3@demo.com", "actividad": "TP1", "nota": 5.0, "aprobado": False, "origen": "Importado"},
            {"cod_materia": "MAT101", "cod_cohorte": "2024", "email": "alumno1@demo.com", "actividad": "TP2", "nota": 8.0, "aprobado": True, "origen": "Manual"},
            # PRO101 ISI 2024
            {"cod_materia": "PRO101", "cod_cohorte": "2024", "email": "alumno1@demo.com", "actividad": "1er Parcial", "nota": 9.0, "aprobado": True, "origen": "Manual"},
            {"cod_materia": "PRO101", "cod_cohorte": "2024", "email": "alumno2@demo.com", "actividad": "1er Parcial", "nota": 4.5, "aprobado": False, "origen": "Manual"},
            {"cod_materia": "PRO101", "cod_cohorte": "2024", "email": "alumno3@demo.com", "actividad": "1er Parcial", "nota": 7.0, "aprobado": True, "origen": "Manual"},
            {"cod_materia": "PRO101", "cod_cohorte": "2024", "email": "alumno1@demo.com", "actividad": "TP Integrador", "nota": 9.5, "aprobado": True, "origen": "Manual"},
            {"cod_materia": "PRO101", "cod_cohorte": "2024", "email": "alumno2@demo.com", "actividad": "TP Integrador", "nota": 6.0, "aprobado": True, "origen": "Manual"},
            {"cod_materia": "PRO101", "cod_cohorte": "2024", "email": "alumno3@demo.com", "actividad": "TP Integrador", "nota": 7.5, "aprobado": True, "origen": "Manual"},
            # PRO101 ISI 2025
            {"cod_materia": "PRO101", "cod_cohorte": "2025", "email": "alumno4@demo.com", "actividad": "1er Parcial", "nota": 8.0, "aprobado": True, "origen": "Manual"},
            {"cod_materia": "PRO101", "cod_cohorte": "2025", "email": "alumno5@demo.com", "actividad": "1er Parcial", "nota": 5.5, "aprobado": False, "origen": "Manual"},
            # MAT101 LC 2024
            {"cod_materia": "MAT101", "cod_cohorte": "2024", "email": "alumno6@demo.com", "actividad": "1er Parcial", "nota": 7.0, "aprobado": True, "origen": "Importado", "nota_textual": "Bueno"},
            {"cod_materia": "MAT101", "cod_cohorte": "2024", "email": "alumno7@demo.com", "actividad": "1er Parcial", "nota": 6.5, "aprobado": True, "origen": "Importado", "nota_textual": "Aprobado"},
            {"cod_materia": "MAT101", "cod_cohorte": "2024", "email": "alumno6@demo.com", "actividad": "TP1", "nota": 8.0, "aprobado": True, "origen": "Importado", "nota_textual": "Muy Bueno"},
            {"cod_materia": "MAT101", "cod_cohorte": "2024", "email": "alumno7@demo.com", "actividad": "TP1", "nota": None, "aprobado": False, "nota_textual": "Ausente", "origen": "Importado"},
        ]

        calif_count = 0
        for cd in calif_data:
            key = f"{cd['cod_materia']}_{cd['cod_cohorte']}"
            vid = version_ids.get(key)
            if not vid:
                # try to find any version for this materia+cohorte
                result = await session.execute(
                    select(VersionPadron).where(
                        VersionPadron.tenant_id == tenant_id,
                        VersionPadron.materia_id == materia_ids[cd["cod_materia"]],
                        VersionPadron.activa.is_(True),
                    )
                )
                vp = result.scalar_one_or_none()
                if not vp:
                    continue
                vid = vp.id

            # find entrada_padron for this alumno in this version
            alumno_email = cd["email"]
            result = await session.execute(
                select(EntradaPadron).where(
                    EntradaPadron.tenant_id == tenant_id,
                    EntradaPadron.version_id == vid,
                    EntradaPadron.usuario_id == usuario_ids[alumno_email],
                )
            )
            ep = result.scalar_one_or_none()
            if not ep:
                continue

            result = await session.execute(
                select(Calificacion).where(
                    Calificacion.tenant_id == tenant_id,
                    Calificacion.entrada_padron_id == ep.id,
                    Calificacion.actividad == cd["actividad"],
                )
            )
            if result.scalar_one_or_none():
                continue

            session.add(Calificacion(
                tenant_id=tenant_id,
                entrada_padron_id=ep.id,
                materia_id=materia_ids[cd["cod_materia"]],
                actividad=cd["actividad"],
                nota_numerica=cd.get("nota"),
                nota_textual=cd.get("nota_textual"),
                aprobado=cd["aprobado"],
                origen=cd["origen"],
            ))
            calif_count += 1
        if calif_count:
            print(f"[ok]   {calif_count} Calificaciones creadas")
        else:
            print("[skip] Calificaciones — no hay nuevas")

        await session.flush()

        # ── 12. Evaluaciones ─────────────────────────────────────────────────
        evaluacion_ids: list[uuid.UUID] = []
        eval_specs = [
            ("MAT101", "ISI", "2024", "Parcial", "1er Parcial", 10, 30),
            ("MAT101", "ISI", "2024", "TP", "TP Grupal", 15, 20),
            ("MAT101", "ISI", "2024", "Recuperatorio", "Recuperatorio 1er Parcial", 7, 15),
            ("PRO101", "ISI", "2024", "Parcial", "1er Parcial", 10, 25),
            ("PRO101", "ISI", "2024", "TP", "TP Integrador", 20, 10),
            ("PRO101", "ISI", "2024", "Recuperatorio", "Recuperatorio 1er Parcial", 7, 15),
        ]
        for cod_materia, cod_carrera, cod_cohorte, tipo, instancia, dias, cupo in eval_specs:
            result = await session.execute(
                select(Evaluacion).where(
                    Evaluacion.tenant_id == tenant_id,
                    Evaluacion.materia_id == materia_ids[cod_materia],
                    Evaluacion.cohorte_id == cohorte_ids[cod_carrera][cod_cohorte],
                    Evaluacion.tipo == tipo,
                    Evaluacion.instancia == instancia,
                )
            )
            if result.scalar_one_or_none():
                print(f"[skip] Evaluacion {cod_materia} {instancia} ya existe")
                continue
            eid = uuid.uuid4()
            evaluacion_ids.append(eid)
            session.add(Evaluacion(
                id=eid,
                tenant_id=tenant_id,
                materia_id=materia_ids[cod_materia],
                cohorte_id=cohorte_ids[cod_carrera][cod_cohorte],
                tipo=tipo,
                estado="Activa",
                instancia=instancia,
                dias_disponibles=dias,
                cupo_por_dia=cupo,
            ))
            print(f"[ok]   Evaluacion {cod_materia} {instancia} creada: {eid}")
        await session.flush()

        # ── 13. ReservaEvaluacion ────────────────────────────────────────────
        reserved_count = 0
        reserva_specs = [
            ("MAT101", "ISI", "2024", "1er Parcial", "alumno1@demo.com"),
            ("MAT101", "ISI", "2024", "1er Parcial", "alumno2@demo.com"),
            ("MAT101", "ISI", "2024", "1er Parcial", "alumno3@demo.com"),
            ("PRO101", "ISI", "2024", "1er Parcial", "alumno1@demo.com"),
            ("PRO101", "ISI", "2024", "1er Parcial", "alumno3@demo.com"),
            ("PRO101", "ISI", "2024", "TP Integrador", "alumno2@demo.com"),
        ]
        for cod_materia, cod_carrera, cod_cohorte, instancia, alumno_email in reserva_specs:
            # find evaluacion
            result = await session.execute(
                select(Evaluacion).where(
                    Evaluacion.tenant_id == tenant_id,
                    Evaluacion.materia_id == materia_ids[cod_materia],
                    Evaluacion.cohorte_id == cohorte_ids[cod_carrera][cod_cohorte],
                    Evaluacion.instancia == instancia,
                )
            )
            ev = result.scalar_one_or_none()
            if not ev:
                continue

            session.add(ReservaEvaluacion(
                tenant_id=tenant_id,
                evaluacion_id=ev.id,
                alumno_id=usuario_ids[alumno_email],
                fecha_hora=_now() + timedelta(days=7),
                estado="Activa",
            ))
            reserved_count += 1
        if reserved_count:
            print(f"[ok]   {reserved_count} ReservaEvaluacion creadas")
        await session.flush()

        # ── 13b. ResultadoEvaluacion ─────────────────────────────────────────
        resultados_count = 0
        for cod_materia, cod_carrera, cod_cohorte, instancia, alumno_email, nota in [
            ("MAT101", "ISI", "2024", "1er Parcial", "alumno1@demo.com", "8"),
            ("MAT101", "ISI", "2024", "1er Parcial", "alumno2@demo.com", "6"),
            ("PRO101", "ISI", "2024", "1er Parcial", "alumno1@demo.com", "9"),
            ("PRO101", "ISI", "2024", "1er Parcial", "alumno3@demo.com", "7"),
        ]:
            result = await session.execute(
                select(Evaluacion).where(
                    Evaluacion.tenant_id == tenant_id,
                    Evaluacion.materia_id == materia_ids[cod_materia],
                    Evaluacion.cohorte_id == cohorte_ids[cod_carrera][cod_cohorte],
                    Evaluacion.instancia == instancia,
                )
            )
            ev = result.scalar_one_or_none()
            if not ev:
                continue

            result = await session.execute(
                select(ResultadoEvaluacion).where(
                    ResultadoEvaluacion.tenant_id == tenant_id,
                    ResultadoEvaluacion.evaluacion_id == ev.id,
                    ResultadoEvaluacion.alumno_id == usuario_ids[alumno_email],
                )
            )
            if result.scalar_one_or_none():
                continue

            session.add(ResultadoEvaluacion(
                tenant_id=tenant_id,
                evaluacion_id=ev.id,
                alumno_id=usuario_ids[alumno_email],
                nota_final=nota,
            ))
            resultados_count += 1
        if resultados_count:
            print(f"[ok]   {resultados_count} ResultadoEvaluacion creados")
        await session.flush()

        # ── 14. SlotEncuentro + InstanciaEncuentro ───────────────────────────
        slot_count = 0
        instancia_count = 0
        base_date = date(2026, 4, 1)
        slot_specs = [
            # recurrent slots (weekly)
            ("prof1@demo.com", "MAT101", "Clase MAT101 - Com A", time(18, 0), "Lunes", base_date, 12, "https://meet.example.com/mat101"),
            ("prof2@demo.com", "PRO101", "Clase PRO101 - Com A", time(19, 30), "Martes", base_date, 12, "https://meet.example.com/pro101"),
            ("prof2@demo.com", "PRO101", "Clase PRO101 - Com B", time(18, 0), "Jueves", base_date, 12, "https://meet.example.com/pro101-b"),
            # unique slots
            ("prof1@demo.com", "MAT101", "Consulta pre-parcial", time(16, 0), None, None, 0, None),
        ]
        for prof_email, cod_materia, titulo, hora, dia_semana, fecha_inicio, cant_semanas, meet_url in slot_specs:
            asig_id = asignacion_prof_ids.get(prof_email, {}).get(cod_materia)
            if not asig_id:
                continue
            sid = uuid.uuid4()
            slot_count += 1
            session.add(SlotEncuentro(
                id=sid,
                tenant_id=tenant_id,
                asignacion_id=asig_id,
                materia_id=materia_ids[cod_materia],
                titulo=titulo,
                hora=hora,
                dia_semana=dia_semana,
                fecha_inicio=fecha_inicio,
                cant_semanas=cant_semanas,
                fecha_unica=None if cant_semanas > 0 else date(2026, 6, 10),
                meet_url=meet_url,
                vig_desde=base_date,
                vig_hasta=date(2026, 7, 1),
            ))
            # Flush para que el SlotEncuentro exista antes de las Instancias
            await session.flush()

            # create instances for recurrent slots
            if cant_semanas > 0 and dia_semana and fecha_inicio:
                day_map = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4, "Sábado": 5, "Domingo": 6}
                target_dow = day_map.get(dia_semana, 0)
                # find first occurrence on or after fecha_inicio
                first_date = fecha_inicio
                while first_date.weekday() != target_dow:
                    first_date = first_date + timedelta(days=1)
                for i in range(min(cant_semanas, 4)):  # create 4 instead of full 12
                    f = first_date + timedelta(weeks=i)
                    if f > date(2026, 6, 30):
                        break
                    estado = "Realizado" if f < date(2026, 6, 10) else "Programado"
                    session.add(InstanciaEncuentro(
                        tenant_id=tenant_id,
                        slot_id=sid,
                        materia_id=materia_ids[cod_materia],
                        fecha=f,
                        hora=hora,
                        titulo=titulo,
                        estado=estado,
                        meet_url=meet_url,
                    ))
                    instancia_count += 1

        # one unique instance for the unique slot
        unique_asig = asignacion_prof_ids.get("prof1@demo.com", {}).get("MAT101")
        if unique_asig:
            session.add(InstanciaEncuentro(
                tenant_id=tenant_id,
                slot_id=None,
                materia_id=materia_ids["MAT101"],
                fecha=date(2026, 6, 10),
                hora=time(16, 0),
                titulo="Consulta pre-parcial MAT101",
                estado="Programado",
                meet_url="https://meet.example.com/consulta-mat101",
                comentario="Clase de consulta abierta para todos los alumnos de MAT101",
            ))
            instancia_count += 1

        print(f"[ok]   {slot_count} SlotEncuentro, {instancia_count} InstanciaEncuentro creados")
        await session.flush()

        # ── 15. Guardia ──────────────────────────────────────────────────────
        guardia_count = 0
        guardia_specs = [
            ("tutor1@demo.com", "MAT101", "ISI", "2024", "Lunes", "14:00–14:45", "Pendiente"),
            ("tutor1@demo.com", "MAT101", "ISI", "2024", "Miércoles", "15:00–15:45", "Realizada"),
            ("tutor2@demo.com", "PRO101", "ISI", "2024", "Martes", "16:00–16:45", "Pendiente"),
            ("tutor2@demo.com", "PRO101", "ISI", "2024", "Jueves", "16:00–16:45", "Cancelada"),
            ("tutor3@demo.com", "ARQ101", "ISI", "2024", "Viernes", "17:00–17:45", "Pendiente"),
            ("tutor3@demo.com", "MAT102", "ISI", "2024", "Lunes", "18:00–18:45", "Realizada"),
            ("tutor1@demo.com", "MAT101", "ISI", "2025", "Miércoles", "14:00–14:45", "Pendiente"),
            ("tutor2@demo.com", "BD101", "ISI", "2024", "Viernes", "15:00–15:45", "Pendiente"),
        ]
        for tutor_email, cod_materia, cod_carrera, cod_cohorte, dia, horario, estado in guardia_specs:
            asig_id = asignacion_tutor_ids.get(tutor_email, {}).get(cod_materia)
            if not asig_id:
                continue
            session.add(Guardia(
                tenant_id=tenant_id,
                asignacion_id=asig_id,
                materia_id=materia_ids[cod_materia],
                carrera_id=carrera_ids[cod_carrera],
                cohorte_id=cohorte_ids[cod_carrera].get(cod_cohorte, list(cohorte_ids[cod_carrera].values())[0]),
                dia=dia,
                horario=horario,
                estado=estado,
            ))
            guardia_count += 1
        print(f"[ok]   {guardia_count} Guardias creadas")
        await session.flush()

        # ── 16. Avisos ────────────────────────────────────────────────────────
        aviso_count = 0
        aviso_specs = [
            {"alcance": "Global", "severidad": "Info", "titulo": "Inicio de inscripciones 2026", "cuerpo": "Las inscripciones al ciclo 2026 están abiertas del 1 al 30 de julio.", "requiere_ack": False, "inicio_en": _months_ago(1), "fin_en": _now() + timedelta(days=60)},
            {"alcance": "PorMateria", "severidad": "Advertencia", "titulo": "Cambio de aula PRO101", "cuerpo": "La clase del martes 25/06 se traslada al aula 304.", "materia": "PRO101", "requiere_ack": True, "inicio_en": _months_ago(0.5), "fin_en": _now() + timedelta(days=10)},
            {"alcance": "PorCohorte", "severidad": "Critico", "titulo": "Fecha límite entrega TP MAT101", "cuerpo": "El TP integrador de MAT101 vence el 30/06. Sin prórroga.", "cohorte": ("ISI", "2024"), "requiere_ack": True, "inicio_en": _months_ago(0.3), "fin_en": _now() + timedelta(days=15)},
            {"alcance": "PorRol", "severidad": "Info", "titulo": "Reunión de profesores", "cuerpo": "Reunión obligatoria de todos los profesores el viernes 28/06 a las 18:00.", "rol_destino": "PROFESOR", "requiere_ack": True, "inicio_en": _months_ago(0.2), "fin_en": _now() + timedelta(days=5)},
            {"alcance": "Global", "severidad": "Info", "titulo": "Feriado nacional 20 de junio", "cuerpo": "Recordamos que el 20 de junio es feriado nacional. No hay actividades.", "requiere_ack": False, "inicio_en": _now() - timedelta(days=5), "fin_en": _now() + timedelta(days=30)},
        ]
        for av in aviso_specs:
            materia_id_val = materia_ids.get(av.get("materia", "")) if av.get("materia") else None
            cohorte_val = av.get("cohorte")
            cohorte_id_val = None
            if cohorte_val:
                cohorte_id_val = cohorte_ids.get(cohorte_val[0], {}).get(cohorte_val[1])

            session.add(Aviso(
                tenant_id=tenant_id,
                alcance=av["alcance"],
                materia_id=materia_id_val,
                cohorte_id=cohorte_id_val,
                rol_destino=av.get("rol_destino"),
                severidad=av["severidad"],
                titulo=av["titulo"],
                cuerpo=av["cuerpo"],
                inicio_en=av["inicio_en"],
                fin_en=av["fin_en"],
                requiere_ack=av["requiere_ack"],
            ))
            aviso_count += 1
        print(f"[ok]   {aviso_count} Avisos creados")
        await session.flush()

        # ── 17. AcknowledgmentAviso ──────────────────────────────────────────
        # find avisos that require ack
        ack_count = 0
        result = await session.execute(
            select(Aviso).where(
                Aviso.tenant_id == tenant_id,
                Aviso.requiere_ack.is_(True),
                Aviso.deleted_at.is_(None),
            )
        )
        avisos_ack = result.scalars().all()
        ack_targets = [
            ("alumno1@demo.com", "Cambio de aula PRO101"),
            ("alumno2@demo.com", "Cambio de aula PRO101"),
            ("prof1@demo.com", "Reunión de profesores"),
            ("prof2@demo.com", "Reunión de profesores"),
        ]
        for alumno_email, titulo_aviso in ack_targets:
            aviso = next((a for a in avisos_ack if a.titulo == titulo_aviso), None)
            if not aviso:
                continue
            session.add(AcknowledgmentAviso(
                tenant_id=tenant_id,
                aviso_id=aviso.id,
                usuario_id=usuario_ids[alumno_email],
            ))
            ack_count += 1
        if ack_count:
            print(f"[ok]   {ack_count} AcknowledgmentAviso creados")
        await session.flush()

        # ── 18. Comunicacion ──────────────────────────────────────────────────
        comm_count = 0
        lote_id = uuid.uuid4()
        comm_specs = [
            ("MAT101", "alumno1@demo.com", "Resultado parcial MAT101", "Tu nota del 1er Parcial ya está disponible en el sistema.", "Pendiente", True, "prof1@demo.com"),
            ("MAT101", "alumno2@demo.com", "Resultado parcial MAT101", "Tu nota del 1er Parcial ya está disponible.", "Pendiente", True, "prof1@demo.com"),
            ("PRO101", "alumno1@demo.com", "Recordatorio TP Integrador", "La fecha de entrega del TP Integrador es este viernes.", "Enviado", False, "prof2@demo.com"),
            ("PRO101", "alumno2@demo.com", "Recordatorio TP Integrador", "La fecha de entrega del TP Integrador es este viernes.", "Enviado", False, "prof2@demo.com"),
            ("PRO101", "alumno3@demo.com", "Recordatorio TP Integrador", "La fecha de entrega del TP Integrador es este viernes.", "Error", False, "prof2@demo.com"),
            ("MAT101", "alumno1@demo.com", "Horarios de consulta", "Se agregaron nuevos horarios de consulta para MAT101.", "Cancelado", True, "prof1@demo.com"),
            ("MAT101", "alumno3@demo.com", "Recuperatorio MAT101", "Te recordamos que el recuperatorio es el 5 de julio.", "Pendiente", False, "prof1@demo.com"),
            ("PRO101", "alumno4@demo.com", "Bienvenida PRO101", "Bienvenido a Programación I. Tus credenciales de Moodle ya están activas.", "Enviado", False, "prof2@demo.com"),
        ]
        for cod_materia, alumno_email, asunto, cuerpo, estado, aprobada, enviado_por_email in comm_specs:
            result = await session.execute(
                select(Comunicacion).where(
                    Comunicacion.tenant_id == tenant_id,
                    Comunicacion.lote_id == lote_id,
                    Comunicacion.destinatario == crypto.encrypt(alumno_email),
                )
            )
            if result.scalar_one_or_none():
                continue

            kwargs = dict(
                tenant_id=tenant_id,
                enviado_por=usuario_ids[enviado_por_email],
                materia_id=materia_ids[cod_materia],
                destinatario=crypto.encrypt(alumno_email),
                asunto=asunto,
                cuerpo=cuerpo,
                estado=estado,
                lote_id=lote_id,
            )
            if estado == "Enviado":
                kwargs["enviado_at"] = _now() - timedelta(days=2)
            if aprobada:
                kwargs["aprobado_at"] = _now() - timedelta(days=3)
                kwargs["aprobado_por"] = usuario_ids["coord@demo.com"]

            session.add(Comunicacion(**kwargs))
            comm_count += 1
        print(f"[ok]   {comm_count} Comunicaciones creadas")
        await session.flush()

        # ── 19. Tarea + ComentarioTarea ──────────────────────────────────────
        tarea_count = 0
        tarea_ids_list: list[uuid.UUID] = []

        tarea_specs = [
            ("coord@demo.com", "prof1@demo.com", "MAT101", "Revisar planificación MAT101 2026", "Pendiente"),
            ("coord@demo.com", "tutor1@demo.com", "MAT101", "Actualizar guía de ejercicios MAT101", "En progreso"),
            ("coord@demo.com", "prof2@demo.com", "PRO101", "Cargar notas finales PRO101", "Resuelta"),
            ("admin@demo.com", "finanzas@demo.com", None, "Revisar liquidaciones junio", "Pendiente"),
            ("coord@demo.com", "prof4@demo.com", "BD101", "Preparar material TP2 BD101", "En progreso"),
        ]
        for asignado_por_email, asignado_a_email, cod_materia, descripcion, estado in tarea_specs:
            tid = uuid.uuid4()
            tarea_ids_list.append(tid)
            tarea_count += 1
            session.add(Tarea(
                id=tid,
                tenant_id=tenant_id,
                materia_id=materia_ids.get(cod_materia) if cod_materia else None,
                asignado_a=usuario_ids[asignado_a_email],
                asignado_por=usuario_ids[asignado_por_email],
                estado=estado,
                descripcion=descripcion,
            ))
        print(f"[ok]   {tarea_count} Tareas creadas")
        # Flush para que las Tareas existan antes de los Comentarios
        await session.flush()

        # Comentarios
        comment_count = 0
        comment_specs = [
            (0, "tutor1@demo.com", "Voy a actualizar la guía esta semana."),
            (1, "coord@demo.com", "Perfecto, avísame cuando esté lista."),
            (0, "tutor1@demo.com", "Ya empecé con los primeros 3 temas."),
            (2, "prof2@demo.com", "Notas cargadas correctamente."),
            (2, "coord@demo.com", "Gracias, Roberto. Reviso y confirmo."),
            (4, "prof4@demo.com", "Estoy trabajando en el material teórico."),
            (4, "coord@demo.com", "Genial. Necesito el borrador para el viernes."),
            (3, "admin@demo.com", "Las liquidaciones de mayo ya están listas para revisión."),
        ]
        for tarea_idx, autor_email, texto in comment_specs:
            if tarea_idx >= len(tarea_ids_list):
                continue
            session.add(ComentarioTarea(
                tenant_id=tenant_id,
                tarea_id=tarea_ids_list[tarea_idx],
                autor_id=usuario_ids[autor_email],
                texto=texto,
            ))
            comment_count += 1
        print(f"[ok]   {comment_count} Comentarios de tarea creados")
        await session.flush()

        # ── 20. SalarioBase ──────────────────────────────────────────────────
        salario_count = 0
        salario_base_specs = [
            ("ADMIN", 500000.00, date(2026, 1, 1)),
            ("PROFESOR", 350000.00, date(2026, 1, 1)),
            ("TUTOR", 180000.00, date(2026, 1, 1)),
            ("COORDINADOR", 420000.00, date(2026, 1, 1)),
            ("FINANZAS", 380000.00, date(2026, 1, 1)),
        ]
        for rol, monto, desde in salario_base_specs:
            result = await session.execute(
                select(SalarioBase).where(
                    SalarioBase.tenant_id == tenant_id,
                    SalarioBase.rol == rol,
                )
            )
            if result.scalar_one_or_none():
                continue
            session.add(SalarioBase(tenant_id=tenant_id, rol=rol, monto=monto, desde=desde))
            salario_count += 1
        print(f"[ok]   {salario_count} SalarioBase creados")
        await session.flush()

        # ── 21. SalarioPlus ──────────────────────────────────────────────────
        salario_plus_count = 0
        salario_plus_specs = [
            ("PROG", "PROFESOR", "Plus por materia Programación", 85000.00, date(2026, 1, 1)),
            ("BD", "PROFESOR", "Plus por materia Base de Datos", 75000.00, date(2026, 1, 1)),
            ("REDES", "PROFESOR", "Plus por materia Redes", 70000.00, date(2026, 1, 1)),
        ]
        for clave, rol, descripcion, monto, desde in salario_plus_specs:
            result = await session.execute(
                select(SalarioPlus).where(
                    SalarioPlus.tenant_id == tenant_id,
                    SalarioPlus.clave == clave,
                    SalarioPlus.rol == rol,
                )
            )
            if result.scalar_one_or_none():
                continue
            session.add(SalarioPlus(tenant_id=tenant_id, clave=clave, rol=rol, descripcion=descripcion, monto=monto, desde=desde))
            salario_plus_count += 1
        print(f"[ok]   {salario_plus_count} SalarioPlus creados")
        await session.flush()

        # ── 22. Liquidacion ──────────────────────────────────────────────────
        liq_count = 0
        liq_specs = [
            ("prof1@demo.com", "ISI", "2024", 5, 2026, "PROFESOR", ["COM-A", "COM-B"], 350000.00, 85000.00, 435000.00, {"PROG": {"comisiones": 2, "monto": 85000.00, "total": 85000.00}}, "Abierta", None),
            ("prof2@demo.com", "ISI", "2024", 5, 2026, "PROFESOR", ["COM-A", "COM-B"], 350000.00, 170000.00, 520000.00, {"PROG": {"comisiones": 2, "monto": 85000.00, "total": 170000.00}}, "Abierta", None),
            ("tutor1@demo.com", "ISI", "2024", 5, 2026, "TUTOR", ["COM-A"], 180000.00, 0.00, 180000.00, {}, "Abierta", None),
            ("prof1@demo.com", "ISI", "2024", 4, 2026, "PROFESOR", ["COM-A"], 350000.00, 85000.00, 435000.00, {"PROG": {"comisiones": 1, "monto": 85000.00, "total": 85000.00}}, "Cerrada", _now() - timedelta(days=15)),
            ("prof2@demo.com", "ISI", "2024", 4, 2026, "PROFESOR", ["COM-A", "COM-B"], 350000.00, 170000.00, 520000.00, {"PROG": {"comisiones": 2, "monto": 85000.00, "total": 170000.00}}, "Cerrada", _now() - timedelta(days=15)),
            ("prof3@demo.com", "ISI", "2024", 5, 2026, "PROFESOR", ["COM-A"], 350000.00, 0.00, 350000.00, {}, "Abierta", None),
            ("tutor2@demo.com", "ISI", "2024", 5, 2026, "TUTOR", ["COM-A", "COM-B"], 180000.00, 0.00, 180000.00, {}, "Abierta", None),
            ("tutor3@demo.com", "ISI", "2024", 4, 2026, "TUTOR", ["COM-A"], 180000.00, 0.00, 180000.00, {}, "Cerrada", _now() - timedelta(days=15)),
        ]
        for liq_email, cod_carrera, cod_cohorte, mes, anio, rol, comisiones, base, plus, total, desglose, estado, cerrada_at in liq_specs:
            session.add(Liquidacion(
                tenant_id=tenant_id,
                usuario_id=usuario_ids[liq_email],
                cohorte_id=cohorte_ids[cod_carrera][cod_cohorte],
                periodo_mes=mes,
                periodo_anio=anio,
                rol=rol,
                comisiones=comisiones,
                base_monto=base,
                plus_monto=plus,
                total_monto=total,
                desglose=desglose,
                estado=estado,
                cerrada_at=cerrada_at,
            ))
            liq_count += 1
        print(f"[ok]   {liq_count} Liquidaciones creadas")
        await session.flush()

        # ── 23. Factura ──────────────────────────────────────────────────────
        fact_count = 0
        fact_specs = [
            ("prof2@demo.com", 5, 2026, "Honorarios mayo 2026 - Programación I", 520000.00, "Pendiente", None),
            ("prof2@demo.com", 4, 2026, "Honorarios abril 2026 - Programación I", 520000.00, "Abonada", _now() - timedelta(days=10)),
            ("prof1@demo.com", 5, 2026, "Honorarios mayo 2026 - Matemática I y II", 435000.00, "Pendiente", None),
        ]
        for email_fact, mes, anio, detalle, monto, estado, abonada_at in fact_specs:
            session.add(Factura(
                tenant_id=tenant_id,
                usuario_id=usuario_ids[email_fact],
                periodo_mes=mes,
                periodo_anio=anio,
                detalle=detalle,
                monto=monto,
                estado=estado,
                abonada_at=abonada_at,
            ))
            fact_count += 1
        print(f"[ok]   {fact_count} Facturas creadas")
        await session.flush()

        # ── 24. AuditLog ─────────────────────────────────────────────────────
        audit_count = 0
        audit_specs = [
            ("admin@demo.com", None, None, "auth:login_exitoso", {"metodo": "password", "ip": "192.168.1.100"}, 1, "192.168.1.100", "Mozilla/5.0"),
            ("admin@demo.com", None, None, "usuario:crear", {"email_hash": "demo"}, 1, "192.168.1.100", "Mozilla/5.0"),
            ("coord@demo.com", None, "MAT101", "calificacion:importar", {"actividad": "1er Parcial", "filas": 25}, 25, "10.0.0.1", "curl/7.88"),
            ("coord@demo.com", "coord@demo.com", None, "comunicacion:enviar", {"lote_id": str(lote_id), "destinatarios": 3}, 3, "10.0.0.1", "PostmanRuntime/7.36"),
            ("prof1@demo.com", None, "MAT101", "comunicacion:aprobar", {"lote_id": str(lote_id)}, 1, "10.0.0.1", "Python/3.13"),
        ]
        for actor_email, impersonado_email, materia_cod, accion, detalle, filas, ip, ua in audit_specs:
            session.add(AuditLog(
                tenant_id=tenant_id,
                actor_id=usuario_ids[actor_email],
                impersonado_id=usuario_ids[impersonado_email] if impersonado_email else None,
                materia_id=materia_ids.get(materia_cod) if materia_cod else None,
                accion=accion,
                detalle=detalle,
                filas_afectadas=filas,
                ip=ip,
                user_agent=ua,
            ))
            audit_count += 1
        print(f"[ok]   {audit_count} AuditLog creados")
        await session.flush()

        # ── 25. Mensaje ──────────────────────────────────────────────────────
        msg_count = 0
        thread_1 = uuid.uuid4()
        thread_2 = uuid.uuid4()
        thread_3 = uuid.uuid4()
        msg_specs = [
            ("coord@demo.com", "prof1@demo.com", thread_1, "Planificación MAT101", "María, ¿viste la planificación que subí?", _now() - timedelta(days=5)),
            ("prof1@demo.com", "coord@demo.com", thread_1, None, "Sí, la revisé. Me parece bien.", _now() - timedelta(days=4)),
            ("coord@demo.com", "prof1@demo.com", thread_1, None, "Perfecto, entonces la damos por aprobada.", _now() - timedelta(days=4), True),
            ("admin@demo.com", "finanzas@demo.com", thread_2, "Liquidaciones junio", "Carlos, necesito las liquidaciones de junio para el jueves.", _now() - timedelta(days=2)),
            ("finanzas@demo.com", "admin@demo.com", thread_2, None, "Ok, las estoy terminando.", _now() - timedelta(days=1)),
            ("tutor1@demo.com", "prof1@demo.com", thread_3, "Consulta alumnos MAT101", "Roberto, tengo varios alumnos preguntando por el recuperatorio.", _now() - timedelta(hours=3)),
        ]
        for rem_email, dest_email, thread_id, asunto, cuerpo, creado_at, *extra in msg_specs:
            leido = extra[0] if extra else False
            session.add(Mensaje(
                tenant_id=tenant_id,
                thread_id=thread_id,
                remitente_id=usuario_ids[rem_email],
                destinatario_id=usuario_ids[dest_email],
                asunto=asunto,
                cuerpo=cuerpo,
                leido_at=_now() if leido else None,
                created_at=creado_at,
            ))
            msg_count += 1
        print(f"[ok]   {msg_count} Mensajes creados")
        await session.flush()

        # ── 26. ProgramaMateria + FechaAcademica ─────────────────────────────
        prog_count = 0
        prog_specs = [
            ("MAT101", "ISI", "2024", "Programa de Matemática I - ISI 2024", "files/programas/mat101_isi_2024.pdf"),
            ("PRO101", "ISI", "2024", "Programa de Programación I - ISI 2024", "files/programas/pro101_isi_2024.pdf"),
            ("BD101", "ISI", "2024", "Programa de Base de Datos I - ISI 2024", "files/programas/bd101_isi_2024.pdf"),
        ]
        for cod_materia, cod_carrera, cod_cohorte, titulo, ref_archivo in prog_specs:
            session.add(ProgramaMateria(
                tenant_id=tenant_id,
                materia_id=materia_ids[cod_materia],
                carrera_id=carrera_ids[cod_carrera],
                cohorte_id=cohorte_ids[cod_carrera][cod_cohorte],
                titulo=titulo,
                referencia_archivo=ref_archivo,
            ))
            prog_count += 1
        print(f"[ok]   {prog_count} ProgramaMateria creados")

        fecha_count = 0
        fecha_specs = [
            ("MAT101", "ISI", "2024", "Parcial", 1, "2026-1", date(2026, 4, 15), "1er Parcial MAT101"),
            ("MAT101", "ISI", "2024", "Parcial", 2, "2026-1", date(2026, 6, 10), "2do Parcial MAT101"),
            ("PRO101", "ISI", "2024", "Parcial", 1, "2026-1", date(2026, 4, 22), "1er Parcial PRO101"),
            ("PRO101", "ISI", "2024", "TP", 1, "2026-1", date(2026, 5, 20), "Entrega TP Integrador PRO101"),
            ("PRO101", "ISI", "2024", "Recuperatorio", 1, "2026-1", date(2026, 7, 5), "Recuperatorio PRO101"),
        ]
        for cod_materia, cod_carrera, cod_cohorte, tipo, numero, periodo, fecha, titulo in fecha_specs:
            session.add(FechaAcademica(
                tenant_id=tenant_id,
                materia_id=materia_ids[cod_materia],
                cohorte_id=cohorte_ids[cod_carrera][cod_cohorte],
                tipo=tipo,
                numero=numero,
                periodo=periodo,
                fecha=fecha,
                titulo=titulo,
            ))
            fecha_count += 1
        print(f"[ok]   {fecha_count} FechaAcademica creadas")
        await session.flush()

        # ── COMMIT ────────────────────────────────────────────────────────────
        await session.commit()

    await engine.dispose()

    total_users = len(USUARIO_DATA)
    print()
    print("=" * 60)
    print("  SEED COMPLETO FINALIZADO")
    print("=" * 60)
    print(f"  Tenant : {TENANT_SLUG}")
    print(f"  Tablas : 26 (todas)")
    print(f"  Usuarios creados/reutilizados: {total_users}")
    print(f"  Password común: {SEED_PASSWORD}")
    print()
    print("  CREDENCIALES POR ROL:")
    print(f"    ADMIN       → admin@demo.com / {SEED_PASSWORD}")
    print(f"    COORDINADOR → coord@demo.com / {SEED_PASSWORD}")
    print(f"    FINANZAS    → finanzas@demo.com / {SEED_PASSWORD}")
    print(f"    NEXO        → nexo@demo.com / {SEED_PASSWORD}")
    print(f"    PROFESOR    → prof1..4@demo.com / {SEED_PASSWORD}")
    print(f"    TUTOR       → tutor1..3@demo.com / {SEED_PASSWORD}")
    print(f"    ALUMNO      → alumno1..10@demo.com / {SEED_PASSWORD}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
