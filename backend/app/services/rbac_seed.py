"""
app/services/rbac_seed.py — Idempotent RBAC seed helper.

Seeds the 7 domain roles, the permission catalog and the base role×permission
matrix derived from knowledge-base/03_actores_y_roles.md §3.3 for a given
tenant_id. Idempotent: re-running does not create duplicate rows (upsert by
clave/nombre within the tenant).

Usage:
  - From Alembic migration: seed_rbac_for_tenant(bind, tenant_id)
  - From application bootstrap when creating a new tenant:
      async with session: await async_seed_rbac_for_tenant(session, tenant_id)

Implemented: C-04 (rbac-permisos-finos)
"""
from __future__ import annotations

import uuid
from typing import Any

import sqlalchemy as sa


# ---------------------------------------------------------------------------
# Domain roles
# ---------------------------------------------------------------------------

DOMAIN_ROLES: list[dict[str, str]] = [
    {"nombre": "ALUMNO",      "descripcion": "Estudiante que cursa materias"},
    {"nombre": "TUTOR",       "descripcion": "Auxiliar/ayudante de cátedra"},
    {"nombre": "PROFESOR",    "descripcion": "Docente a cargo de comisiones"},
    {"nombre": "COORDINADOR", "descripcion": "Responsable de materias o cohortes"},
    {"nombre": "NEXO",        "descripcion": "Rol de articulación transversal"},
    {"nombre": "ADMIN",       "descripcion": "Administrador del tenant"},
    {"nombre": "FINANZAS",    "descripcion": "Responsable de liquidaciones y honorarios"},
]

# ---------------------------------------------------------------------------
# Permission catalog — all `modulo:accion` keys used in the matrix
# ---------------------------------------------------------------------------

PERMISSIONS: list[dict[str, str]] = [
    # estado académico
    {"clave": "academico:ver_propio",       "modulo": "academico",      "accion": "ver_propio",       "descripcion": "Ver estado académico propio"},
    # evaluaciones
    {"clave": "evaluacion:reservar",        "modulo": "evaluacion",     "accion": "reservar",         "descripcion": "Reservar instancia de evaluación"},
    # avisos
    {"clave": "avisos:confirmar",           "modulo": "avisos",         "accion": "confirmar",        "descripcion": "Confirmar avisos (acknowledgment)"},
    {"clave": "avisos:publicar",            "modulo": "avisos",         "accion": "publicar",         "descripcion": "Publicar avisos"},
    # calificaciones
    {"clave": "calificaciones:importar",    "modulo": "calificaciones", "accion": "importar",         "descripcion": "Importar calificaciones"},
    # atrasados
    {"clave": "atrasados:ver",              "modulo": "atrasados",      "accion": "ver",              "descripcion": "Ver alumnos atrasados"},
    # entregas
    {"clave": "entregas:ver_sin_corregir",  "modulo": "entregas",       "accion": "ver_sin_corregir", "descripcion": "Detectar entregas sin corregir"},
    # comunicacion
    {"clave": "comunicacion:enviar",        "modulo": "comunicacion",   "accion": "enviar",           "descripcion": "Enviar comunicaciones a alumnos"},
    {"clave": "comunicacion:aprobar",       "modulo": "comunicacion",   "accion": "aprobar",          "descripcion": "Aprobar comunicaciones masivas"},
    # encuentros
    {"clave": "encuentros:gestionar",       "modulo": "encuentros",     "accion": "gestionar",        "descripcion": "Gestionar encuentros"},
    # guardias
    {"clave": "guardias:registrar",         "modulo": "guardias",       "accion": "registrar",        "descripcion": "Registrar guardias"},
    # tareas
    {"clave": "tareas:gestionar",           "modulo": "tareas",         "accion": "gestionar",        "descripcion": "Gestionar tareas internas"},
    # equipos
    {"clave": "equipos:asignar",            "modulo": "equipos",        "accion": "asignar",          "descripcion": "Gestionar equipos docentes (asignaciones)"},
    # estructura académica
    {"clave": "estructura:gestionar",       "modulo": "estructura",     "accion": "gestionar",        "descripcion": "Gestionar estructura académica (carreras, cohortes, materias)"},
    # usuarios
    {"clave": "usuarios:gestionar",         "modulo": "usuarios",       "accion": "gestionar",        "descripcion": "Gestionar usuarios del tenant"},
    # auditoria
    {"clave": "auditoria:ver",              "modulo": "auditoria",      "accion": "ver",              "descripcion": "Ver auditoría"},
    # liquidaciones
    {"clave": "liquidaciones:operar_grilla","modulo": "liquidaciones",  "accion": "operar_grilla",    "descripcion": "Operar grilla salarial"},
    {"clave": "liquidaciones:cerrar",       "modulo": "liquidaciones",  "accion": "cerrar",           "descripcion": "Calcular / cerrar liquidaciones"},
    {"clave": "liquidaciones:facturas",     "modulo": "liquidaciones",  "accion": "facturas",         "descripcion": "Gestionar facturas"},
    # configuracion
    {"clave": "tenant:configurar",          "modulo": "tenant",         "accion": "configurar",       "descripcion": "Configurar el tenant"},
    # impersonacion (mechanism implemented in C-05)
    {"clave": "impersonacion:usar",         "modulo": "impersonacion",  "accion": "usar",             "descripcion": "Impersonar un usuario (soporte)"},
    # rbac administration
    {"clave": "rbac:administrar",           "modulo": "rbac",           "accion": "administrar",      "descripcion": "Administrar catálogo RBAC (roles, permisos, matriz)"},
    {"clave": "rbac:ver",                   "modulo": "rbac",           "accion": "ver",              "descripcion": "Ver catálogo RBAC"},
    # padron (C-09)
    {"clave": "padron:cargar",              "modulo": "padron",         "accion": "cargar",           "descripcion": "Cargar padrón de alumnos"},
    {"clave": "padron:ver",                 "modulo": "padron",         "accion": "ver",              "descripcion": "Ver padrón de alumnos"},
    {"clave": "padron:vaciar",              "modulo": "padron",         "accion": "vaciar",           "descripcion": "Vaciar padrón de alumnos"},
    # calificaciones (C-10)
    {"clave": "calificaciones:ver",         "modulo": "calificaciones", "accion": "ver",              "descripcion": "Ver calificaciones"},
    {"clave": "calificaciones:configurar",  "modulo": "calificaciones", "accion": "configurar",       "descripcion": "Configurar umbral de calificaciones"},
    # analisis (C-11)
    {"clave": "analisis:ver",               "modulo": "analisis",       "accion": "ver",              "descripcion": "Ver análisis académico (atrasados, ranking, notas finales, reporte)"},
]

# ---------------------------------------------------------------------------
# Role × Permission matrix from §3.3
# Format: (rol_nombre, permiso_clave, alcance)
# alcance: "global" | "propio"
# NEXO: seeded without permissions (OQ-C04-01 / PA-25 unresolved)
# ---------------------------------------------------------------------------

MATRIX: list[tuple[str, str, str]] = [
    # ALUMNO
    ("ALUMNO", "academico:ver_propio",       "global"),
    ("ALUMNO", "evaluacion:reservar",        "global"),
    ("ALUMNO", "avisos:confirmar",           "global"),

    # TUTOR
    ("TUTOR",  "avisos:confirmar",           "global"),
    ("TUTOR",  "atrasados:ver",              "global"),
    ("TUTOR",  "entregas:ver_sin_corregir",  "global"),
    ("TUTOR",  "encuentros:gestionar",       "global"),
    ("TUTOR",  "guardias:registrar",         "propio"),

    # PROFESOR
    ("PROFESOR", "avisos:confirmar",         "global"),
    ("PROFESOR", "calificaciones:importar",  "propio"),
    ("PROFESOR", "atrasados:ver",            "propio"),
    ("PROFESOR", "entregas:ver_sin_corregir","propio"),
    ("PROFESOR", "comunicacion:enviar",      "propio"),
    ("PROFESOR", "encuentros:gestionar",     "propio"),
    ("PROFESOR", "guardias:registrar",       "propio"),
    ("PROFESOR", "tareas:gestionar",         "propio"),

    # COORDINADOR
    ("COORDINADOR", "avisos:confirmar",          "global"),
    ("COORDINADOR", "calificaciones:importar",   "global"),
    ("COORDINADOR", "atrasados:ver",             "global"),
    ("COORDINADOR", "entregas:ver_sin_corregir", "global"),
    ("COORDINADOR", "comunicacion:enviar",       "global"),
    ("COORDINADOR", "comunicacion:aprobar",      "global"),
    ("COORDINADOR", "encuentros:gestionar",      "global"),
    ("COORDINADOR", "guardias:registrar",        "global"),
    ("COORDINADOR", "tareas:gestionar",          "global"),
    ("COORDINADOR", "avisos:publicar",           "global"),
    ("COORDINADOR", "equipos:asignar",           "global"),
    ("COORDINADOR", "auditoria:ver",             "propio"),

    # ADMIN
    ("ADMIN", "avisos:confirmar",          "global"),
    ("ADMIN", "calificaciones:importar",   "global"),
    ("ADMIN", "atrasados:ver",             "global"),
    ("ADMIN", "entregas:ver_sin_corregir", "global"),
    ("ADMIN", "comunicacion:enviar",       "global"),
    ("ADMIN", "comunicacion:aprobar",      "global"),
    ("ADMIN", "encuentros:gestionar",      "global"),
    ("ADMIN", "guardias:registrar",        "global"),
    ("ADMIN", "tareas:gestionar",          "global"),
    ("ADMIN", "avisos:publicar",           "global"),
    ("ADMIN", "equipos:asignar",           "global"),
    ("ADMIN", "estructura:gestionar",      "global"),
    ("ADMIN", "usuarios:gestionar",        "global"),
    ("ADMIN", "auditoria:ver",             "global"),
    ("ADMIN", "tenant:configurar",         "global"),
    ("ADMIN", "impersonacion:usar",        "global"),  # OQ-C04-03: seeded for ADMIN
    ("ADMIN", "rbac:administrar",          "global"),
    ("ADMIN", "rbac:ver",                  "global"),

    # FINANZAS
    ("FINANZAS", "avisos:confirmar",           "global"),
    ("FINANZAS", "auditoria:ver",              "global"),
    ("FINANZAS", "liquidaciones:operar_grilla","global"),
    ("FINANZAS", "liquidaciones:cerrar",       "global"),
    ("FINANZAS", "liquidaciones:facturas",     "global"),

    # NEXO — intentionally no permissions (OQ-C04-01 / PA-25 unresolved)

    # PROFESOR — padron (C-09)
    ("PROFESOR", "padron:cargar",  "propio"),
    ("PROFESOR", "padron:ver",     "propio"),
    ("PROFESOR", "padron:vaciar",  "propio"),

    # COORDINADOR — padron (C-09)
    ("COORDINADOR", "padron:cargar",  "global"),
    ("COORDINADOR", "padron:ver",     "global"),
    ("COORDINADOR", "padron:vaciar",  "global"),

    # ADMIN — padron (C-09)
    ("ADMIN", "padron:cargar",  "global"),
    ("ADMIN", "padron:ver",     "global"),
    ("ADMIN", "padron:vaciar",  "global"),

    # PROFESOR — calificaciones (C-10)
    ("PROFESOR", "calificaciones:ver",        "propio"),
    ("PROFESOR", "calificaciones:configurar", "propio"),

    # COORDINADOR — calificaciones (C-10)
    ("COORDINADOR", "calificaciones:ver",        "global"),
    ("COORDINADOR", "calificaciones:configurar", "global"),

    # ADMIN — calificaciones (C-10)
    ("ADMIN", "calificaciones:ver",        "global"),
    ("ADMIN", "calificaciones:configurar", "global"),

    # TUTOR — analisis (C-11)
    ("TUTOR", "analisis:ver", "global"),

    # PROFESOR — analisis (C-11)
    ("PROFESOR", "analisis:ver", "propio"),

    # COORDINADOR — analisis (C-11)
    ("COORDINADOR", "analisis:ver", "global"),

    # ADMIN — analisis (C-11)
    ("ADMIN", "analisis:ver", "global"),
]


# ---------------------------------------------------------------------------
# Synchronous seed (used from Alembic migrations which run on a sync bind)
# ---------------------------------------------------------------------------

def seed_rbac_for_tenant(bind: Any, tenant_id: Any) -> None:
    """Idempotently seed roles, permissions and the matrix for *tenant_id*.

    Uses raw SQL so it can be called from both sync Alembic migrations and
    async application code (via run_sync). Upsert strategy:
      - Roles / permisos: INSERT ... ON CONFLICT DO NOTHING
      - rol_permiso: INSERT ... ON CONFLICT DO NOTHING (unique on tenant+rol+permiso)

    Parameters
    ----------
    bind:
        A SQLAlchemy connectable (sync Connection from Alembic op.get_bind(),
        or a sync connection obtained via run_sync in async contexts).
    tenant_id:
        UUID of the tenant to seed. Accepts uuid.UUID or string.
    """
    if not isinstance(tenant_id, uuid.UUID):
        tenant_id = uuid.UUID(str(tenant_id))

    tid = str(tenant_id)

    # -- 1. Upsert roles ----------------------------------------------------
    for role_data in DOMAIN_ROLES:
        bind.execute(
            sa.text(
                """
                INSERT INTO roles (id, tenant_id, nombre, descripcion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tenant_id, :nombre, :descripcion, now(), now())
                ON CONFLICT (tenant_id, nombre) DO NOTHING
                """
            ),
            {"tenant_id": tid, "nombre": role_data["nombre"], "descripcion": role_data["descripcion"]},
        )

    # -- 2. Upsert permissions -----------------------------------------------
    for perm_data in PERMISSIONS:
        bind.execute(
            sa.text(
                """
                INSERT INTO permisos (id, clave, modulo, accion, descripcion, tenant_id, created_at, updated_at)
                VALUES (gen_random_uuid(), :clave, :modulo, :accion, :descripcion, :tenant_id, now(), now())
                ON CONFLICT (tenant_id, clave) DO NOTHING
                """
            ),
            {
                "tenant_id": tid,
                "clave": perm_data["clave"],
                "modulo": perm_data["modulo"],
                "accion": perm_data["accion"],
                "descripcion": perm_data["descripcion"],
            },
        )

    # -- 3. Upsert matrix rows -----------------------------------------------
    for rol_nombre, permiso_clave, alcance in MATRIX:
        bind.execute(
            sa.text(
                """
                INSERT INTO rol_permiso (id, rol_id, permiso_id, alcance, tenant_id, created_at, updated_at)
                SELECT
                    gen_random_uuid(),
                    r.id,
                    p.id,
                    :alcance,
                    :tenant_id,
                    now(),
                    now()
                FROM roles r, permisos p
                WHERE r.tenant_id = :tenant_id AND r.nombre = :rol_nombre
                  AND p.clave  = :permiso_clave
                ON CONFLICT (tenant_id, rol_id, permiso_id) DO NOTHING
                """
            ),
            {
                "tenant_id": tid,
                "rol_nombre": rol_nombre,
                "permiso_clave": permiso_clave,
                "alcance": alcance,
            },
        )


# ---------------------------------------------------------------------------
# Async wrapper (used when creating a new tenant at runtime)
# ---------------------------------------------------------------------------

async def async_seed_rbac_for_tenant(session: Any, tenant_id: Any) -> None:
    """Async-compatible wrapper around seed_rbac_for_tenant.

    Call this from async application code (e.g., tenant creation service).
    Runs the sync seed via run_sync on the session's connection.
    """
    async with session.begin():
        conn = await session.connection()
        await conn.run_sync(seed_rbac_for_tenant, tenant_id)
