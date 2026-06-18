## 1. Migración y permisos

- [x] 1.1 Crear migración Alembic 006 con tablas `usuario` y `asignacion`: `Usuario` con campos (id UUID PK, tenant_id FK, nombre, apellidos, email cifrado, email_hash HMAC, dni cifrado, cuil cifrado, cbu cifrado, alias_cbu cifrado, banco, regional, legajo, legajo_profesional, facturador, estado, timestamps + soft delete heredados de BaseModel). `Asignacion` con campos (id UUID PK, tenant_id, usuario_id FK, rol FK enum, materia_id FK nullable, carrera_id FK nullable, cohorte_id FK nullable, comisiones JSONB, responsable_id FK nullable, desde date, hasta date nullable, timestamps + soft delete heredados). Unique constraints: `(tenant_id, email_hash)` en usuario; `(tenant_id, legajo)` en usuario. Foreign keys con ON DELETE RESTRICT / SET NULL.
- [x] 1.2 Sin cambios — ambos permisos (`usuarios:gestionar` b000000c y `equipos:asignar` b0000005) ya están seedeados en migración 003.

## 2. Modelos SQLAlchemy

- [x] 2.1 Crear `app/models/domain/usuario.py` con modelo `Usuario`. Campos PII (`email`, `dni`, `cuil`, `cbu`, `alias_cbu`) almacenados como ciphertext en la columna (el modelo es agnóstico del cifrado). `email_hash` columna real (VARCHAR 64, indexada). `__repr__` que excluye campos PII.
- [x] 2.2 Crear `app/models/domain/asignacion.py` con modelo `Asignacion`. Campos: `usuario_id` FK → Usuario, `rol` (String), `materia_id` FK → Materia nullable, `carrera_id` FK → Carrera nullable, `cohorte_id` FK → Cohorte nullable, `comisiones` JSONB default [], `responsable_id` FK → Usuario nullable, `desde` Date, `hasta` Date nullable. Propiedad `estado_vigencia` calculada en Python.
- [x] 2.3 Exportar ambos modelos en `app/models/domain/__init__.py` y en `app/models/__init__.py` para que Alembic los detecte.

## 3. Schemas Pydantic

- [x] 3.1 Crear `app/schemas/usuarios.py` con schemas: `UsuarioCreate`, `UsuarioUpdate`, `UsuarioResponse`, `UsuarioListParams`. Todos con `extra='forbid'` y `from_attributes=True` en responses.
- [x] 3.2 Crear `app/schemas/asignaciones.py` con: `AsignacionCreate`, `AsignacionUpdate`, `AsignacionResponse` (incluye `estado_vigencia` como campo calculado). `extra='forbid'` en todos.

## 4. Repositorios

- [x] 4.1 Crear `app/repositories/usuarios/__init__.py` y `app/repositories/usuarios/usuario_repository.py` con `UsuarioRepository(BaseRepository[Usuario])`. Método extra: `get_by_email(tenant_id, email)` que calcula `email_hash` y busca por esa columna. `get_by_email_hash(tenant_id, email_hash)` para búsqueda directa.
- [x] 4.2 Crear `app/repositories/usuarios/asignacion_repository.py` con `AsignacionRepository(BaseRepository[Asignacion])`. Métodos extra: `list_by_usuario(usuario_id)`, `list_by_materia(materia_id)`, `list_vigentes(fecha)` con filtro combinado `desde <= fecha AND (hasta IS NULL OR hasta >= fecha)`.

## 5. Servicios

- [x] 5.1 Crear `app/services/usuarios/__init__.py` y `app/services/usuarios/usuario_service.py` con `UsuarioService`. Métodos: `crear_usuario` (recibe datos planos, cifra PII con AESCipher, calcula email_hash con HMAC, persiste), `actualizar_usuario` (si cambia email → recifra + rehash), `desactivar_usuario` (cambia estado a Inactivo, previene doble desactivación), `buscar_por_email` (usa hash). Validaciones: unicidad email por tenant, email formato.
- [x] 5.2 Crear `app/services/usuarios/asignacion_service.py` con `AsignacionService`. Métodos: `crear_asignacion` (valida usuario activo, valida fechas desde≤hasta, valida responsable existe en mismo tenant), `actualizar_asignacion`, `eliminar_asignacion` (soft delete), `listar_con_filtros` (por usuario, materia, solo vigentes). Reglas: usuario inactivo no puede recibir asignaciones; rango de fechas inválido → 422.

## 6. Routers / Endpoints

- [x] 6.1 Crear `app/api/v1/routers/usuarios.py` con router para `/api/admin/usuarios`: `GET /` (listar, con filtro opcional `?email=`), `POST /` (crear), `GET /{id}` (obtener), `PATCH /{id}` (actualizar), `DELETE /{id}` (desactivar). Todos con `require_permission("usuarios:gestionar")`.
- [x] 6.2 Crear router para `/api/asignaciones` (puede ir en mismo archivo o separado `asignaciones.py`): `GET /` (listar con filtros `?usuario_id=`, `?materia_id=`, `?solo_vigentes=true`), `POST /` (crear), `GET /{id}` (obtener), `PATCH /{id}` (actualizar), `DELETE /{id}` (eliminar). Todos con `require_permission("equipos:asignar")`.
- [x] 6.3 Registrar ambos routers en `app/main.py` (dentro del `api_v1_router`).

## 7. Tests

- [x] 7.1 Configurar `tests/test_usuarios/__init__.py` y `conftest.py` con fixtures específicos: `usuario_data_valido`, `usuario_data_sin_pii`, `usuario_create` (objeto creado), `asignacion_data_valida`, `asignacion_create`.
- [x] 7.2 Tests de Usuario: creación con PII cifrada (verificar que en DB el campo está cifrado y en response está descifrado), unicidad email por tenant, email duplicado en otro tenant OK, actualización de email (recifrado + rehash), desactivación (estado Inactivo + 409 si ya inactivo), búsqueda por email (caso existente + inexistente), PII no expuesta en logs/respuestas de error.
- [x] 7.3 Tests de Asignacion: creación válida con contexto, creación sin contexto (rol global), asignación a usuario inactivo → 422, rango fechas inválido → 422, responsable de otro tenant → 422, listado por usuario/materia, filtro solo_vigentes, vigencia derivada (4 escenarios de estado_vigencia), soft delete.
- [x] 7.4 Tests de RBAC: usuario sin `usuarios:gestionar` → 403 en endpoints de usuario; usuario sin `equipos:asignar` → 403 en endpoints de asignación; ADMIN puede ambos; COORDINADOR solo asignaciones; no autenticado → 401.
- [x] 7.5 Tests de multi-tenancy: usuario de tenant A no ve usuarios de tenant B; asignación de tenant A referenciando usuario de tenant B → 404.
