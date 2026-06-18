## Why

C-07 habilita el modelo de identidad académica del sistema. Sin usuarios y asignaciones, ningún módulo de dominio puede operar: no hay a quién importar del padrón (C-09), no hay equipos docentes (C-08), no hay destinatarios para comunicaciones (C-12), no hay liquidaciones (C-18). Es el eslabón que conecta la estructura académica (C-06) con toda la operativa del sistema.

Además, introduce el cifrado de PII en reposo —requisito de seguridad crítico— y completa el modelo de autorización iniciado en C-04: una asignación vigente es lo que otorga permisos a un usuario sobre un contexto académico concreto.

## What Changes

- **Nuevo modelo `Usuario`** con UUID interno como identidad, campos PII cifrados con AES-256-GCM (`email`, `dni`, `cuil`, `cbu`, `alias_cbu`), más `nombre`, `apellidos`, `legajo` (atributo de negocio, NO credencial), `regional`, `banco`, `facturador`, `estado` (Activo/Inactivo). Unicidad `(tenant_id, email)`.
- **Nuevo modelo `Asignacion`** que vincula `Usuario` ↔ `Rol` ↔ contexto académico (`Materia`, `Carrera`, `Cohorte`, `comisiones`), con `responsable_id` (jerarquía), vigencia `desde/hasta`, y `estado_vigencia` derivado.
- **Nuevos endpoints `/api/admin/usuarios`** (CRUD completo, guard `usuarios:gestionar`, solo ADMIN).
- **Nuevos endpoints `/api/asignaciones`** (CRUD completo, guard `equipos:asignar`, COORDINADOR y ADMIN).
- **Nuevos permisos en la matriz RBAC**: `usuarios:gestionar` (ADMIN), `equipos:asignar` (COORDINADOR, ADMIN).
- **Migración Alembic 006**: tablas `usuario`, `asignacion`.
- **Columna auxiliar `email_hash`** en `Usuario` para búsqueda determinística por email manteniendo el cifrado AES-256-GCM no-determinístico.

## Capabilities

### New Capabilities
- `user-management`: CRUD de usuarios con PII cifrada en reposo, unicidad por tenant, soft delete (estado Inactivo), legajo como atributo de negocio.
- `role-assignment`: Asignación de roles a usuarios con contexto académico (materia/carrera/cohorte/comisiones), vigencia temporal, jerarquía responsable, y derivación de estado vigente/vencida.

### Modified Capabilities
*(Ninguna. C-07 no modifica specs existentes — introduce capabilities nuevas.)*

## Impact

- **Backend**: Nuevos models (`usuario.py`, `asignacion.py`), repositories (`usuarios/`), services (`usuarios/`), schemas, y routers (`/api/v1/routers/usuarios.py`).
- **Base de datos**: Migración 006 con tablas `usuario`, `asignacion` + seed de permisos `usuarios:gestionar` y `equipos:asignar`.
- **Seguridad**: El AESCipher existente (`app/core/security.py`) se reutiliza para cifrado de PII. Se agrega columna `email_hash` (HMAC-SHA256) para búsqueda sin comprometer el cifrado.
- **RBAC**: Se agregan 2 permisos nuevos a la matriz seed. No se modifican guards existentes.
- **Tests**: Suite completa en `tests/test_usuarios/` con cobertura ≥80% líneas, ≥90% reglas de negocio.
