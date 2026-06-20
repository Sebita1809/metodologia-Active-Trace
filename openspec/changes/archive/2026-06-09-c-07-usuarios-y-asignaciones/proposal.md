## Why

La plataforma ya tiene tenancy, auth, RBAC, audit log y el catálogo académico (Carrera, Cohorte, Materia de C-06), pero todavía no modela **quién es cada persona del tenant** ni **qué hace, dónde y cuándo**. Sin `Usuario` (la ficha de personas con datos fiscales/PII) y sin `Asignacion` (el contexto académico: quién dicta qué materia, en qué carrera/cohorte/comisiones, durante qué período y a cargo de quién), ningún módulo de dominio posterior (equipos, padrón, calificaciones, comunicaciones, liquidaciones) puede arrancar. Es el siguiente eslabón del camino crítico tras C-06.

## What Changes

- Nuevo modelo **`Usuario`** (tabla `usuario`) — ficha de persona del tenant con PII cifrada AES-256 (`email`, `dni`, `cuil`, `cbu`, `alias_cbu`) usando el `CryptoService` ya existente. Identidad por UUID interno; `legajo` es atributo de negocio, nunca credencial. Unicidad `(tenant_id, email)`.
- Nuevo modelo **`Asignacion`** (tabla `asignacion`) — vincula `Usuario` ↔ rol de negocio (PROFESOR | TUTOR | COORDINADOR | NEXO | ADMIN | FINANZAS) ↔ contexto académico (`materia_id`, `carrera_id`, `cohorte_id`, `comisiones`), con jerarquía vía `responsable_id`, vigencia `desde`/`hasta` y `estado_vigencia` **derivado** (Vigente | Vencida), nunca persistido.
- ABM de usuarios bajo `/api/admin/usuarios` con guard `require_permission("usuarios:gestionar")` (solo ADMIN).
- CRUD de asignaciones bajo `/api/asignaciones` con guard `require_permission("equipos:asignar")` (ADMIN, COORDINADOR), con filtros por materia/carrera/cohorte/usuario/rol/responsable.
- **Migración 007** crea las tablas `usuario` y `asignacion` con índices únicos y constraints.
- PII nunca aparece en logs ni en texto plano en ninguna capa; las respuestas de API descifran on-read controladamente.
- Una asignación vencida **no** otorga permisos pero se conserva para el histórico de auditoría.

## Capabilities

### New Capabilities
- `usuario`: ficha de persona del tenant con PII cifrada en reposo, unicidad de email por tenant, identidad por UUID, estado Activo/Inactivo y ABM restringido a ADMIN.
- `asignacion`: vínculo Usuario ↔ rol de negocio ↔ contexto académico con vigencia temporal, `estado_vigencia` derivado, jerarquía por responsable y CRUD bajo permiso `equipos:asignar`.

### Modified Capabilities
*(ninguna — no se modifican requisitos de specs existentes. `usuario`/`asignacion` son capacidades nuevas; el `User` de auth (C-03) permanece intacto como entidad separada.)*

## Impact

- **Modelos**: nuevos `backend/app/models/usuario.py`, `backend/app/models/asignacion.py`.
- **Migración**: nueva `backend/alembic/versions/007_usuarios_y_asignaciones.py`.
- **Repositories / Services / Schemas / Routers**: nuevos archivos por cada entidad bajo `backend/app/repositories/`, `services/`, `schemas/`, `api/v1/routers/`.
- **Dependencias internas**: usa `CryptoService` (`backend/app/core/crypto.py`), `BaseTenantModel`, `BaseRepository`, FKs a `carrera`/`cohorte`/`materia` (C-06).
- **RBAC**: consume permisos ya sembrados `usuarios:gestionar`, `equipos:asignar`, `asignaciones:gestionar`. La migración 007 los siembra defensivamente si faltaran.
- **Sin frontend** (C-24) ni importación masiva en este change.
- **Coexistencia con `User` (auth)**: `Usuario` (dominio/ficha) y `User` (credenciales) son entidades distintas y no se fusionan en este change.
