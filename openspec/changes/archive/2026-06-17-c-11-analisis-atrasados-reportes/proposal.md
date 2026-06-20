## Why

Con C-10 el sistema puede persistir calificaciones y umbrales, pero no puede responder la pregunta central del PROFESOR: "¿quién está atrasado y por qué?". Este change cierra ese hueco: convierte los datos de calificaciones en análisis accionables (atrasados, ranking, notas finales, reportes de métricas) necesarios para que C-12 pueda generar comunicaciones dirigidas.

## What Changes

- Nuevo servicio `analisis_service.py` con lógica de detección de atrasados (RN-06), ranking de aprobadas (RN-09) y cálculo de nota final agrupada (F2.5)
- Nuevos endpoints `GET /api/analisis/atrasados`, `GET /api/analisis/ranking`, `GET /api/analisis/notas-finales`, `GET /api/analisis/reporte` (métricas rápidas de una asignación)
- Nuevos métodos de consulta en `CalificacionRepository` para soportar los análisis: `list_by_entradas`, `count_aprobadas_by_alumno`, etc.
- Permisos `analisis:ver` (PROFESOR, TUTOR, COORDINADOR) requeridos en todos los endpoints
- Sin nuevos modelos SQLAlchemy ni migraciones — opera íntegramente sobre `Calificacion`, `EntradaPadron`, `UmbralMateria` y `Asignacion`

## Capabilities

### New Capabilities

- `analisis-atrasados`: Servicio de análisis académico que computa sobre datos de calificaciones — detección de atrasados (RN-06), ranking de actividades aprobadas (RN-09), notas finales agrupadas (F2.5) y reporte rápido de métricas por asignación (F2.4)

### Modified Capabilities

- `calificaciones`: Agrega métodos de consulta analítica en `CalificacionRepository` — necesarios para los cálculos de análisis sin duplicar lógica de acceso a datos

## Impact

- **Archivos nuevos**: `backend/app/services/analisis_service.py`, `backend/app/api/v1/routers/analisis.py`, `backend/app/schemas/analisis.py`
- **Archivos modificados**: `backend/app/repositories/calificacion_repository.py` (nuevos métodos de query), `backend/app/services/rbac_seed.py` (permiso `analisis:ver`), `backend/app/main.py` (registro del router)
- **Sin migraciones**: no se crean nuevas tablas
- **Desbloquea**: C-12 (comunicaciones) que necesita la lista de atrasados para generar mensajes dirigidos
