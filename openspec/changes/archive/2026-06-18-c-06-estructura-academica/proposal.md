## Why

C-04 (RBAC) y C-05 (audit-log) ya están completos: el sistema tiene autorización fina y trazabilidad de acciones. Pero no existe aún ningún modelo de dominio académico. No hay carreras, no hay cohortes, no hay materias. Sin la estructura académica fundamental ningún otro módulo puede operar — no se pueden importar calificaciones (F1.1), no se pueden asignar equipos docentes, no se pueden configurar encuentros ni generar comunicaciones. C-06 construye la base del modelo de dominio sobre la que se apoya todo el resto del producto.

## What Changes

- **Nuevos modelos**: `Carrera`, `Cohorte`, `Materia` como entidades del catálogo académico por tenant. Carrera y Materia con unicidad `(tenant_id, codigo)`. Cohorte con unicidad `(tenant_id, carrera_id, nombre)`.
- **Regla de negocio**: carrera inactiva no puede tener cohortes activas.
- **Endpoints ABM**: `/api/admin/carreras`, `/api/admin/cohortes`, `/api/admin/materias` con CRUD completo, protegidos con permiso `estructura:gestionar` (rol ADMIN).
- **Servicios y repositorios**: capa de servicio y repository para cada entidad, siguiendo Clean Architecture (Routers → Services → Repositories → Models).
- **Migración 005**: creación de tablas `carrera`, `cohorte`, `materia` con constraints de unicidad y FK correspondientes.
- **Tests**: ABM de cada entidad, validación de unicidad, regla carrera inactiva sin cohortes activas, scope de tenant.

## Capabilities

### New Capabilities
- `estructura-academica`: Gestión del catálogo académico del tenant. Carreras, cohortes y materias como entidades base del dominio. CRUD con validaciones de unicidad y reglas de negocio, protegido por RBAC con permiso `estructura:gestionar`.

### Modified Capabilities
- *(Ninguna — C-04 y C-05 no se modifican; el permiso `estructura:gestionar` se agrega como seed en la matriz de ADMIN)*

## Impact

- **Nuevos modelos**: `app/models/domain/carrera.py`, `app/models/domain/cohorte.py`, `app/models/domain/materia.py`
- **Nuevos servicios**: `app/services/estructura/carrera_service.py`, `app/services/estructura/cohorte_service.py`, `app/services/estructura/materia_service.py`
- **Nuevos repositorios**: `app/repositories/estructura/carrera_repository.py`, `app/repositories/estructura/cohorte_repository.py`, `app/repositories/estructura/materia_repository.py`
- **Nuevos routers**: `app/api/v1/routers/carreras.py`, `app/api/v1/routers/cohortes.py`, `app/api/v1/routers/materias.py`
- **Migración**: `005_carrera_cohorte_materia.py` en Alembic
- **Seed de permisos**: agregar `estructura:gestionar` a la matriz del rol ADMIN
- **Tests**: `tests/test_estructura_academica.py`
