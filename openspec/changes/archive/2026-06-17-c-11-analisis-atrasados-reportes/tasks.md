## 1. Schemas Pydantic

- [x] 1.1 Crear `backend/app/schemas/analisis.py` — `AlumnoAtrasado` (alumno_id, nombre, apellidos, actividades_faltantes: list[str], actividades_reprobadas: list[str]), `AtrasadosResponse` (atrasados: list[AlumnoAtrasado], sin_padron: bool), todos con `extra='forbid'`
- [x] 1.2 Agregar `RankingItem` (alumno_id, nombre, apellidos, aprobadas: int), `RankingResponse` (items: list[RankingItem])
- [x] 1.3 Agregar `NotaFinalItem` (alumno_id, nombre, apellidos, aprobadas: int, total_actividades: int, porcentaje_aprobacion: float), `NotasFinalesResponse` (items: list[NotaFinalItem])
- [x] 1.4 Agregar `ReporteAsignacion` (total_alumnos: int, total_atrasados: int, pct_aprobacion_general: float, total_actividades: int, tiene_datos: bool)

## 2. Servicio de análisis

- [x] 2.1 Crear `backend/app/services/analisis_service.py` — función `_get_entradas_activas(asignacion_id, db, tenant_id)` que consulta el padrón activo vía `PadronRepository` y retorna lista de `EntradaPadron`; retorna `[]` si no hay padrón activo
- [x] 2.2 Implementar `get_atrasados(asignacion_id, db, tenant_id)` — carga entradas activas + calificaciones via `CalificacionRepository.list_by_entradas`; detecta faltantes (entradas sin ninguna calificación) y reprobados (`aprobado = False`); retorna `AtrasadosResponse`
- [x] 2.3 Implementar `get_ranking(asignacion_id, db, tenant_id)` — agrupa calificaciones aprobadas por alumno, filtra alumnos con count >= 1 (RN-09), ordena desc; retorna `RankingResponse`
- [x] 2.4 Implementar `get_notas_finales(asignacion_id, db, tenant_id)` — por cada entrada del padrón activo calcula aprobadas/total/porcentaje; incluye alumnos sin calificaciones con cero; retorna `NotasFinalesResponse`
- [x] 2.5 Implementar `get_reporte(asignacion_id, db, tenant_id)` — llama internamente a `get_atrasados` y `get_notas_finales`; agrega total_alumnos, total_atrasados, pct_aprobacion_general, total_actividades; retorna `ReporteAsignacion`

## 3. RBAC

- [x] 3.1 Agregar permiso `analisis:ver` al catálogo RBAC en `backend/app/services/rbac_seed.py`
- [x] 3.2 Asignar `analisis:ver` a roles PROFESOR, TUTOR y COORDINADOR en el seed

## 4. Router y endpoints

- [x] 4.1 Crear `backend/app/api/v1/routers/analisis.py` con `APIRouter(prefix="/analisis", tags=["analisis"])`
- [x] 4.2 `GET /atrasados` — query param `asignacion_id` (UUID), `require_permission("analisis:ver")`; llama `get_atrasados`; retorna `AtrasadosResponse`
- [x] 4.3 `GET /ranking` — query param `asignacion_id` (UUID), `require_permission("analisis:ver")`; llama `get_ranking`; retorna `RankingResponse`
- [x] 4.4 `GET /notas-finales` — query param `asignacion_id` (UUID), `require_permission("analisis:ver")`; llama `get_notas_finales`; retorna `NotasFinalesResponse`
- [x] 4.5 `GET /reporte` — query param `asignacion_id` (UUID), `require_permission("analisis:ver")`; llama `get_reporte`; retorna `ReporteAsignacion`
- [x] 4.6 Registrar router en `backend/app/main.py`

## 5. Tests

- [x] 5.1 Test unitario: `get_atrasados` — alumno sin calificaciones aparece como atrasado con actividades faltantes vacías y reprobadas vacías (condición a)
- [x] 5.2 Test unitario: `get_atrasados` — alumno con calificación `aprobado = False` aparece como atrasado (condición b)
- [x] 5.3 Test unitario: `get_atrasados` — alumno con todas las actividades aprobadas no aparece
- [x] 5.4 Test unitario: `get_atrasados` — sin padrón activo retorna `AtrasadosResponse(atrasados=[], sin_padron=True)`
- [x] 5.5 Test unitario: `get_ranking` — excluye alumnos sin aprobadas (RN-09); ordena de mayor a menor
- [x] 5.6 Test unitario: `get_ranking` — retorna lista vacía si no hay calificaciones
- [x] 5.7 Test unitario: `get_notas_finales` — alumno sin calificaciones retorna `aprobadas=0, total=0, pct=0.0`
- [x] 5.8 Test unitario: `get_notas_finales` — porcentaje calculado correctamente con N aprobadas de M total
- [x] 5.9 Test unitario: `get_reporte` — `tiene_datos=False` cuando no hay calificaciones ni padrón
- [x] 5.10 Test de integración: RBAC — `403` en los 4 endpoints sin permiso `analisis:ver`
- [x] 5.11 Test de integración: multi-tenant isolation — datos de otro tenant no aparecen en ningún endpoint
