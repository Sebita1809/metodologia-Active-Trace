## Context

C-09 es la primera capacidad de **ingesta de datos** del sistema. Aporta el padrón de alumnos por materia×cohorte, que C-10 (calificaciones) y C-11 (atrasados) consumen vía `EntradaPadron`. Depende de C-06 (`Materia`, `Cohorte`) y C-07 (`Usuario`, `CryptoService`), ambos archivados.

El proyecto sigue Clean Architecture estricta: Routers → Services → Repositories → Models. Patrones ya establecidos y a reutilizar tal cual:
- `BaseTenantModel` (PK UUID server-side, `tenant_id`, `created_at/updated_at`, `deleted_at`).
- `BaseRepository[T]` con `_base_query()` como único punto de scope de tenant + soft-delete.
- PII cifrada con `CryptoService` (AES-256-GCM), descifrada solo en servicio, fuera de logs/`__repr__` (patrón de `Usuario`/`UsuarioService`).
- Auditoría vía `AuditService.registrar(current_user, AccionAuditoria.X, ...)`; `PADRON_CARGAR` ya está en el catálogo.
- RBAC con `require_permission("modulo:accion", scope=...)`; seed idempotente de permisos `ON CONFLICT DO NOTHING` en la migración (patrón de `007`).
- Router fino con dependencia `_get_svc` que construye el servicio con `tenant_id=current_user.tenant_id`.

Tensión de dominio: **RN-05** define el padrón como upsert destructivo sin historial, pero **E6** y el scope de C-09 en `CHANGES.md` lo definen versionado. Esta es la pregunta abierta **PA-01**. Se resuelve a favor del modelo versionado (E6/C-09 son la fuente vigente); RN-05 queda superseded y se anotará al archivar.

## Goals / Non-Goals

**Goals:**
- Modelos `VersionPadron` y `EntradaPadron` con versionado: una sola versión activa por `(tenant_id, materia_id, cohorte_id)`.
- Servicio de import con preview (sin persistir) + confirm (crea versión activa, desactiva la anterior).
- Soporte `.xlsx` (openpyxl) y `.csv` (stdlib) con el mismo mapeo de columnas.
- Cliente `moodle_ws.py` aislado: sync usuarios/actividades, on-demand + nocturna, errores → 502 con reintento, fallback manual.
- Vaciado scope-isolated (RN-04) por soft-delete.
- Permisos `padron:cargar | ver | vaciar` y auditoría `PADRON_CARGAR`.
- TDD: versionado, import xlsx/csv, entrada sin `usuario_id`, aislamiento tenant, mock Moodle + fallback 502.

**Non-Goals:**
- Cálculo de calificaciones / atrasados (C-10/C-11): aquí solo se modela el padrón.
- Implementación del scheduler nocturno concreto (cron del worker): C-09 entrega el cliente y el endpoint on-demand; la activación nocturna es un punto de integración con la infra de jobs.
- Frontend de carga de padrón (pertenece a la fase de frontend).
- Resolver definitivamente PA-01 en la KB (se documenta como decisión; la edición de la KB se hace al archivar).
- Matching difuso alumno↔usuario: el match se hace por `email_hash` exacto; sin match → `usuario_id = NULL`.

## Decisions

### D1 — Dos entidades: `VersionPadron` (cabecera) + `EntradaPadron` (detalle)
Fiel a E6. `VersionPadron` lleva `materia_id`, `cohorte_id`, `cargado_por` (FK `usuarios`), `cargado_at`, `activa: bool`, `origen: str` (`archivo` | `moodle`). `EntradaPadron` lleva `version_id` (FK con `ondelete=RESTRICT`, soft-delete vía base), `usuario_id` (FK nullable), y datos desnormalizados `nombre/apellidos/email/comision/regional`. Ambas heredan `BaseTenantModel`.
- *Alternativa descartada*: una sola tabla con columna de versión → complica la consulta "activa" y el vaciado; E6 ya prescribe dos entidades.

### D2 — "Una activa por (materia, cohorte)" se garantiza en el servicio dentro de una transacción
La activación es: dentro de una sola transacción, `UPDATE version_padron SET activa=false WHERE (tenant,materia,cohorte) AND activa=true`, luego insertar la nueva con `activa=true`. Se añade además un **índice único parcial** `UNIQUE (tenant_id, materia_id, cohorte_id) WHERE activa = true AND deleted_at IS NULL` como red de seguridad a nivel DB.
- *Alternativa descartada*: confiar solo en el código de servicio → sin la garantía de DB, un bug o carrera podría dejar dos activas. El índice parcial es barato y es la defensa correcta en Postgres.

### D3 — Preview y confirm separados; el preview no persiste
El parseo del archivo vive en un helper puro del servicio (`_parsear_archivo(bytes, content_type) -> (entradas, errores)`). El endpoint de preview llama al parser y devuelve el resultado sin tocar la DB. El de confirm vuelve a parsear (o recibe el payload ya estructurado) y persiste. Mantener el parser puro lo hace testeable sin DB ni HTTP.
- *Alternativa descartada*: cachear el preview server-side entre llamadas → introduce estado/sesión innecesario; reparsing es simple y determinista.

### D4 — Parsers: `openpyxl` para xlsx, `csv` stdlib para csv, con normalización común
Un único contrato de columnas (`nombre`, `apellidos`, `email`, `comision`, `regional`) y una función de normalización compartida tras la extracción de filas, de modo que ambos formatos converjan al mismo modelo intermedio. `openpyxl` es nueva dependencia del backend (declarar en `pyproject`/requirements).
- *Alternativa descartada*: `pandas` → demasiado pesado para un parseo tabular simple.

### D5 — Match alumno ↔ usuario por `email_hash` exacto
Al confirmar, por cada entrada se calcula `CryptoService.hash_deterministic(email)` y se busca el `Usuario` por `email_hash` (reutiliza `UsuarioRepository.get_by_email_hash`). Si existe → `usuario_id` se setea; si no → queda `NULL`. El `email` de la entrada se cifra siempre.
- *Alternativa descartada*: match por legajo o nombre → frágil; el email es el identificador único por tenant ya implementado.

### D6 — Cliente `moodle_ws.py` aislado, con reintento y errores tipados
El cliente expone p.ej. `async fetch_padron(curso_ref) -> list[EntradaCruda]` y `async fetch_actividades(...)`. Usa un cliente HTTP async (httpx) con timeout y política de reintento (N intentos, backoff) ante errores transitorios. Define una excepción de dominio `MoodleIntegrationError`; el router/servicio la traduce a `HTTPException(status_code=502)`. La confirmación de versión solo ocurre si la obtención de datos fue completa (no se activa una versión parcial).
- *Alternativa descartada*: dejar que el error de red propague como 500 → viola la spec (debe ser 502) y mezcla fallas de infra propia con fallas del LMS externo.

### D7 — Vaciado = soft-delete de versiones y entradas del scope
`vaciar(materia_id, cohorte_id)` hace soft-delete de las `VersionPadron` del scope y de sus `EntradaPadron`. Respeta RN-04: el servicio aplica el scope del actor (PROFESOR → `propio` vía permiso `scope="propio"`; COORDINADOR/ADMIN → `global`). Nunca borrado físico.

### D8 — Permisos y seed en la migración 008
Permisos nuevos: `padron:cargar`, `padron:ver`, `padron:vaciar`. Matriz: PROFESOR (`propio`) → los tres; COORDINADOR y ADMIN (`global`) → los tres. Seed idempotente `ON CONFLICT DO NOTHING` para todos los tenants activos, replicando `_seed_*_for_all_tenants()` de `007`. Se añaden también a `rbac_seed.py` (`PERMISSIONS` + `MATRIX`) para tenants nuevos.

### D9 — Endpoints bajo `/api/padron`
- `POST /padron/preview` (`padron:cargar`) — multipart file → preview (no persiste).
- `POST /padron/confirmar` (`padron:cargar`, 201) — crea versión activa desde archivo.
- `POST /padron/sync-moodle` (`padron:cargar`) — sync on-demand desde Moodle; 502 ante fallo.
- `GET /padron` (`padron:ver`) — versión activa de `(materia, cohorte)`, email descifrado.
- `GET /padron/versiones` (`padron:ver`) — historial de versiones de `(materia, cohorte)`.
- `DELETE /padron` (`padron:vaciar`) — vaciar scope.
Todos toman identidad/tenant del JWT; `materia_id`/`cohorte_id` son datos de negocio validados, nunca identidad.

## Risks / Trade-offs

- **[Dos versiones activas por carrera/bug]** → índice único parcial en DB (D2) + activación transaccional; test explícito "activar desactiva la anterior".
- **[PII (email) filtrada en logs o respuestas de error de import/preview]** → email siempre cifrado en reposo; parser y errores reportan solo posición/fila, nunca el valor; `__repr__` de `EntradaPadron` excluye `email` (patrón `Usuario`).
- **[Fuga cross-tenant en consultas de padrón]** → todo acceso vía `_base_query()`; test de aislamiento (T1 no ve padrón de T2).
- **[Falla del LMS deja padrón parcial]** → la versión solo se activa tras obtener los datos completos; ante fallo se hace rollback y se responde 502 (D6).
- **[Archivo malicioso / muy grande]** → validar content-type y extensión; límite de tamaño; `openpyxl` en modo read-only. Mitigación a confirmar en implementación.
- **[Conflicto KB: RN-05 vs versionado]** → decisión documentada (PA-01); RN-05 superseded. Riesgo de confusión para futuros agentes hasta editar la KB → se anota en proposal/Impact y al archivar.
- **[Nueva dependencia openpyxl]** → superficie de dependencias mayor; aceptable y estándar para xlsx.

## Migration Plan

1. Migración `008_padron_y_moodle` (down_revision `007`):
   - `create_table version_padron` (+ FKs `tenant_id`, `materia_id`, `cohorte_id`, `cargado_por`; índices `ix_version_padron_tenant_id`, `ix_version_padron_tenant_materia_cohorte`; índice único parcial de "una activa").
   - `create_table entrada_padron` (+ FKs `tenant_id`, `version_id`, `usuario_id` nullable; índices `ix_entrada_padron_tenant_id`, `ix_entrada_padron_version`).
   - Seed idempotente de permisos `padron:*` + matriz para todos los tenants activos.
2. `downgrade()`: drop índices + tablas en orden inverso (entrada_padron antes que version_padron). El seed de permisos se deja (consistente con migraciones previas) o se revierte si se decide; por defecto no se revierte el seed.
3. Sin backfill de datos (capacidad nueva).
4. Rollback: `alembic downgrade -1` elimina ambas tablas; no afecta C-06/C-07.

## Open Questions

- **PA-01 (formal)**: la edición de `knowledge-base/05_reglas_de_negocio.md` (marcar RN-05 superseded) y `10_preguntas_abiertas.md` se hace al archivar el change, no en esta capa.
- **Scheduler nocturno**: qué componente dispara la sync nocturna (cron del worker async / N8N) se define con la infra de jobs; aquí solo se entrega el cliente y el endpoint on-demand.
- **Mapeo de cursos Moodle → (materia, cohorte)**: la convención exacta de identificación del curso en el LMS se confirma en implementación del cliente; no afecta el modelo de datos.
- **Política de reintento concreta** (número de intentos, backoff, timeout) → parametrizable por configuración; valores por defecto a fijar en implementación.
