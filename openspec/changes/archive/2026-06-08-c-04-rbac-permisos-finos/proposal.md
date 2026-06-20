## Why

El sistema ya autentica (C-03 emite el JWT con `user_id`, `tenant_id` y `roles`) pero **no autoriza**: cualquier usuario autenticado puede ejecutar cualquier acción porque no existe ningún control de permisos. La regla de oro del producto exige RBAC con permisos finos `modulo:accion`, fail-closed y como **catálogo de datos administrable** (nunca hardcodeado). C-04 es el último eslabón fundacional de seguridad: sin él, ningún módulo de negocio posterior (C-05 en adelante) puede declarar quién accede a qué. Es prerequisito de GATE 4, que desbloquea tres ramas en paralelo.

## What Changes

- **Modelo de datos del catálogo RBAC** (migración 004):
  - `roles` — catálogo de roles por tenant (seed: ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS). Administrable, no fijo en código.
  - `permisos` — catálogo de capacidades atómicas `modulo:accion` (seed derivado de la matriz §3.3 de `03_actores_y_roles.md`).
  - `rol_permiso` — matriz N:N rol × permiso (los datos de la matriz, NO hardcode). Soporta el marcador de alcance `(propio)` vs global.
  - `usuario_rol` — asignación de roles a usuarios dentro del tenant, con vigencia (`desde`/`hasta`). Es la base mínima para resolver permisos efectivos; la asignación rol↔contexto-académico completa (materia/comisión) llega en C-07.
- **Resolución de permisos efectivos server-side por request**: dado el `user_id` + `tenant_id` del JWT verificado, se calcula la **unión** de permisos de todos los roles vigentes del usuario, acotada por tenant. Los permisos **nunca** se leen del JWT; se resuelven contra la BD en cada petición (alineado con C-03 design §3.1).
- **Guard `require_permission("modulo:accion")`**: dependency de FastAPI que cada endpoint declara. **Fail-closed**: si el usuario no tiene el permiso → `403`. Soporta evaluación de alcance `(propio)`.
- **Seed idempotente** de la matriz base rol × permiso (los 7 roles del dominio + sus permisos según §3.3), aplicado por tenant.
- **API de administración del catálogo** (CRUD de roles, permisos y matriz), protegida por permisos del propio módulo (`rbac:*`), para que ADMIN administre la matriz sin tocar código.
- **Tests** (≥90% reglas de negocio): usuario sin permiso → 403; unión de permisos de múltiples roles; permiso `(propio)` vs global; asignación no vigente no otorga acceso; aislamiento por tenant; catálogo administrable.

## Capabilities

### New Capabilities
- `rbac-catalog`: modelo de datos y reglas del catálogo administrable rol × permiso (entidades `roles`, `permisos`, `rol_permiso`, `usuario_rol`; seed de la matriz base; vigencia de asignaciones; aislamiento por tenant).
- `rbac-authorization`: resolución de permisos efectivos server-side por request y el guard `require_permission("modulo:accion")` fail-closed, incluyendo semántica de alcance `(propio)` vs global.

### Modified Capabilities
- `auth-dependency`: la dependency de auth (`get_current_user`) se complementa con `require_permission`; la autorización deja de ser un hueco reservado. El contrato de `get_current_user` no cambia, pero se documenta que los `roles` del JWT son informativos y los permisos se resuelven contra la BD.

## Impact

- **Código nuevo**: `app/models/rol.py`, `app/models/permiso.py`, `app/models/rol_permiso.py`, `app/models/usuario_rol.py`; `app/repositories/` correspondientes; `app/services/rbac_service.py` (resolución de permisos efectivos); `app/core/permissions.py` (hoy stub reservado → implementación del resolver y `require_permission`); `app/core/dependencies.py` (agrega `require_permission`); routers de administración del catálogo.
- **Migración**: `004_rbac_catalog.py` (tablas `roles`, `permisos`, `rol_permiso`, `usuario_rol`) + seed de la matriz base.
- **Seguridad / Governance**: dominio **CRÍTICO** (RBAC). Toda decisión de modelado de permisos y de evaluación del guard requiere revisión humana antes de implementar.
- **Dependencias aguas abajo**: habilita GATE 4 — C-05 (audit-log), C-06 (estructura-academica) y C-21 (frontend-shell-y-auth) pasan a estar listos para arrancar.
- **Sin breaking changes** para C-03: el JWT y los endpoints de auth no se modifican.
