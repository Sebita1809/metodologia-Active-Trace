## 1. Modelos y migración

- [x] 1.1 Crear `backend/app/models/domain/version_padron.py` con `VersionPadron` (id, materia_id, cohorte_id, tenant_id, activa, origen, cargado_por, cargado_at)
- [x] 2.1 Crear `backend/app/models/domain/entrada_padron.py` con `EntradaPadron` (id, version_padron_id, tenant_id, nombre, apellidos, email, comision, regional, usuario_id nullable)
- [x] 3.1 Agregar foreign keys y relaciones en ambos modelos (VersionPadron → Materia, Cohorte, Usuario; EntradaPadron → VersionPadron, Usuario)
- [x] 4.1 Exportar ambos modelos en `backend/app/models/domain/__init__.py` y en `backend/app/models/__init__.py`
- [x] 5.1 Crear migración Alembic `007_padron` con tablas `version_padron`, `entrada_padron`, índices (materia+cohorte+activa, email, version_id)
- [x] 5.2 Agregar seed del permiso `padron:importar` (UUID determinístico) en migración 007
- [x] 5.3 Agregar seed de `rol_permiso` para COORDINADOR (scope global) y PROFESOR (scope `propio`) en migración 007
- [x] 5.4 Agregar seed de `rol_permiso` para ADMIN (scope global) en migración 007

## 2. Schemas Pydantic

- [x] 2.1 Crear `backend/app/schemas/padron.py` con `VersionPadronResponse`, `VersionPadronListResponse`, `EntradaPadronResponse`
- [x] 2.2 Crear `VersionPadronCreate` con datos de entrada para creación manual
- [x] 2.3 Crear `PadronPreviewResponse` con columnas detectadas, total_rows, sample_rows, errores por fila
- [x] 2.4 Crear `PadronImportConfirmRequest` con preview_token o file_hash
- [x] 2.5 Crear `PadronImportConfirmResponse` con version_id y resumen de entradas creadas
- [x] 2.6 Crear `PadronClearDataResponse` con confirmación de eliminación

## 3. Repositorios

- [x] 3.1 Agregar método `hard_delete` en `backend/app/repositories/base.py` para borrado físico
- [x] 3.2 Crear `backend/app/repositories/padron/__init__.py`
- [x] 3.3 Crear `backend/app/repositories/padron/version_padron_repository.py` con `VersionPadronRepository` (create, get_by_id, get_active_by_materia_cohorte, list_by_materia_cohorte, activate_deactivate, hard_delete_by_materia_cohorte)
- [x] 3.4 Crear `backend/app/repositories/padron/entrada_padron_repository.py` con `EntradaPadronRepository` (bulk_create, get_by_version, hard_delete_by_version, count_by_version)
- [x] 3.5 Agregar filtro de tenant en todos los queries de ambos repositorios

## 4. File Parser (xlsx/csv)

- [x] 4.1 Crear `backend/app/services/padron/file_parser_service.py` con `FileParserService`
- [x] 4.2 Implementar `parse_xlsx(file)` con openpyxl: leer filas, detectar columnas por header
- [x] 4.3 Implementar `parse_csv(file)` con csv.DictReader: leer filas, detectar columnas
- [x] 4.4 Implementar `auto_detect_columns(headers)` con fuzzy matching a campos conocidos (nombre, apellidos, email, comision, regional)
- [x] 4.5 Implementar `validate_rows(rows, column_map)` con validación por fila (sin fail-fast), recolectar errores
- [x] 4.6 Implementar `build_preview(parsed_data)` con column_mapping, total_rows, sample_rows (primeras 5), errores
- [x] 4.7 Implementar `parse(file)` como método público que detecta formato y delega

## 5. PadronService — Gestión

- [x] 5.1 Crear `backend/app/services/padron/__init__.py`
- [x] 5.2 Crear `backend/app/services/padron/padron_service.py` con `PadronService` e inyección de repositorios
- [x] 5.3 Implementar `create_version(materia_id, cohorte_id, usuario_id, origen, entradas)` con scope de tenant + validación de existencia de materia/cohorte
- [x] 5.4 Implementar `activate_version(version_id)` con desactivación de versión activa previa (solo una activa por materia+cohorte)
- [x] 5.5 Implementar `get_active_version(materia_id, cohorte_id)` con todas las entradas
- [x] 5.6 Implementar `list_versions(materia_id, cohorte_id)` ordenado por cargado_at DESC
- [x] 5.7 Implementar `clear_subject_data(materia_id, cohorte_id)` con guard de permiso `propio` y hard delete
- [x] 5.8 Integrar `AuditService.log(AuditAction.PADRON_CARGAR, ...)` en create_version, activate_version y clear_subject_data

## 6. PadronImportService — Importación desde archivo

- [x] 6.1 Crear `backend/app/services/padron/padron_import_service.py` con `PadronImportService`
- [x] 6.2 Implementar `preview_file(file)` que delega en FileParserService y retorna preview
- [x] 6.3 Implementar `confirm_import(preview_token)` que delega en PadronService para crear version + activar
- [x] 6.4 Implementar `auto_match_usuario(email)` que busca Usuario por email en el tenant
- [x] 6.5 Integrar auto_match_usuario en confirm_import para setear usuario_id cuando hay match

## 7. Moodle WS Client

- [x] 7.1 Crear `backend/app/integrations/moodle_ws.py` con clase `MoodleWSClient`
- [x] 7.2 Implementar `__init__(tenant_config)` que lee MOODLE_WS_URL y MOODLE_WS_TOKEN
- [x] 7.3 Implementar `get_enrolled_users(course_id)` que llama a `core_enrol_get_enrolled_users`
- [x] 7.4 Implementar retry con exponential backoff (3 intentos) y excepción tipada `MoodleConnectionError`
- [x] 7.5 Mapear `MoodleConnectionError` a HTTP 502 en la capa de router

## 8. Sincronización on-demand desde Moodle

- [x] 8.1 Implementar `PadronService.sync_from_moodle(materia_id, cohorte_id, moodle_course_id, ws_url, ws_token)` que orquesta: MoodleWSClient → fetch → mapear → crear VersionPadron con origen="moodle"
- [x] 8.2 La resolución de course_id se pasa desde el request (moodle_course_id); la resolución materia→course_id será añadida cuando se agregue el campo a Materia
- [x] 8.3 El router devuelve 400 si el tenant no tiene config Moodle (ws_url/ws_token)

## 9. Nightly Sync Worker

- [x] 9.1 Crear `backend/app/workers/padron_sync.py` con bucle autónomo de sincronización nocturna
- [x] 9.2 Implementar iteración de todos los tenants con config Moodle
- [x] 9.3 Implementar iteración de materias activas × cohortes por tenant (desde Asignacion)
- [x] 9.4 Implementar mecanismo de lock por tenant (saltar si sync previa aún corriendo)
- [x] 9.5 Integrar con PadronService.sync_from_moodle para cada materia+cohorte (usa repos directamente)
- [x] 9.6 Agregar logging de progreso y errores por tenant/materia/cohorte
- [x] 9.7 Configurar sleep entre iteraciones

## 10. Router /api/padron

- [x] 10.1 Crear `backend/app/api/v1/routers/padron.py` con `APIRouter(prefix="/padron")`
- [x] 10.2 Implementar `POST /import/preview` protegido con permiso `padron:importar`
- [x] 10.3 Implementar `POST /import/confirm` protegido con `padron:importar`
- [x] 10.4 Implementar `GET /{materia_id}/{cohorte_id}` protegido con `padron:importar` — retorna versión activa
- [x] 10.5 Implementar `GET /{materia_id}/{cohorte_id}/versiones` protegido con `padron:importar` — lista histórico
- [x] 10.6 Implementar `POST /{materia_id}/{cohorte_id}/activar/{version_id}` protegido con `padron:importar`
- [x] 10.7 Implementar `POST /sync/moodle` protegido con `padron:importar` — sincronización on-demand
- [x] 10.8 Implementar `DELETE /{materia_id}/{cohorte_id}` protegido con `padron:importar` — clear subject data (F1.5, RN-04)
- [x] 10.9 Agregar guards RBAC con scope (`propio` para PROFESOR, global para COORDINADOR/ADMIN)
- [x] 10.10 Registrar router en `main.py` (ya registrado)

## 11. Tests

- [x] 11.1 Crear `backend/tests/test_padron/conftest.py` con fixtures (carrera, materia, cohorte, version, entrada, auth_headers por rol)
- [x] 11.2 Test: crear VersionPadron con datos válidos retorna versión con activa=False
- [x] 11.3 Test: crear EntradaPadron con usuario_id=null es aceptado
- [x] 11.4 Test: activar versión desactiva la versión activa previa para misma materia+cohorte
- [x] 11.5 Test: activar versión ya activa es idempotente
- [x] 11.6 Test: get_active_version retorna 404 si no hay versión activa
- [x] 11.7 Test: list_versions retorna ordenado por fecha descendente
- [x] 11.8 Test: preview archivo xlsx válido retorna columnas detectadas + sample rows + 0 errores
- [x] 11.9 Test: preview archivo sin columna email retorna error de columna faltante
- [x] 11.10 Test: preview archivo con errores por fila retorna errores sin fail-fast
- [x] 11.11 Test: preview formato no soportado (.pdf) retorna 400
- [x] 11.12 Test: confirm import crea VersionPadron con origen="archivo" y activa
- [x] 11.13 Test: confirm import auto-matchea email existente con Usuario del tenant
- [x] 11.14 Test: confirm import deja usuario_id null para email sin match
- [x] 11.15 Test: MoodleWSClient.get_enrolled_users exitoso retorna lista de usuarios
- [x] 11.16 Test: MoodleWSClient con Moodle unreachable lanza MoodleConnectionError
- [x] 11.17 Test: on-demand sync desde Moodle exitoso crea VersionPadron con origen="moodle"
- [x] 11.18 Test: on-demand sync con Moodle down retorna 502 (mock client)
- [x] 11.19 Test: retry succeeds en segundo intento
- [x] 11.20 Test: todos los retries fallan → 502
- [x] 11.21 Test: clear subject data hard-deletea todas las versiones y entradas para materia+cohorte
- [x] 11.22 Test: PROFESOR puede importar para materia propia pero no para materia de otro
- [x] 11.23 Test: COORDINADOR puede importar para cualquier materia del tenant
- [x] 11.24 Test: PROFESOR puede limpiar materia propia pero no materia ajena
- [x] 11.25 Test: COORDINADOR puede limpiar cualquier materia del tenant
- [x] 11.26 Test: aislamiento multi-tenant — operación en tenant A no afecta tenant B
- [x] 11.27 Test: activar versión crea evento de auditoría PADRON_CARGAR
- [x] 11.28 Test: clear subject data crea evento de auditoría PADRON_CARGAR
- [x] 11.29 Test: nightly sync procesa todos los tenants con config Moodle
- [x] 11.30 Test: nightly sync salta tenant con lock activo
