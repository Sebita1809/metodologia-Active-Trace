# Tasks — C-09 padron-ingesta-moodle

> Strict TDD: test que falla → código mínimo → triangulación → refactor.
> Tests con PostgreSQL real (sin mocks de DB). Moodle WS sí se mockea (servicio externo).
> Cobertura ≥80% líneas, ≥90% reglas de negocio.

## 1. Modelos y migración

- [x] 1.1 Crear `app/models/version_padron.py` (`VersionPadron(BaseTenantModel)`: `materia_id`, `cohorte_id` FKs RESTRICT; `cargado_por` FK `usuarios` RESTRICT; `cargado_at: datetime`; `activa: bool` default false; `origen: str` `archivo|moodle`). `__repr__` sin PII.
- [x] 1.2 Crear `app/models/entrada_padron.py` (`EntradaPadron(BaseTenantModel)`: `version_id` FK `version_padron` RESTRICT; `usuario_id` FK `usuarios` RESTRICT **nullable**; `nombre`, `apellidos`, `comision`, `regional`; `email: Text` ciphertext). `__repr__` NUNCA expone `email`.
- [x] 1.3 Registrar ambos modelos en `app/models/__init__.py`.
- [x] 1.4 Crear migración `backend/alembic/versions/008_padron_y_moodle.py` (down_revision `007`): tablas `version_padron` y `entrada_padron` con FKs e índices (`ix_*_tenant_id`, `ix_version_padron_tenant_materia_cohorte`, `ix_entrada_padron_version`).
- [x] 1.5 Añadir índice **único parcial** `uq_version_padron_activa` sobre `(tenant_id, materia_id, cohorte_id) WHERE activa = true AND deleted_at IS NULL`.
- [x] 1.6 `downgrade()`: drop índices + `entrada_padron` + `version_padron` en orden inverso.
- [ ] 1.7 Aplicar la migración contra la DB de test y verificar upgrade/downgrade. *(requiere entorno de ejecución)*

## 2. Repositorios

- [x] 2.1 Test: `VersionPadronRepository` aísla por tenant (T1 no ve versiones de T2) usando `_base_query()`.
- [x] 2.2 Implementar `app/repositories/version_padron_repository.py`: `get_activa(materia_id, cohorte_id)`, `list_versiones(materia_id, cohorte_id)`, `desactivar_activa(materia_id, cohorte_id) -> int` (UPDATE activa=false scoped), `soft_delete_scope(materia_id, cohorte_id) -> int`.
- [x] 2.3 Test: `EntradaPadronRepository` aísla por tenant; `bulk_create` inserta entradas; `list_by_version` filtra por versión + tenant + no borradas.
- [x] 2.4 Implementar `app/repositories/entrada_padron_repository.py` (`bulk_create`, `list_by_version`, `soft_delete_by_versions`).

## 3. Parser de archivos (puro, sin DB)

- [x] 3.1 Test: parsear `.csv` válido devuelve N entradas normalizadas (nombre, apellidos, email, comision, regional).
- [x] 3.2 Test: parsear `.xlsx` válido (openpyxl) devuelve las mismas entradas que el csv equivalente.
- [x] 3.3 Test: archivo con columnas faltantes / formato inválido devuelve lista de errores y NO entradas; errores no contienen el email en claro.
- [x] 3.4 Implementar parser en `padron_parser.py` (helper puro `parsear_archivo(data: bytes, content_type) -> (entradas, errores)`); añadir `openpyxl` a dependencias del backend.

## 4. PadronService — preview, confirm, versionado, vaciado

- [x] 4.1 Test: `preview(file)` devuelve entradas + errores y NO persiste ninguna `VersionPadron`/`EntradaPadron`.
- [x] 4.2 Implementar `app/services/padron_service.py` con `preview(...)` (parser + dry-run, sin DB writes).
- [x] 4.3 Test (regla clave): `confirmar(...)` crea versión `activa=true` y, si ya existía una activa para `(materia, cohorte)`, la anterior queda `activa=false` y conservada.
- [x] 4.4 Test: `confirmar(...)` cifra `email` de cada entrada (valor persistido ≠ texto plano).
- [x] 4.5 Test: entrada cuyo email no matchea ningún `Usuario` queda con `usuario_id = NULL`; la que matchea por `email_hash` setea `usuario_id`.
- [x] 4.6 Implementar `confirmar(...)`: transacción → `desactivar_activa` + crear `VersionPadron` activa + `bulk_create` entradas (cifrando email, resolviendo `usuario_id` por `email_hash`).
- [x] 4.7 Test: `confirmar(...)` registra `AuditService.registrar(..., PADRON_CARGAR, filas_afectadas=N, detalle=...)` con actor del JWT.
- [x] 4.8 Implementar la emisión de auditoría `PADRON_CARGAR` en `confirmar(...)`.
- [x] 4.9 Test: `ver_padron_activo(materia, cohorte)` devuelve entradas de la versión activa con `email` descifrado.
- [x] 4.10 Implementar `ver_padron_activo(...)` y `list_versiones(...)` (descifrando email en la respuesta).
- [x] 4.11 Test (RN-04): `vaciar(materia A, cohorte X)` soft-deletea solo ese scope; `(materia B, cohorte X)` y `(materia A, cohorte Y)` quedan intactos.
- [x] 4.12 Implementar `vaciar(materia, cohorte)` (soft-delete de versiones + entradas del scope).

## 5. Integración Moodle Web Services

- [x] 5.1 Test: cliente `moodle_ws` con HTTP mockeado devuelve entradas normalizadas de un curso (sin tocar DB).
- [x] 5.2 Implementar `app/integrations/moodle_ws.py`: cliente async (httpx) con URL/token inyectados; `fetch_padron(...)`, `fetch_actividades(...)`; excepción `MoodleIntegrationError`.
- [x] 5.3 Test: error transitorio del LMS se reintenta según política antes de propagar.
- [x] 5.4 Implementar reintento con backoff y timeout en el cliente.
- [x] 5.5 Test: `sync_moodle(...)` exitoso crea versión activa con `origen="moodle"` y registra `PADRON_CARGAR`.
- [x] 5.6 Test (fallback 502): cuando Moodle falla tras reintentos, `sync_moodle(...)` propaga `MoodleIntegrationError`, NO activa una versión parcial (rollback) y el endpoint responde HTTP 502.
- [x] 5.7 Implementar `sync_moodle(...)` en `PadronService` (obtener datos completos → reutilizar lógica de `confirmar`; ante fallo, rollback).

## 6. Schemas (Pydantic v2, extra='forbid')

- [x] 6.1 Crear `app/schemas/padron.py`: `PadronPreviewResponse` (entradas + errores), `ConfirmarPadronRequest`, `VersionPadronResponse`, `EntradaPadronResponse` (email descifrado), `SyncMoodleRequest`, `VaciarPadronRequest`. Todos con `model_config = ConfigDict(extra='forbid')`.

## 7. Router y wiring

- [x] 7.1 Crear `app/api/v1/routers/padron.py` con `_get_svc` (tenant del JWT) y endpoints:
  - `POST /padron/preview` (`padron:cargar`) — multipart, no persiste.
  - `POST /padron/confirmar` (`padron:cargar`, 201).
  - `POST /padron/sync-moodle` (`padron:cargar`) — 502 ante `MoodleIntegrationError`.
  - `GET /padron` (`padron:ver`).
  - `GET /padron/versiones` (`padron:ver`).
  - `DELETE /padron` (`padron:vaciar`).
- [x] 7.2 Sin lógica de negocio en el router: todo delega a `PadronService`. Identidad/tenant SIEMPRE del JWT; `materia_id`/`cohorte_id` validados como dato de negocio.
- [x] 7.3 Registrar el router `padron` en el agregador de la API v1.
- [x] 7.4 Mapear `MoodleIntegrationError` → `HTTPException(502)` (handler o try/except en el endpoint).

## 8. RBAC seed

- [x] 8.1 Añadir permisos `padron:cargar`, `padron:ver`, `padron:vaciar` y matriz (PROFESOR `propio`; COORDINADOR/ADMIN `global`) al seed idempotente de la migración 008 (`ON CONFLICT DO NOTHING`, para todos los tenants activos).
- [x] 8.2 Añadir los mismos permisos + matriz a `app/services/rbac_seed.py` (`PERMISSIONS` + `MATRIX`) para tenants nuevos.
- [x] 8.3 Test: usuario sin `padron:cargar`/`padron:ver`/`padron:vaciar` recibe 403 en los endpoints correspondientes (fail-closed).

## 9. Tests de endpoint (integración HTTP) y cierre

- [x] 9.1 Test E2E: preview → confirmar → ver devuelve el padrón cargado; reconfirmar desactiva la versión previa.
- [x] 9.2 Test E2E: aislamiento de tenant en los endpoints (T1 no ve/maneja padrón de T2).
- [x] 9.3 Test E2E: `sync-moodle` con cliente mockeado OK crea versión; con fallo responde 502.
- [ ] 9.4 Verificar cobertura (≥80% líneas, ≥90% reglas de negocio del padrón) y que ningún test mockea la DB. *(requiere ejecutar pytest con coverage)*
- [x] 9.5 Verificar ≤500 LOC por archivo backend; refactor si algún archivo lo excede. *(realizado: todos los archivos ≤500 LOC)*
- [x] 9.6 Marcar `C-09` como completado en `CHANGES.md` y anotar RN-05 superseded / PA-01 resuelto (al archivar).
