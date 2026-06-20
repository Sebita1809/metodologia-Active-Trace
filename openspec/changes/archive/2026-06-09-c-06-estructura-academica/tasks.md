## 1. Modelos SQLAlchemy

- [x] 1.1 Crear `backend/app/models/carrera.py` — modelo `Carrera` con mixin base (UUID, tenant_id, timestamps, soft delete), campos `codigo`, `nombre`, `estado` (enum Activa/Inactiva)
- [x] 1.2 Crear `backend/app/models/cohorte.py` — modelo `Cohorte` con FK a `Carrera`, campos `nombre`, `anio`, `vig_desde`, `vig_hasta` (nullable), `estado`
- [x] 1.3 Crear `backend/app/models/materia.py` — modelo `Materia` con mixin base, campos `codigo`, `nombre`, `estado` (catálogo único por tenant, ADR-006)
- [x] 1.4 Exportar los 3 modelos en `backend/app/models/__init__.py`

## 2. Migración Alembic

- [x] 2.1 Generar `Migración 004` (`alembic revision --autogenerate -m "carrera cohorte materia"`) con tablas `carrera`, `cohorte`, `materia`
- [x] 2.2 Revisar y ajustar la migración: agregar índices únicos `uq_carrera_tenant_codigo`, `uq_cohorte_tenant_carrera_nombre`, `uq_materia_tenant_codigo`
- [x] 2.3 Agregar en la migración el data-seed del permiso `estructura:gestionar` asignado al rol ADMIN (verificar que no exista antes de insertar)

## 3. Repositories

- [x] 3.1 Crear `backend/app/repositories/carrera_repository.py` — hereda de `BaseRepository`, scope tenant siempre activo, métodos `get_by_codigo`, `list_activas`
- [x] 3.2 Crear `backend/app/repositories/cohorte_repository.py` — scope tenant, métodos `get_by_nombre_carrera`, `list_by_carrera`
- [x] 3.3 Crear `backend/app/repositories/materia_repository.py` — scope tenant, métodos `get_by_codigo`, `list_activas`

## 4. Schemas Pydantic

- [x] 4.1 Crear `backend/app/schemas/carrera.py` — schemas `CarreraCreate`, `CarreraUpdate`, `CarreraResponse` con `model_config = ConfigDict(extra='forbid')`
- [x] 4.2 Crear `backend/app/schemas/cohorte.py` — schemas `CohorteCreate`, `CohorteUpdate`, `CohorteResponse` (incluir `vig_hasta` opcional)
- [x] 4.3 Crear `backend/app/schemas/materia.py` — schemas `MateriaCreate`, `MateriaUpdate`, `MateriaResponse`

## 5. Services

- [x] 5.1 Crear `backend/app/services/carrera_service.py` — métodos `create`, `update`, `delete`, `get`, `list`; validar unicidad `(tenant_id, codigo)` → HTTP 409; soft delete
- [x] 5.2 Crear `backend/app/services/cohorte_service.py` — validar unicidad `(tenant_id, carrera_id, nombre)` → HTTP 409; validar que carrera activa antes de crear/activar cohorte → HTTP 422; validar `vig_hasta >= vig_desde` → HTTP 422
- [x] 5.3 Crear `backend/app/services/materia_service.py` — validar unicidad `(tenant_id, codigo)` → HTTP 409; soft delete

## 6. Routers

- [x] 6.1 Crear `backend/app/routers/carreras.py` — endpoints `POST /api/admin/carreras`, `GET /api/admin/carreras`, `GET /api/admin/carreras/{id}`, `PATCH /api/admin/carreras/{id}`, `DELETE /api/admin/carreras/{id}`; guard `require_permission("estructura:gestionar")` en escritura
- [x] 6.2 Crear `backend/app/routers/cohortes.py` — mismos verbos bajo `/api/admin/cohortes`; guard en escritura; filtro opcional `?carrera_id=`
- [x] 6.3 Crear `backend/app/routers/materias.py` — mismos verbos bajo `/api/admin/materias`; guard en escritura
- [x] 6.4 Registrar los 3 routers en `backend/app/main.py`

## 7. Tests — Modelos y Repositorios

- [x] 7.1 Test: crear Carrera → persiste con campos correctos y `estado = Activa` por defecto
- [x] 7.2 Test: unicidad `(tenant_id, codigo)` en Carrera → segunda inserción lanza IntegrityError
- [x] 7.3 Test: soft delete de Carrera → `deleted_at` seteado, no aparece en list
- [x] 7.4 Test: crear Cohorte → persiste con FK a Carrera y `vig_hasta` nullable
- [x] 7.5 Test: unicidad `(tenant_id, carrera_id, nombre)` en Cohorte → IntegrityError en duplicado
- [x] 7.6 Test: crear Materia → persiste con `estado = Activa` por defecto
- [x] 7.7 Test: unicidad `(tenant_id, codigo)` en Materia → IntegrityError en duplicado
- [x] 7.8 Test: aislamiento multi-tenant — repo de Carrera no retorna registros de otro tenant

## 8. Tests — Services y Reglas de Negocio

- [x] 8.1 Test: `CarreraService.create` con código duplicado en mismo tenant → HTTP 409
- [x] 8.2 Test: `CarreraService.create` con código duplicado en otro tenant → HTTP 201
- [x] 8.3 Test: `CohorteService.create` sobre carrera inactiva → HTTP 422
- [x] 8.4 Test: `CohorteService.update` para activar cohorte con carrera inactiva → HTTP 422
- [x] 8.5 Test: `CohorteService.create` con `vig_hasta` anterior a `vig_desde` → HTTP 422
- [x] 8.6 Test: `CohorteService.create` con nombre duplicado en misma carrera y tenant → HTTP 409
- [x] 8.7 Test: `MateriaService.create` con código duplicado en mismo tenant → HTTP 409

## 9. Tests — Endpoints (integración)

- [x] 9.1 Test: `POST /api/admin/carreras` sin token → HTTP 401
- [x] 9.2 Test: `POST /api/admin/carreras` sin permiso `estructura:gestionar` → HTTP 403
- [x] 9.3 Test: `POST /api/admin/carreras` con ADMIN válido → HTTP 201 + body correcto
- [x] 9.4 Test: `GET /api/admin/carreras` solo retorna carreras del tenant del usuario
- [x] 9.5 Test: `GET /api/admin/carreras/{id}` con ID de otro tenant → HTTP 404
- [x] 9.6 Test: `PATCH /api/admin/carreras/{id}` → actualiza estado, retorna HTTP 200
- [x] 9.7 Test: `DELETE /api/admin/carreras/{id}` → HTTP 204, carrera no aparece en GET
- [x] 9.8 Test: `POST /api/admin/cohortes` con carrera inactiva → HTTP 422
- [x] 9.9 Test: `POST /api/admin/cohortes` con carrera activa → HTTP 201
- [x] 9.10 Test: `GET /api/admin/cohortes` solo retorna cohortes del tenant del usuario
- [x] 9.11 Test: `POST /api/admin/materias` con ADMIN válido → HTTP 201
- [x] 9.12 Test: `GET /api/admin/materias` solo retorna materias del tenant del usuario
- [x] 9.13 Test: `POST /api/admin/materias` con código duplicado → HTTP 409
