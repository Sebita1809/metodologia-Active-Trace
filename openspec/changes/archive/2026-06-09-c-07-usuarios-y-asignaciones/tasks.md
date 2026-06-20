## 1. Modelos SQLAlchemy

- [x] 1.1 Crear `backend/app/models/usuario.py` — modelo `Usuario(BaseTenantModel)` con columnas: `nombre` (String 200), `apellidos` (String 200), `email` (Text — almacena ciphertext AES-GCM), `email_hash` (String 64 — HMAC-SHA256 determinístico), `dni`, `cuil`, `cbu`, `alias_cbu` (Text nullable — ciphertext), `banco` (String nullable), `regional` (String nullable), `legajo` (String nullable), `legajo_profesional` (String nullable), `facturador` (Boolean default False), `estado` (String 20 default "Activo"); `__repr__` expone solo `id` y `tenant_id` (nunca PII)
- [x] 1.2 Crear `backend/app/models/asignacion.py` — modelo `Asignacion(BaseTenantModel)` con FK `usuario_id → usuario.id` (RESTRICT), `rol` (String 30), `materia_id` / `carrera_id` / `cohorte_id` (UUID FK nullable RESTRICT a sus respectivas tablas), `comisiones` (JSONB default `[]`), `responsable_id` (UUID FK → `usuario.id` nullable RESTRICT — auto-referencia), `desde` (Date NOT NULL), `hasta` (Date nullable); tabla `asignaciones`
- [x] 1.3 Exportar ambos modelos en `backend/app/models/__init__.py`

## 2. Migración Alembic

- [x] 2.1 Crear `backend/alembic/versions/007_usuarios_y_asignaciones.py` con `revision = "007"`, `down_revision = "006"`
- [x] 2.2 En `upgrade()`: crear tabla `usuario` con todas las columnas del modelo (mixin base + campos dominio), FK a `tenants.id` RESTRICT
- [x] 2.3 Agregar índice único `uq_usuario_tenant_email_hash` sobre `(tenant_id, email_hash)`; índice de apoyo sobre `(tenant_id, estado)`
- [x] 2.4 Crear tabla `asignacion` con todas las columnas: mixin base + `usuario_id`, `rol`, `materia_id`/`carrera_id`/`cohorte_id` (nullable), `comisiones` (JSONB), `responsable_id` (nullable self-ref), `desde`, `hasta`; FKs con RESTRICT
- [x] 2.5 Agregar índices de apoyo en `asignacion`: `(tenant_id, usuario_id)`, `(tenant_id, materia_id)`, `(tenant_id, responsable_id)`
- [x] 2.6 Data-seed defensivo (`ON CONFLICT DO NOTHING`): insertar permisos `usuarios:gestionar`, `equipos:asignar`, `asignaciones:gestionar` en `permisos` y asignarlos en `rol_permiso` (ADMIN para los tres; COORDINADOR para `equipos:asignar` y `asignaciones:gestionar`)

## 3. Extensión CryptoService

- [x] 3.1 Agregar método `hash_deterministic(value: str) -> str` a `CryptoService` en `backend/app/core/crypto.py` — HMAC-SHA256 del valor normalizado (strip + lowercase) usando `self._key` como clave; retorna hex string de 64 chars; usar para computar `email_hash`

## 4. Repositories

- [x] 4.1 Crear `backend/app/repositories/usuario_repository.py` — hereda `BaseRepository[Usuario]`, constructor `(*, session, tenant_id)`; métodos: `get_by_email_hash(email_hash: str) -> Usuario | None` (usa `_base_query()`), `list_activos() -> list[Usuario]`
- [x] 4.2 Crear `backend/app/repositories/asignacion_repository.py` — hereda `BaseRepository[Asignacion]`; método `list_with_filters(*, usuario_id, materia_id, carrera_id, cohorte_id, rol, responsable_id) -> list[Asignacion]` — todos los parámetros opcionales (`None` = sin filtro); usa `_base_query()` como base

## 5. Schemas Pydantic

- [x] 5.1 Crear `backend/app/schemas/usuario.py` — `UsuarioCreate` (campos en claro), `UsuarioUpdate` (todos opcionales), `UsuarioResponse` (PII descifrada; **sin** `email_hash`); `_Base` con `model_config = ConfigDict(extra="forbid", from_attributes=True)`; `estado: Literal["Activo", "Inactivo"]`
- [x] 5.2 Crear `backend/app/schemas/asignacion.py` — `RolNegocioEnum` (`Literal["PROFESOR", "TUTOR", "COORDINADOR", "NEXO", "ADMIN", "FINANZAS"]`); `AsignacionCreate`, `AsignacionUpdate` (todos opcionales), `AsignacionResponse` con campo `estado_vigencia: Literal["Vigente", "Vencida"]` (calculado, no del modelo); `comisiones: list[str] = []`

## 6. Services

- [x] 6.1 Crear `backend/app/services/usuario_service.py` — `UsuarioService(*, session, tenant_id, crypto: CryptoService)`: `create` → normaliza email, computa `email_hash`, valida unicidad con repo (HTTP 409 si existe), cifra PII con `crypto.encrypt`, persiste; `update` → re-cifra solo campos presentes; `get`/`list` → descifra PII al construir respuesta; `delete` → soft_delete vía repo; NUNCA loguear PII ni incluirla en mensajes de error; raise `ValueError` para 409
- [x] 6.2 Crear `backend/app/services/asignacion_service.py` — `AsignacionService(*, session, tenant_id)`: `create`, `update`, `get`, `list_with_filters`, `delete`; computar `estado_vigencia` al construir respuesta (property: `"Vigente"` si `desde <= hoy` y (`hasta is None` o `hoy <= hasta`), `"Vencida"` si `hasta < hoy`); validar que `rol` ∈ valores permitidos (HTTPException 422 si no)

## 7. Routers

- [x] 7.1 Crear `backend/app/api/v1/routers/usuarios.py` — `POST /` (201), `GET /`, `GET /{id}`, `PATCH /{id}`, `DELETE /` (204); guard `require_permission("usuarios:gestionar", scope="global")` en todos los escritura; inicializar `UsuarioService` con `CryptoService` desde settings en el dependency helper
- [x] 7.2 Crear `backend/app/api/v1/routers/asignaciones.py` — `POST /` (201), `GET /` (query params: `materia_id`, `carrera_id`, `cohorte_id`, `usuario_id`, `rol`, `responsable_id`), `GET /{id}`, `PATCH /{id}`, `DELETE /{id}` (204); guard `require_permission("equipos:asignar", scope="global")` en escritura; GET lectura abierta dentro del tenant
- [x] 7.3 Registrar ambos routers en `backend/app/main.py`: `prefix="/api/admin/usuarios"` y `prefix="/api/asignaciones"`, `tags=["usuarios"]` y `tags=["asignaciones"]`

## 8. Tests — Modelos y Repositorios

- [x] 8.1 Test: crear `Usuario` → persiste con `estado = "Activo"` por defecto; columna `email` contiene ciphertext (no el email original)
- [x] 8.2 Test: unicidad `(tenant_id, email_hash)` → segunda inserción con mismo hash lanza `IntegrityError`
- [x] 8.3 Test: soft delete `Usuario` → `deleted_at` seteado, no retornado por `repo.list()`
- [x] 8.4 Test: `Usuario.__repr__` no expone ningún campo PII (`email`, `dni`, `cuil`, `cbu`, `alias_cbu`) — ni en claro ni como ciphertext visible
- [x] 8.5 Test: crear `Asignacion` → persiste con FK a `Usuario`, `comisiones = []` por defecto, `responsable_id` nullable
- [x] 8.6 Test: `Asignacion` con `responsable_id` auto-referencia → persiste correctamente; FK apunta a `usuario` del mismo tenant
- [x] 8.7 Test: aislamiento multi-tenant — `UsuarioRepository` scoped a tenant A no retorna usuarios de tenant B

## 9. Tests — Services y Reglas de Negocio

- [x] 9.1 Test: `UsuarioService.create` → columna `email` almacenada difiere del plaintext de entrada (está cifrada)
- [x] 9.2 Test: `UsuarioService.create` → `email_hash` almacenado es HMAC de email normalizado (no el email en claro)
- [x] 9.3 Test: `UsuarioService.get` → PII fields descifradas en respuesta coinciden con los valores originales enviados en create
- [x] 9.4 Test: `UsuarioService.create` email duplicado mismo tenant → raise `ValueError` (router traduce a HTTP 409)
- [x] 9.5 Test: `UsuarioService.create` email duplicado otro tenant → crea exitosamente (HTTP 201)
- [x] 9.6 Test: `email_hash` no aparece en ningún campo de `UsuarioResponse`
- [x] 9.7 Test: `AsignacionService.create` con `desde` pasado y `hasta` futuro → `estado_vigencia = "Vigente"`
- [x] 9.8 Test: `AsignacionService` con `hasta` en el pasado → `estado_vigencia = "Vencida"`
- [x] 9.9 Test: `AsignacionService` con `hasta = None` → `estado_vigencia = "Vigente"` (vigencia abierta)
- [x] 9.10 Test: `AsignacionService.create` con `rol = "INVALIDO"` → raise `HTTPException(422)`

## 10. Tests — Endpoints (integración)

- [x] 10.1 Test: `POST /api/admin/usuarios` sin token → HTTP 401
- [x] 10.2 Test: `POST /api/admin/usuarios` sin permiso `usuarios:gestionar` → HTTP 403
- [x] 10.3 Test: `POST /api/admin/usuarios` con ADMIN válido → HTTP 201; body incluye PII descifrada; no incluye `email_hash`
- [x] 10.4 Test: `GET /api/admin/usuarios` retorna solo usuarios del tenant del JWT
- [x] 10.5 Test: `GET /api/admin/usuarios/{id}` con ID de otro tenant → HTTP 404
- [x] 10.6 Test: `PATCH /api/admin/usuarios/{id}` → actualiza `estado`, retorna HTTP 200
- [x] 10.7 Test: `DELETE /api/admin/usuarios/{id}` → HTTP 204; usuario no aparece en GET posterior
- [x] 10.8 Test: `POST /api/admin/usuarios` con email duplicado en mismo tenant → HTTP 409
- [x] 10.9 Test: `POST /api/asignaciones` sin token → HTTP 401
- [x] 10.10 Test: `POST /api/asignaciones` sin permiso `equipos:asignar` → HTTP 403
- [x] 10.11 Test: `POST /api/asignaciones` con COORDINADOR válido → HTTP 201; `estado_vigencia` presente en respuesta
- [x] 10.12 Test: `GET /api/asignaciones?materia_id=...` filtra correctamente (solo las de esa materia en el tenant)
- [x] 10.13 Test: `GET /api/asignaciones?responsable_id=...` filtra correctamente
- [x] 10.14 Test: `GET /api/asignaciones` retorna solo asignaciones del tenant del JWT
