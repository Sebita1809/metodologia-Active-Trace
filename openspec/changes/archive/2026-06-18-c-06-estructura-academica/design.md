## Context

C-04 (RBAC) y C-05 (audit-log) están completos: el sistema cuenta con autorización fina `modulo:accion` y trazabilidad de operaciones. Sin embargo, no existe ningún modelo de dominio académico — no hay carreras, cohortes ni materias. Sin esta base ningún módulo downstream puede operar (importación de calificaciones, equipos docentes, encuentros, comunicaciones). C-06 construye las tres entidades fundacionales del catálogo académico multi-tenant sobre las que se apoya el resto del producto.

## Goals / Non-Goals

**Goals:**
- Modelos ORM para `Carrera`, `Cohorte`, `Materia` con herencia de `BaseModel` (UUID PK, tenant_id, soft-delete, timestamps)
- CRUD completo para cada entidad protegido con `require_permission("estructura:gestionar")`
- Regla de negocio RN-XX: una carrera inactiva no puede tener cohortes activas (validación en service layer)
- Migración Alembic `005_carrera_cohorte_materia.py` con constraints de unicidad y FK
- Seed del permiso `estructura:gestionar` (ya existe en migración 003; solo verificar que esté en matriz ADMIN)
- Tests de ABM, unicidad, regla de negocio y tenant-scope

**Non-Goals:**
- Entidad `Dictado` (instancia de dictado de una materia en una cohorte — postergada a C-07 por ADR-006)
- Entidad `AsignacionDocente` / equipos docentes (C-09)
- Comisiones, encuentros, coloquios (cambios posteriores)
- Relación Materia ↔ Carrera (el catálogo de materias es global por tenant; la vinculación se da vía Dictado en C-07)

## Decisions

| Decisión | Opción elegida | Rationale |
|----------|---------------|-----------|
| **Ubicación de modelos** | `models/domain/carrera.py`, `models/domain/cohorte.py`, `models/domain/materia.py` | Los modelos actuales están planos en `models/` porque son pocos (auth, tenant). Al crecer el dominio académico es mejor agruparlos en un subpaquete `domain/` para mantener ≤500 LOC por archivo y separar concerns. Se re-exportan desde `models/__init__.py` para que Alembic autogenerate los detecte. |
| **Paquete de repositorios** | `repositories/estructura/carrera_repository.py` (y análogos) | Sigue el patrón existente de `repositories/` planos. Se usa un prefijo `estructura/` para agrupar los tres repositorios del módulo, consistente con `services/estructura/`. |
| **Paquete de servicios** | `services/estructura/carrera_service.py` (y análogos) | Sigue el patrón existente de `services/auth/` y `services/audit/`. Cada módulo de dominio tiene su subdirectorio. |
| **Routers** | `api/v1/routers/carreras.py`, `api/v1/routers/cohortes.py`, `api/v1/routers/materias.py` | Archivos separados por entidad (un archivo por recurso). Prefijo `/api/admin/` + tag `["admin"]`. Todos protegidos con `Depends(require_permission("estructura:gestionar"))`. |
| **RBAC granularidad** | Un solo permiso `estructura:gestionar` para las tres entidades | Las tres son operaciones de catálogo administrativo. No hay necesidad de distinguir permisos por entidad en esta etapa. El ADMIN ya tiene este permiso en la semilla de 003. |
| **Reutilización de guard** | `require_permission` de `core/permissions.py` (C-04) | Sin cambios en el guard — se usa directamente como dependency. El permiso `estructura:gestionar` ya existe en la migración 003. Solo verificar que esté asignado al rol ADMIN. |
| **Estado enum** | `core/enums.py` → `EstadoGenerico(str, Enum): ACTIVA = "Activa"; INACTIVA = "Inactiva"` | Reutilizable en todas las entidades que usen estado Activa/Inactiva. Sigue el patrón de `TenantEstado` en `models/tenant.py` pero en centralizado. |
| **Migración** | `alembic/versions/005_carrera_cohorte_materia.py` (revision = "005", down_revision apunta al hash de 004) | Sigue la numeración secuencial existente. La migración es acumulativa — las tres tablas se crean juntas porque ninguna dependencia externa las separa y no hay datos en producción que migrar. |
| **Naming FK constraints** | `fk_cohorte_carrera_id_carrera` y similares explícitos | Consistente con el patrón de migraciones existentes (ej. `uq_rol_permiso`). |
| **Naming unique constraints** | `uq_carrera_tenant_codigo`, `uq_cohorte_tenant_carrera_nombre`, `uq_materia_tenant_codigo` | Patrón `uq_{tabla}_{columnas}` usado en migraciones previas. |
| **Service hereda de clase base** | No — cada service es independiente, recibe `db` y `tenant_id` por constructor | Los services de auth no usan base común; no se justifica abstraer hasta tener 3+ services con comportamiento común. |
| **Repository hereda de BaseRepository** | Sí — `CarreraRepository(BaseRepository[Carrera])` | BaseRepository ya provee tenant-scope, soft-delete y CRUD genérico. Solo se extiende si hay queries específicas (ej. listar cohortes activas por carrera). |

### Endpoints

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/api/admin/carreras` | Listar carreras del tenant |
| POST | `/api/admin/carreras` | Crear carrera |
| GET | `/api/admin/carreras/{id}` | Obtener carrera por ID |
| PUT | `/api/admin/carreras/{id}` | Actualizar carrera |
| DELETE | `/api/admin/carreras/{id}` | Soft-delete carrera |
| GET | `/api/admin/cohortes` | Listar cohortes del tenant (con filtro opcional por carrera_id) |
| POST | `/api/admin/cohortes` | Crear cohorte |
| GET | `/api/admin/cohortes/{id}` | Obtener cohorte por ID |
| PUT | `/api/admin/cohortes/{id}` | Actualizar cohorte |
| DELETE | `/api/admin/cohortes/{id}` | Soft-delete cohorte |
| GET | `/api/admin/materias` | Listar materias del tenant |
| POST | `/api/admin/materias` | Crear materia |
| GET | `/api/admin/materias/{id}` | Obtener materia por ID |
| PUT | `/api/admin/materias/{id}` | Actualizar materia |
| DELETE | `/api/admin/materias/{id}` | Soft-delete materia |

### Flujo de validación (RN: carrera inactiva sin cohortes activas)

```
PUT /api/admin/carreras/{id}  (cambiar estado a INACTIVA)
  → CarreraService.update()
    → Si estado pasa a INACTIVA:
      → CohorteRepository.list(estado=EstadoGenerico.ACTIVA, carrera_id=id)
      → Si existe alguna → HTTP 409 con detalle "No se puede inactivar una carrera con cohortes activas"
    → Si pasa → CarreraRepository.update()
```

## Risks / Trade-offs

- **Riesgo: migración 005 depende del revision ID concreto de 004**. La migración 004 (`981efb7b4070`) fue creada con un hash de revisión, no con el número secuencial `004`. Sin embargo, la migración 003 usó `"003"` como revision y apuntó al hash de 002. Para mantener la convención numérica legible, 005 usará revision `"005"` y `down_revision` apuntará al hash real de 004 (`981efb7b4070`). Esto es frágil si se regenera 004 — se mitigó documentando la dependencia explícita en el encabezado de la migración.

- **Riesgo: modelo de enums duplicado**. `TenantEstado` ya existe en `models/tenant.py` con los mismos valores. Podría unificarse, pero refactorizar `Tenant` ahora introduce riesgo de regression en C-02. Se acepta la duplicación temporal y se centraliza solo para los nuevos modelos vía `core/enums.py`.

- **Trade-off: repositorios planos vs. genéricos**. Los repositorios de estructura no agregan lógica significativa sobre `BaseRepository`. Podrían omitirse y usar `BaseRepository` directamente desde los services, pero se crean igual para mantener la consistencia arquitectónica (Routers → Services → Repositories → Models) y tener un punto de extensión futuro sin refactor.

- **Riesgo: Cohorte depende de Carrera (FK)**. El orden de creación de tablas en la migración debe ser Carrera → Cohorte → Materia. La migración 005 debe respetar este orden o fallará en PostgreSQL por la FK.
