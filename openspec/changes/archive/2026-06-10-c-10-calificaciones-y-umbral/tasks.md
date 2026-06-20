## 1. Modelos SQLAlchemy y migración

- [x] 1.1 Crear `backend/app/models/umbral_materia.py` — modelo `UmbralMateria` con `id`, `tenant_id`, `asignacion_id`, `materia_id`, `umbral_pct` (int, default 60), `valores_aprobatorios` (ARRAY/JSONB), usando `BaseMixin` (soft-delete, timestamps); constraint UNIQUE `(tenant_id, asignacion_id)`
- [x] 1.2 Crear `backend/app/models/calificacion.py` — modelo `Calificacion` con `id`, `tenant_id`, `entrada_padron_id` (FK → `entrada_padron`), `materia_id`, `actividad` (str), `nota_numerica` (Numeric, nullable), `nota_textual` (str, nullable), `aprobado` (bool), `origen` (Enum: `Importado`|`Manual`), `importado_at`, usando `BaseMixin`
- [x] 1.3 Generar migración `alembic/versions/009_calificacion_umbral_materia.py` — crea tablas `calificacion` y `umbral_materia` con sus FKs e índices
- [x] 1.4 Registrar ambos modelos en `backend/app/models/__init__.py`

## 2. Schemas Pydantic

- [x] 2.1 Crear `backend/app/schemas/calificacion.py` — `CalificacionRead`, `OrigenEnum`; todos con `extra='forbid'`
- [x] 2.2 Crear `backend/app/schemas/umbral_materia.py` — `UmbralMateriaRead`, `UmbralMateriaUpsert` (umbral_pct, valores_aprobatorios); `extra='forbid'`
- [x] 2.3 Agregar a `calificacion.py` los schemas de import: `ActividadDetectada`, `ImportPreviewResponse` (actividades_numericas, actividades_textuales, alumnos_detectados), `ImportConfirmRequest` (asignacion_id, actividades_seleccionadas)
- [x] 2.4 Agregar `FinalizacionPreviewResponse` — lista de `{alumno, actividad}` sin calificar

## 3. Repositorios

- [x] 3.1 Crear `backend/app/repositories/calificacion_repository.py` — `CalificacionRepository` extendiendo `BaseRepository`: `create_many(entries)`, `list_by_asignacion(asignacion_id, tenant_id)`, `delete_by_asignacion(asignacion_id, tenant_id)` (soft-delete), filtrado por tenant en todas las queries
- [x] 3.2 Crear `backend/app/repositories/umbral_materia_repository.py` — `UmbralMateriaRepository`: `get_by_asignacion(asignacion_id, tenant_id)`, `upsert(asignacion_id, tenant_id, data)`

## 4. Parser de archivos LMS

- [x] 4.1 Crear `backend/app/services/lms_parser.py` — función `parse_lms_grades(file_bytes, filename)` que acepta `.xlsx` y `.csv`; detecta columnas numéricas (terminan en `(Real)`, RN-01) y columnas textuales; retorna `DataFrame` o estructura interna
- [x] 4.2 Implementar `detect_activities(parsed)` — retorna `{numericas: [str], textuales: [str]}`
- [x] 4.3 Implementar `parse_finalizacion(file_bytes, filename)` — parsea reporte de finalización del LMS y retorna lista de `{alumno_email, actividad, finalizado}`
- [x] 4.4 Manejo de errores: formato inválido, columnas de identificación ausentes → raise `ValueError` con mensaje descriptivo

## 5. Servicio de calificaciones

- [x] 5.1 Crear `backend/app/services/calificacion_service.py` — función `_compute_aprobado(nota_numerica, nota_textual, umbral_pct, valores_aprobatorios)` — lógica RN-01/RN-02/RN-03; no accede a DB
- [x] 5.2 Implementar `preview_import(file_bytes, filename, asignacion_id, db, tenant_id)` — parsea archivo, detecta actividades, retorna `ImportPreviewResponse` sin persistir
- [x] 5.3 Implementar `confirm_import(file_bytes, filename, request, actor_id, db, tenant_id)` — parsea, filtra actividades seleccionadas, llama `_compute_aprobado` por cada fila, persiste vía `CalificacionRepository.create_many`, emite audit `CALIFICACIONES_IMPORTAR`
- [x] 5.4 Implementar `finalizacion_preview(file_bytes, filename, asignacion_id, db, tenant_id)` — parsea reporte de finalización, cruza con calificaciones existentes, retorna actividades textuales finalizadas sin calificación (RN-07/RN-08); sin persistencia

## 6. Servicio de umbral

- [x] 6.1 Crear `backend/app/services/umbral_materia_service.py` — `UmbralMateriaService.upsert(asignacion_id, umbral_pct, valores_aprobatorios, tenant_id, db)` — crea o actualiza `UmbralMateria`
- [x] 6.2 Implementar `UmbralMateriaService.get(asignacion_id, tenant_id, db)` — retorna `UmbralMateriaRead` o defaults (60, ["Satisfactorio", "Supera lo esperado"]) si no existe

## 7. Audit codes y RBAC

- [x] 7.1 Agregar `CALIFICACIONES_IMPORTAR = "CALIFICACIONES_IMPORTAR"` al enum `AccionAuditoria` en `backend/app/services/audit_codes.py` (already existed from C-04/C-05)
- [x] 7.2 Agregar permisos `calificaciones:importar`, `calificaciones:ver`, `calificaciones:configurar` al catálogo RBAC (`backend/app/services/rbac_seed.py`) — added `ver` and `configurar` (importar already existed)
- [x] 7.3 Asignar permisos al rol `PROFESOR` (importar, ver, configurar) y `COORDINADOR` (importar, ver, configurar) en el seed/catálogo

## 8. Router y endpoints

- [x] 8.1 Crear `backend/app/api/v1/routers/calificaciones.py` con `APIRouter(tags=["calificaciones"])`
- [x] 8.2 `POST /preview` — multipart file upload, `require_permission("calificaciones:importar")`; llama `preview_import`; retorna `ImportPreviewResponse`
- [x] 8.3 `POST /import` — multipart file + JSON body con `ImportConfirmRequest`, `require_permission("calificaciones:importar")`; llama `confirm_import`; retorna filas creadas
- [x] 8.4 `POST /finalizacion-preview` — multipart file + `asignacion_id`, `require_permission("calificaciones:importar")`; llama `finalizacion_preview`; retorna `FinalizacionPreviewResponse`
- [x] 8.5 `GET /` — query params `asignacion_id`, `require_permission("calificaciones:ver")`; retorna lista de `CalificacionRead`
- [x] 8.6 `PUT /umbral` — body `UmbralMateriaUpsert` + `asignacion_id`, `require_permission("calificaciones:configurar")`; llama `UmbralMateriaService.upsert`
- [x] 8.7 `GET /umbral` — query param `asignacion_id`, `require_permission("calificaciones:ver")`; retorna `UmbralMateriaRead`
- [x] 8.8 Registrar router en `backend/app/main.py`

## 9. Tests

- [x] 9.1 Test unitario: `_compute_aprobado` numérico — nota < umbral → `False`, nota == umbral → `True`, nota > umbral → `True`
- [x] 9.2 Test unitario: `_compute_aprobado` textual — "Satisfactorio" → `True`, "Supera lo esperado" → `True`, "No satisfactorio" → `False`
- [x] 9.3 Test unitario: `_compute_aprobado` con umbral por defecto 60 cuando no se pasan parámetros
- [x] 9.4 Test de integración: `preview_import` con archivo xlsx real/fixture — detecta columnas `(Real)` y textuales; no crea `Calificacion`
- [x] 9.5 Test de integración: `confirm_import` — crea solo actividades seleccionadas; emite `AuditLog` con `CALIFICACIONES_IMPORTAR`
- [x] 9.6 Test de integración: `confirm_import` — `aprobado` correcto según umbral configurado vs. defecto
- [x] 9.7 Test de integración: `finalizacion_preview` — retorna solo actividades textuales finalizadas sin calificación; excluye actividades numéricas (RN-08)
- [x] 9.8 Test de integración: `upsert` de umbral — crea nuevo; actualiza existente
- [x] 9.9 Test de integración: aislamiento de umbral — cambio de umbral del docente A no afecta calificaciones del docente B en misma materia
- [x] 9.10 Test de integración: RBAC — `403` en todos los endpoints sin permiso correspondiente
- [x] 9.11 Test de integración: multi-tenant isolation — consultas no devuelven datos de otro tenant
