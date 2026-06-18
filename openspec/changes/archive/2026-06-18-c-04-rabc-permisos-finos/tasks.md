## 1. Modelos y Migración

- [x] 1.1 Crear modelo `Rol` (SQLAlchemy): `id`, `tenant_id`, `nombre`, `descripcion`, timestamps (BaseModel), unique constraint `(tenant_id, nombre)`
- [x] 1.2 Crear modelo `Permiso` (SQLAlchemy): `id`, `codigo` (unique), `modulo`, `accion`, `descripcion`, timestamps (BaseModel)
- [x] 1.3 Crear modelo `RolPermiso` (SQLAlchemy): `id`, `rol_id` (FK → rol), `permiso_id` (FK → permiso), timestamps, unique constraint `(rol_id, permiso_id)`, FK a rol y permiso con ondelete=CASCADE
- [x] 1.4 Agregar `Rol`, `Permiso`, `RolPermiso` al `__init__.py` de modelos
- [x] 1.5 Generar migración Alembic 003 con `alembic revision --autogenerate -m "003_rol_permiso"`
- [x] 1.6 Revisar y corregir la migración autogenerada (verificar tipos, FKs, unique constraints)

## 2. Seed de Roles y Matriz de Permisos

- [x] 2.1 Agregar seed de los 7 roles del dominio en la migración 003: ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS
- [x] 2.2 Agregar seed de todos los permisos definidos en la matriz (`calificaciones:importar`, `atrasados:ver`, `comunicacion:enviar`, `comunicacion:aprobar`, `equipos:asignar`, `encuentros:gestionar`, `encuentros:ver`, `guardias:registrar`, `tareas:gestionar`, `avisos:publicar`, `estructura:gestionar`, `usuarios:gestionar`, `auditoria:ver`, `liquidaciones:gestionar`, `liquidaciones:cerrar`, `facturas:gestionar`, `salarios:gestionar`, `configuracion:gestionar`, `impersonacion:usar`)
- [x] 2.3 Agregar seed de la matriz rol × permiso según `03_actores_y_roles.md §3.3`, incluyendo el alcance `(propio)` como metadata textual en la relación

## 3. Guard de Autorización

- [x] 3.1 Implementar función `resolve_user_permissions(user_context, db)` en `app/core/permissions.py` que consulta RolPermiso para obtener los códigos de permiso del usuario según sus roles
- [x] 3.2 Implementar guard `require_permission(permiso_codigo: str)` como FastAPI dependency que: (a) obtiene `UserContext` de `get_current_user`, (b) resuelve permisos vía DB, (c) si no tiene el permiso → raise `HTTPException(403)`
- [x] 3.3 Agregar `require_permission` a `app/core/dependencies.py` como re-export para que los routers lo importen desde allí
- [x] 3.4 Verificar que `get_current_user` se ejecute antes que `require_permission` (orden de dependencias correcto en FastAPI)

## 4. Tests

- [x] 4.1 Escribir test: seed inicial tiene los 7 roles y los permisos esperados
- [x] 4.2 Escribir test: usuario con permiso accede → 200 OK
- [x] 4.3 Escribir test: usuario sin permiso → 403 Forbidden
- [x] 4.4 Escribir test: usuario multi-rol hereda permisos de ambos roles
- [x] 4.5 Escribir test: aislamiento por tenant (mismo rol en tenant distinto no otorga permisos)
- [x] 4.6 Escribir test: usuario no autenticado → 401 (get_current_user se ejecuta primero)
- [x] 4.7 Escribir test: unicidad (rol duplicado en mismo tenant, permiso duplicado)
- [x] 4.8 Escribir test: FK constraints (rol_permiso no acepta rol_id o permiso_id inexistente)
