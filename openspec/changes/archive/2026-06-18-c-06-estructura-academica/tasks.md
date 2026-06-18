# Tasks — C-06 Estructura Académica

> Implementación de modelos, CRUD y reglas de negocio para Carrera, Cohorte y Materia.

---

## 1. Enum compartido

- [x] 1.1 Crear `backend/app/core/enums.py` con `EstadoGenerico(str, Enum): ACTIVA = "Activa"; INACTIVA = "Inactiva"` — reutilizable por todas las entidades que usen estado Activa/Inactiva

## 2. Modelos ORM del dominio

- [x] 2.1 Crear `backend/app/models/domain/__init__.py` (vacio o re-export)
- [x] 2.2 Crear `backend/app/models/domain/carrera.py` — modelo `Carrera` con herencia de `BaseModel`, columnas: `codigo` (String 50, unique por tenant), `nombre` (String 255), `estado` (EstadoGenerico → String 20)
- [x] 2.3 Crear `backend/app/models/domain/cohorte.py` — modelo `Cohorte` con FK a `Carrera.id`, columnas: `carrera_id`, `nombre`, `anio` (Integer), `vig_desde` (Date), `vig_hasta` (Date nullable)
- [x] 2.4 Crear `backend/app/models/domain/materia.py` — modelo `Materia` con herencia de `BaseModel`, columnas: `codigo` (String 50, unique por tenant), `nombre` (String 255), `estado` (EstadoGenerico → String 20)
- [x] 2.5 Re-exportar `Carrera`, `Cohorte`, `Materia` en `backend/app/models/__init__.py` para que Alembic autogenerate los detecte

## 3. Migración Alembic 005

- [x] 3.1 Crear `backend/alembic/versions/005_carrera_cohorte_materia.py` — revision `"005"`, `down_revision` apuntando al hash de 004 (`981efb7b4070`)
- [x] 3.2 Crear tabla `carrera` con: UUID PK, tenant_id (FK → tenant.id), codigo (String 50), nombre (String 255), estado (String 20), timestamps (created_at, updated_at, deleted_at), unique constraint `uq_carrera_tenant_codigo` sobre (tenant_id, codigo)
- [x] 3.3 Crear tabla `cohorte` con: UUID PK, tenant_id, carrera_id (FK → carrera.id con `fk_cohorte_carrera_id_carrera`), nombre (String 255), anio (Integer), vig_desde (Date), vig_hasta (Date nullable), timestamps, unique constraint `uq_cohorte_tenant_carrera_nombre` sobre (tenant_id, carrera_id, nombre)
- [x] 3.4 Crear tabla `materia` con: UUID PK, tenant_id, codigo (String 50), nombre (String 255), estado (String 20), timestamps, unique constraint `uq_materia_tenant_codigo` sobre (tenant_id, codigo)
- [x] 3.5 Agregar índices para `deleted_at`, `tenant_id`, y FK columns en cada tabla
- [x] 3.6 Ejecutar `alembic upgrade head` y verificar que las tres tablas se crean correctamente

## 4. Schemas Pydantic (DTOs)

- [x] 4.1 Crear `backend/app/schemas/estructura.py` con schemas `CarreraCreate`, `CarreraUpdate`, `CarreraResponse`, `CohorteCreate`, `CohorteUpdate`, `CohorteResponse`, `MateriaCreate`, `MateriaUpdate`, `MateriaResponse` — todos con `model_config = ConfigDict(extra='forbid')`
- [x] 4.2 `CarreraCreate`: `codigo` (str), `nombre` (str); `CarreraUpdate`: `nombre` (opcional), `estado` (opcional)
- [x] 4.3 `CohorteCreate`: `carrera_id` (UUID), `nombre` (str), `anio` (int), `vig_desde` (date); `vig_hasta` (date opcional); `CohorteUpdate`: `nombre` (opcional), `carrera_id` (opcional), `vig_hasta` (opcional)
- [x] 4.4 `MateriaCreate`: `codigo` (str), `nombre` (str); `MateriaUpdate`: `nombre` (opcional), `estado` (opcional)
- [x] 4.5 `CarreraResponse`, `CohorteResponse`, `MateriaResponse`: incluir `id`, `tenant_id`, `created_at`, `updated_at`

## 5. Repositorios

- [x] 5.1 Crear `backend/app/repositories/estructura/__init__.py` (vacío)
- [x] 5.2 Crear `backend/app/repositories/estructura/carrera_repository.py` con `CarreraRepository(BaseRepository[Carrera])` — método adicional: `list_activas_por_carrera(carrera_id)` (hereda CRUD de BaseRepository)
- [x] 5.3 Crear `backend/app/repositories/estructura/cohorte_repository.py` con `CohorteRepository(BaseRepository[Cohorte])` — métodos adicionales: `list_activas_por_carrera(carrera_id)` para validación de regla de carrera inactiva
- [x] 5.4 Crear `backend/app/repositories/estructura/materia_repository.py` con `MateriaRepository(BaseRepository[Materia])` (hereda CRUD de BaseRepository sin extensiones)

## 6. Servicios

- [x] 6.1 Crear `backend/app/services/estructura/__init__.py` (vacío)
- [x] 6.2 Crear `backend/app/services/estructura/carrera_service.py` con `CarreraService`
- [x] 6.3 Crear `backend/app/services/estructura/cohorte_service.py` con `CohorteService`
- [x] 6.4 Crear `backend/app/services/estructura/materia_service.py` con `MateriaService`

## 7. Routers FastAPI

- [x] 7.1 Crear `backend/app/api/v1/routers/carreras.py` — CRUD completo en `/api/admin/carreras` protegido con `Depends(require_permission("estructura:gestionar"))`, tag `["admin"]`
- [x] 7.2 Crear `backend/app/api/v1/routers/cohortes.py` — CRUD completo en `/api/admin/cohortes` con GET filter `?carrera_id=`, protegido con `Depends(require_permission("estructura:gestionar"))`, tag `["admin"]`
- [x] 7.3 Crear `backend/app/api/v1/routers/materias.py` — CRUD completo en `/api/admin/materias` protegido con `Depends(require_permission("estructura:gestionar"))`, tag `["admin"]`
- [x] 7.4 Importar y registrar los tres routers en `backend/app/main.py` con `app.include_router(router, prefix="/api/v1")`

## 8. Tests

- [x] 8.1 Crear `backend/tests/test_estructura/__init__.py` (vacío)
- [x] 8.2 Test: creación de carrera (201), código duplicado en mismo tenant (409), código duplicado en tenant distinto se permite (201)
- [x] 8.3 Test: obtener carrera por ID (200), listar carreras del tenant (200), obtener carrera de otro tenant (404)
- [x] 8.4 Test: actualizar nombre de carrera (200), desactivar carrera sin cohortes activas (200), desactivar con cohortes activas (409), reactivar carrera (200)
- [x] 8.5 Test: soft-delete carrera sin cohortes activas (204), soft-delete con cohortes activas (409), registro eliminado no aparece en listados, registro eliminado retorna 404 por ID
- [x] 8.6 Test: crear cohorte para carrera activa (201), crear cohorte para carrera inactiva (422), nombre duplicado en misma carrera (409), vig_hasta en el pasado se permite (201)
- [x] 8.7 Test: obtener cohorte por ID (200), listar cohortes filtradas por carrera (200), obtener cohorte de otro tenant (404)
- [x] 8.8 Test: actualizar nombre de cohorte (200), actualizar cambiando a carrera inactiva (422)
- [x] 8.9 Test: soft-delete cohorte (204)
- [x] 8.10 Test: crear materia con datos válidos (201), código duplicado mismo tenant (409), código duplicado tenant distinto (201)
- [x] 8.11 Test: obtener materia por ID (200), listar materias (200), obtener materia de otro tenant (404)
- [x] 8.12 Test: actualizar nombre (200), desactivar materia (200), soft-delete materia (204)
- [x] 8.13 Test: usuario sin permiso `estructura:gestionar` recibe 403 en todos los endpoints
- [x] 8.14 Test: envío con campos extra rechazado con 422 en todos los endpoints de creación
- [x] 8.15 Test: aislamiento multi-tenant — tenant A no ve ni modifica datos de tenant B

## 9. Verificación de seed y cierre

- [x] 9.1 Verificar en base de datos que el permiso `estructura:gestionar` (UUID `b000000b-0000-0000-0000-00000000000b`) está asignado al rol ADMIN en `rol_permiso`
- [x] 9.2 Ejecutar suite completa de tests de estructura y confirmar que pasan
- [x] 9.3 Verificar que `alembic downgrade -1` funciona y vuelve al estado previo sin pérdida
- [x] 9.4 Ejecutar `alembic upgrade head` nuevamente para dejar el schema en el estado final
