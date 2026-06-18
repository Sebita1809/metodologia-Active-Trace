## Why

C-03 (auth-jwt-2fa) ya implementa autenticación: los usuarios pueden identificarse y obtener un JWT con sus roles. Pero no existe ningún sistema de autorización que controle qué puede hacer cada rol. Cualquier usuario autenticado puede acceder a cualquier endpoint. C-04 resuelve esto implementando RBAC con permisos finos (`modulo:accion`), necesario antes de construir cualquier módulo de dominio (C-05 en adelante). Sin C-04 no hay seguridad en los endpoints.

## What Changes

- **Modelos administrables**: tablas `Rol`, `Permiso` (`modulo:accion`), y `RolPermiso` (matriz rol × permiso como datos, no hardcode).
- **Seed de roles del dominio**: ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS con su matriz de permisos basal (según `03_actores_y_roles.md §3.3`).
- **Guard `require_permission`**: FastAPI dependency que declara el permiso requerido por endpoint y resuelve server-side si el usuario lo tiene. Sin permiso → 403.
- **Migración 003**: creación de tablas `rol`, `permiso`, `rol_permiso` + seed data.
- **Integración con C-03**: el guard consume `UserContext.roles` de `get_current_user` para resolver permisos.

## Capabilities

### New Capabilities
- `rbac-authorization`: Sistema de autorización RBAC con permisos finos. Modelos Rol, Permiso, RolPermiso administrables. Guard `require_permission` que protege endpoints. Resolución server-side de permisos efectivos por tenant.

### Modified Capabilities
- *(Ninguna — `user-auth` no cambia su comportamiento; el RBAC es una capa independiente que consume sus outputs)*

## Impact

- **Nuevos modelos**: `Rol`, `Permiso`, `RolPermiso` en `app/models/`
- **Nuevo guard**: `require_permission()` en `app/core/permissions.py` (reemplaza el placeholder actual)
- **Nuevo router**: `app/api/v1/routers/permissions.py` (CRUD de roles/permisos, opcional en C-04)
- **Migración**: `003_rol_permiso.py` en Alembic
- **Seed data**: Matriz de permisos para los 7 roles
- **Tests**: En `tests/test_rbac.py`
