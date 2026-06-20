## 1. Modelos del catálogo RBAC

- [x] 1.1 Crear `app/models/rol.py` (`Rol(BaseTenantModel)`): `nombre` (str, único por tenant), `descripcion` (str|None). UniqueConstraint `(tenant_id, nombre)`.
- [x] 1.2 Crear `app/models/permiso.py` (`Permiso(BaseTenantModel)`): `clave` (str `modulo:accion`, único por tenant), `modulo`, `accion`, `descripcion`. UniqueConstraint `(tenant_id, clave)`.
- [x] 1.3 Crear `app/models/rol_permiso.py` (`RolPermiso(BaseTenantModel)`): FK `rol_id`, FK `permiso_id`, `alcance` (Enum `global`|`propio`, default `global`). UniqueConstraint `(tenant_id, rol_id, permiso_id)`.
- [x] 1.4 Crear `app/models/usuario_rol.py` (`UsuarioRol(BaseTenantModel)`): FK `user_id`, FK `rol_id`, `vigente_desde` (datetime), `vigente_hasta` (datetime|None). Índice `(tenant_id, user_id)`.
- [x] 1.5 Registrar los modelos nuevos en `app/models/__init__.py` para que Alembic los detecte.

## 2. Migración 004 + seed

- [x] 2.1 Generar `backend/alembic/versions/004_rbac_catalog.py` creando `roles`, `permisos`, `rol_permiso`, `usuario_rol` (una sola migración para el catálogo; ver D-07).
- [x] 2.2 Implementar `app/services/rbac_seed.py`: helper idempotente que siembra los 7 roles del dominio, los permisos `modulo:accion` y la matriz base de `03_actores_y_roles.md` §3.3 para un `tenant_id` dado (upsert por clave/nombre).
- [x] 2.3 Incluir el seed en la migración 004 aplicándolo a cada tenant existente; NEXO se siembra sin permisos (OQ-C04-01) e `impersonacion:usar` se asigna a ADMIN (OQ-C04-03).
- [x] 2.4 Test: aplicar migración + seed deja los 7 roles y la matriz base; re-ejecutar el seed no duplica filas (idempotencia).

## 3. Repositories

- [x] 3.1 Crear `app/repositories/roles.py`, `permisos.py`, `rol_permiso.py`, `usuario_rol.py` extendiendo `BaseRepository[T]` (scope de tenant heredado).
- [x] 3.2 Test (DB real/efímera): cada repo aísla por tenant — un repo de tenant A no ve filas del tenant B.

## 4. Servicio de resolución de permisos efectivos

- [x] 4.1 Test (rojo): `RbacService.resolver_permisos_efectivos(user_id, tenant_id, ahora)` retorna la unión de claves de permiso de los roles vigentes, con su alcance efectivo (`global` gana sobre `propio`).
- [x] 4.2 Implementar `app/services/rbac_service.py` con el resolver vía join `usuario_rol → rol_permiso → permiso`, filtrando por tenant y vigencia (`ahora ∈ [vigente_desde, vigente_hasta)`).
- [x] 4.3 Test: rol vencido no aporta permisos; rol NEXO sin permisos no otorga acceso; permisos acotados por tenant; JWT manipulado no influye (resolución solo desde BD).
- [x] 4.4 Test: unión de múltiples roles vigentes; `global` prevalece sobre `propio` cuando ambos provienen de roles distintos.

## 5. Guard `require_permission` (core)

- [x] 5.1 Test (rojo): endpoint con `require_permission("x:y")` → usuario con el permiso pasa; sin el permiso → 403 (no 401); endpoint sin guard no expone datos protegidos (fail-closed).
- [x] 5.2 Implementar el resolver y el guard en `app/core/permissions.py` (reemplaza el stub) y exponer `require_permission(clave, scope="global")` como dependency factory en `app/core/dependencies.py`.
- [x] 5.3 Implementar la semántica de alcance: `scope="propio"` acepta `propio` o `global` y expone `PermisoConcedido(clave, alcance)` al handler; `scope="global"` exige `global`.
- [x] 5.4 Test: alcance `propio` satisface endpoint `propio`; `propio` NO satisface endpoint `global` (403); el handler recibe el alcance concedido para filtrar por dueño.

## 6. API de administración del catálogo

- [x] 6.1 Crear schemas Pydantic v2 (`extra='forbid'`) para roles, permisos y matriz rol×permiso (request/response DTOs).
- [x] 6.2 Implementar router de administración (`app/routers/rbac.py`) con CRUD de roles, permisos y matriz, cada endpoint protegido por `require_permission("rbac:administrar")` (o claves `rbac:*` específicas). Sin lógica de negocio en el router (delega al service).
- [x] 6.3 Registrar el router en la app FastAPI.
- [x] 6.4 Test: usuario sin `rbac:administrar` → 403 al editar la matriz (anti-escalada de privilegios); ADMIN edita la matriz y el cambio surte efecto inmediato en la resolución (sin reemitir token).

## 7. Cobertura y cierre

- [x] 7.1 Verificar cobertura ≥80% líneas y ≥90% reglas de negocio del módulo RBAC (tests sin mocks de DB).
- [x] 7.2 Revisar que todos los escenarios de los specs `rbac-catalog`, `rbac-authorization` y la delta `auth-dependency` tienen test asociado.
- [x] 7.3 Ejecutar la suite completa (`pytest`) y confirmar verde antes de archivar.
