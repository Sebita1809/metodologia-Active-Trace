# Tasks — C-12 Comunicaciones Cola Worker

> Strict TDD por task: **Safety Net** (correr tests existentes de archivos que se modifican) → **RED** (test que falla primero) → **GREEN** (mínimo código) → **TRIANGULATE** (2do+ caso) → **REFACTOR** (sin cambiar comportamiento). Tests con DB real/efímera; el canal de envío se mockea, NUNCA la DB.

## 1. Modelo SQLAlchemy y migración

- [x] 1.1 RED: test de creación de `Comunicacion` — al crearse, `estado == Pendiente` y `enviado_at is None`. GREEN: crear `backend/app/models/comunicacion.py` con campos E21 (`id`, `tenant_id`, `enviado_por` FK Usuario, `materia_id` FK Materia, `destinatario`, `asunto`, `cuerpo`, `estado` Enum, `lote_id`, `enviado_at`) + `aprobado_at`/`aprobado_por` (nullable) + `BaseMixin` (soft delete, timestamps). TRIANGULATE: default de `lote_id`/`estado`. REFACTOR.
- [x] 1.2 Definir el Enum `EstadoComunicacion` (`Pendiente | Enviando | Enviado | Error | Cancelado`) como tipo PostgreSQL ENUM o VARCHAR+CHECK; nunca enteros.
- [x] 1.3 Generar migración Alembic `0XX_comunicacion.py` — crea tabla `comunicacion` con FKs, tipo Enum, índices `(tenant_id, lote_id)` y `(tenant_id, estado)`; comentario en migración marcando `destinatario` como PII cifrada; `downgrade` reversible.
- [x] 1.4 Registrar `Comunicacion` en `backend/app/models/__init__.py`.

## 2. Schemas Pydantic

- [x] 2.1 RED: test de que `ComunicacionRead` y `EncolarLoteRequest` rechazan campos extra. GREEN: crear `backend/app/schemas/comunicacion.py` con `EstadoComunicacionEnum`, `ComunicacionRead` (incluye `destinatario` descifrado), todos con `model_config = ConfigDict(extra='forbid')`. TRIANGULATE: campo válido pasa, campo extra falla. REFACTOR.
- [x] 2.2 Agregar `PreviewRequest` (plantilla asunto/cuerpo, lista de destinatarios con sus variables) y `PreviewResponse` (lista de renders por destinatario); `extra='forbid'`.
- [x] 2.3 Agregar `EncolarLoteRequest` (materia_id, asunto, cuerpo, destinatarios + variables) y `EncolarLoteResponse` (lote_id, cantidad); `extra='forbid'`.
- [x] 2.4 Agregar `AprobarLoteRequest` / `AprobarItemRequest` y `ColaQuery` (filtros `lote_id`, `estado`); `extra='forbid'`.

## 3. Lógica pura — máquina de estados y render

- [x] 3.1 RED: tests de `transicion_valida(actual, destino)` para cada transición VÁLIDA (`Pendiente→Enviando`, `Pendiente→Cancelado`, `Enviando→Enviado`, `Enviando→Error`). GREEN: implementar la función pura en `backend/app/services/comunicacion_estado.py` (sin DB). TRIANGULATE: cada transición inválida (`Enviado→Pendiente`, `Enviando→Cancelado`, `Cancelado→Enviando`, etc.) retorna False. REFACTOR: tabla de transiciones.
- [x] 3.2 RED: test de `render_plantilla(plantilla, variables)` — `{{nombre_alumno}}` → "Ana". GREEN: implementar función pura. TRIANGULATE: variable ausente queda literal; múltiples ocurrencias; sin variables. REFACTOR.

## 4. Repository

- [x] 4.1 Safety Net: correr tests de `BaseRepository`. RED: test `create_many(comunicaciones)` persiste N filas con tenant scope. GREEN: crear `backend/app/repositories/comunicacion_repository.py` extendiendo `BaseRepository`. TRIANGULATE: filas de otro tenant no se devuelven. REFACTOR.
- [x] 4.2 RED: test `list_cola(tenant_id, lote_id=None, estado=None)` filtra por tenant y por filtros opcionales. GREEN. TRIANGULATE: filtro por `estado=Pendiente`; filtro por `lote_id`; aislamiento de tenant. REFACTOR.
- [x] 4.3 RED: test `aplicar_transicion_condicional(id, tenant_id, desde, hacia)` — UPDATE condicionado a `estado == desde` (gana la carrera cancelación/worker). GREEN. TRIANGULATE: si el estado ya cambió, no actualiza y retorna 0 filas afectadas. REFACTOR.
- [x] 4.4 RED: test `marcar_aprobado(ids|lote_id, aprobado_por, tenant_id)` setea `aprobado_at`/`aprobado_por` solo en `Pendiente`. GREEN. TRIANGULATE: por lote completo vs. item individual; no toca no-Pendientes. REFACTOR.

## 5. Servicio de comunicaciones

- [x] 5.1 RED: test `preview(request, tenant_id)` retorna renders y NO persiste ninguna `Comunicacion`. GREEN: crear `backend/app/services/comunicacion_service.py` usando `render_plantilla`. TRIANGULATE: variable ausente; verificar que la tabla `comunicacion` queda vacía. REFACTOR.
- [x] 5.2 RED: test `encolar_lote(request, actor_id, tenant_id, db)` crea una `Comunicacion` por destinatario en `Pendiente` con un único `lote_id`, `enviado_por` = actor del JWT, `destinatario` cifrado con `CryptoService`. GREEN. TRIANGULATE: 3 destinatarios → 3 filas mismo `lote_id`; verificar que el valor en DB es ciphertext (no el email plano). REFACTOR.
- [x] 5.3 RED: test que `encolar_lote` emite un único `AuditLog` con acción `COMUNICACION_ENVIAR`. GREEN: integrar helper de auditoría (C-05). TRIANGULATE: un solo evento por lote, no uno por destinatario. REFACTOR.
- [x] 5.4 RED: test `aprobar(lote_id|item_id, aprobador_id, tenant_id, db)` setea aprobación; `aprobado_por` proviene del JWT. GREEN. TRIANGULATE: lote completo vs. destinatario individual. REFACTOR.
- [x] 5.5 RED: test `cancelar(lote_id|item_id, tenant_id, db)` pasa `Pendiente → Cancelado`; rechaza cancelar desde `Enviando`/`Enviado`/`Error`. GREEN: usar `transicion_valida` + transición condicional. TRIANGULATE: cancelar Pendiente OK; cancelar Enviando lanza error de dominio. REFACTOR.
- [x] 5.6 RED: test `listar_cola(query, tenant_id, db)` descifra `destinatario` solo en la respuesta y respeta filtros. GREEN. TRIANGULATE: filtro por estado/lote; aislamiento de tenant. REFACTOR.

## 6. Worker asíncrono

- [x] 6.1 RED: test `procesar_pendientes(db, canal)` con canal mock que retorna éxito → comunicación pasa `Pendiente → Enviando → Enviado` y setea `enviado_at`. GREEN: crear `backend/app/workers/__init__.py` y `backend/app/workers/comunicacion_worker.py` con interfaz `canal.enviar(destinatario, asunto, cuerpo)`. TRIANGULATE: transiciona a `Enviando` antes de invocar el canal. REFACTOR.
- [x] 6.2 RED: test con canal mock que retorna fallo → comunicación pasa a `Error`. GREEN. TRIANGULATE: canal que lanza excepción → se captura, pasa a `Error`, NO propaga. REFACTOR.
- [x] 6.3 RED: test de aislamiento de fallos — en un lote, una falla y las demás tienen éxito → la fallida en `Error`, el resto en `Enviado`, el loop no se detiene. GREEN. TRIANGULATE: orden de fallos distinto. REFACTOR.
- [x] 6.4 RED: test de aprobación — tenant exige aprobación: solo despacha `Pendiente` con `aprobado_at`; deja las no aprobadas en `Pendiente`. GREEN. TRIANGULATE: tenant sin aprobación despacha todos; config ausente → fail-safe (no despacha sin aprobar). REFACTOR.
- [x] 6.5 RED: test de carrera — comunicación cancelada antes de tomarla: el worker no la transiciona a `Enviando` ni invoca el canal (transición condicional `WHERE estado = Pendiente`). GREEN. TRIANGULATE: el resto del lote sí se procesa. REFACTOR.
- [x] 6.6 Verificar que `comunicacion_worker.py` y `comunicacion_service.py` quedan ≤500 LOC; extraer helpers si excede.

## 7. Audit codes y RBAC

- [x] 7.1 Agregar `COMUNICACION_ENVIAR` al enum `AccionAuditoria` en `backend/app/services/audit_codes.py` (si no existe).
- [x] 7.2 Agregar permisos `comunicacion:enviar` y `comunicacion:aprobar` al catálogo RBAC (`backend/app/services/rbac_seed.py`).
- [x] 7.3 Asignar `comunicacion:enviar` a PROFESOR, COORDINADOR, ADMIN; `comunicacion:aprobar` a COORDINADOR, ADMIN.

## 8. Router y endpoints

- [x] 8.1 Crear `backend/app/api/v1/routers/comunicaciones.py` con `APIRouter(prefix="/comunicaciones", tags=["comunicaciones"])`; handlers `async`, sin lógica de negocio, todo vía `Depends()`.
- [x] 8.2 `POST /preview` — `require_permission("comunicacion:enviar")`; identidad desde `get_current_user`; llama `preview`; `response_model=PreviewResponse`.
- [x] 8.3 `POST /` (encolar lote) — `require_permission("comunicacion:enviar")`; llama `encolar_lote`; `response_model=EncolarLoteResponse`.
- [x] 8.4 `GET /` (cola) — query `lote_id`/`estado`; `require_permission("comunicacion:enviar")` o `comunicacion:aprobar`; `response_model=list[ComunicacionRead]`.
- [x] 8.5 `POST /aprobar` — body lote o item; `require_permission("comunicacion:aprobar")`; llama `aprobar`.
- [x] 8.6 `POST /cancelar` — body lote o item; `require_permission("comunicacion:aprobar")`; llama `cancelar`.
- [x] 8.7 Registrar el router en `backend/app/main.py`.

## 9. Tests de integración (endpoints + RBAC + tenant)

- [x] 9.1 RED/GREEN: `POST /preview` renderiza variables y no crea filas; sin permiso → 403.
- [x] 9.2 RED/GREEN: `POST /` encola lote, mismo `lote_id`, `destinatario` cifrado en DB, `enviado_por` del JWT, emite `COMUNICACION_ENVIAR`; sin permiso → 403.
- [x] 9.3 RED/GREEN: `GET /` filtra por `lote_id` y `estado`; descifra `destinatario` en la respuesta; sin permiso → 403.
- [x] 9.4 RED/GREEN: `POST /aprobar` aprueba lote y item individual; `aprobado_por` del JWT; sin `comunicacion:aprobar` → 403.
- [x] 9.5 RED/GREEN: `POST /cancelar` cancela `Pendiente`; rechaza cancelar `Enviando`; sin permiso → 403.
- [x] 9.6 RED/GREEN: aislamiento multi-tenant — un `lote_id` de otro tenant retorna 404/vacío en todos los endpoints.
- [x] 9.7 RED/GREEN: flujo E2E FL-04 — encolar → aprobar parte del lote → worker (canal mock) → aprobados `Enviado`, no aprobados `Pendiente`, cancelados `Cancelado`.
- [x] 9.8 Verificar cobertura ≥80% líneas y ≥90% en reglas de negocio (máquina de estados, aprobación, worker).
