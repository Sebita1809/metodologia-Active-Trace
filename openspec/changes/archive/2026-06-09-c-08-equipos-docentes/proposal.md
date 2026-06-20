## Why

Con las entidades `Usuario` y `Asignacion` disponibles (C-07), el sistema necesita las operaciones de gestión de equipos docentes: la vista del propio equipo para cada docente, las herramientas de coordinación (asignación masiva, clonado entre períodos, modificación de vigencias en bloque y exportación). Sin estas capacidades, la preparación de cada cuatrimestre requiere reasignar manualmente a todos los docentes, operación costosa y propensa a errores.

## What Changes

- Nuevo router `/api/equipos/*` con guard `equipos:asignar` para todas las operaciones de gestión de coordinación.
- Endpoint `GET /api/equipos/mis-equipos` (permiso `equipos:ver`): lista las asignaciones vigentes del usuario autenticado con su contexto académico, filtros por estado/materia/rol/carrera/cohorte.
- Endpoints CRUD de asignaciones (`GET /api/equipos/asignaciones`, `POST`, `PATCH /{id}`, `DELETE /{id}`) para gestión individual por COORDINADOR/ADMIN.
- `POST /api/equipos/asignaciones/masiva`: asignación en bloque de múltiples docentes × materia × carrera × cohorte × rol con vigencia, con búsqueda por autocompletado (RN-30).
- `POST /api/equipos/asignaciones/clonar`: duplica todas las asignaciones vigentes de un equipo origen (materia × carrera × cohorte) hacia un destino con fechas del nuevo período (RN-12).
- `PATCH /api/equipos/asignaciones/vigencia`: actualiza `desde`/`hasta` en bloque para todas las asignaciones de un equipo seleccionado (F4.6).
- `GET /api/equipos/asignaciones/exportar`: descarga archivo CSV/XLSX con el detalle completo del equipo (F4.7).
- Auditoría `ASIGNACION_MODIFICAR` en cada operación de escritura.

## Capabilities

### New Capabilities

- `equipos-docentes`: Gestión completa de equipos docentes sobre el modelo `Asignacion` — vista propia del docente (mis-equipos), gestión individual, asignación masiva, clonado entre períodos, modificación de vigencia en bloque y exportación. Incluye la lógica de clonado (RN-12) y búsqueda con autocompletado (RN-30).

### Modified Capabilities

<!-- No hay cambios en requerimientos de specs existentes. C-08 agrega endpoints y servicios sobre el modelo Asignacion definido en C-07, sin alterar el contrato de la entidad. -->

## Impact

- **Código nuevo**: `backend/app/api/v1/routers/equipos.py`, `backend/app/services/equipo_service.py`, `backend/app/repositories/asignacion_repository.py` (extensión con queries especializadas), `backend/app/schemas/equipo.py`
- **Código extendido**: `backend/app/models/__init__.py` — ya expone `Asignacion`; el repository de asignaciones recibe métodos nuevos (bulk insert, clone, bulk update vigencia, export query)
- **Dependencias**: requiere C-07 completo (`Asignacion`, `Usuario`, `Materia`, `Carrera`, `Cohorte`, guards RBAC de C-04, audit log de C-05)
- **APIs expuestas**: 7 endpoints nuevos bajo `/api/equipos/`
- **Sin breaking changes** en rutas ni contratos existentes
