## Context

C-11 dejó disponible el análisis de atrasados (`GET /api/v1/analisis/atrasados`). C-12 es la última pieza del camino crítico: comunicar. Introduce la entidad `Comunicacion` (E21), una máquina de estados con cola, un worker asíncrono independiente que despacha al canal externo, y el flujo de aprobación administrativa.

Tres restricciones del dominio condicionan el diseño:

1. **Preview obligatorio (RN-16)**: nada se encola sin que el usuario haya visto el render con variables sustituidas. El preview no persiste.
2. **Aprobación configurable por tenant (RN-17)**: si el tenant exige aprobación, los mensajes quedan en `Pendiente` hasta que un COORDINADOR/ADMIN apruebe; el worker solo procesa aprobados.
3. **Aislamiento del worker (§5.2)**: el worker vive en `workers/`, es módulo independiente y sus fallos no rompen el flujo HTTP. Un error de despacho transiciona el mensaje a `Error`, no propaga excepción al request.

Restricciones transversales del proyecto: identidad desde JWT, multi-tenancy row-level, soft delete, `destinatario` (email = PII) cifrado AES-256 en reposo, ≤500 LOC por archivo, una migración por cambio de schema, Strict TDD.

## Goals / Non-Goals

**Goals:**
- Modelo `Comunicacion` (E21) con máquina de estados `Pendiente → Enviando → Enviado | Error | Cancelado` y agrupación por `lote_id`
- Preview con sustitución de variables (RN-16) sin persistencia
- Encolado de lote en estado `Pendiente`; auditoría `COMUNICACION_ENVIAR` al confirmar
- Aprobación/cancelación de lote completo o por destinatario individual (RN-17)
- Worker asíncrono que consume `Pendiente`, transiciona a `Enviando`, despacha y resuelve `Enviado`/`Error`
- Permisos `comunicacion:enviar` y `comunicacion:aprobar`; fail-closed
- `destinatario` cifrado AES-256; descifrado solo en capa de presentación

**Non-Goals:**
- Integración real con SMTP/N8N de producción — el canal de envío se abstrae detrás de una interfaz; la implementación concreta del canal real queda fuera del alcance de TDD (se mockea)
- Editor visual de plantillas (queda para el frontend, C-22+)
- Reintentos automáticos con backoff de mensajes en `Error` (se deja `Error` como estado terminal en esta versión)
- Programación de envíos diferidos / scheduling
- Webhooks de tracking de apertura/click

## Decisions

### D-01: Máquina de estados en el service, no en el modelo

**Decisión**: una función pura `_transicion_valida(estado_actual, estado_destino) -> bool` y un método de service `_aplicar_transicion(comunicacion, destino)` concentran la lógica de RN-15. El modelo solo guarda el campo `estado` como Enum.

**Razón**: las transiciones son reglas de negocio, no estructura de datos. Una función pura es trivial de testear exhaustivamente (toda transición válida e inválida) sin DB. Alternativa rechazada: triggers en PostgreSQL → opacos, difíciles de testear y de versionar.

**Transiciones válidas (RN-15)**:
- `Pendiente → Enviando` (worker toma el mensaje aprobado)
- `Pendiente → Cancelado` (solo `Pendiente` puede cancelarse)
- `Enviando → Enviado` (despacho OK)
- `Enviando → Error` (despacho falló)
- Cualquier otra → inválida (lanza error de dominio)

### D-02: Aprobación modelada como gate sobre `Pendiente`, no como estado separado

**Decisión**: no se agrega un estado `Aprobado`. Se agrega una columna `aprobado_at` (timestamp, nullable) y `aprobado_por` (UUID, nullable). El worker solo levanta mensajes `Pendiente` con `aprobado_at IS NOT NULL` cuando el tenant exige aprobación. Si el tenant no exige aprobación, el worker levanta cualquier `Pendiente`.

**Razón**: la aprobación es ortogonal al ciclo de vida de envío (RN-15 define 5 estados, no 6). Modelarla como flag evita inflar la máquina de estados. Cancelar un mensaje aprobado-pero-no-enviado sigue siendo `Pendiente → Cancelado`, sin transición extra.

**Configuración por tenant**: la bandera `requiere_aprobacion_comunicaciones` se lee de la config del tenant. Para esta versión se asume un atributo en el tenant o un default seguro: **si no está definido, se exige aprobación** (fail-safe hacia el flujo más controlado).

### D-03: `destinatario` cifrado con `CryptoService` en la capa de service

**Decisión**: el service cifra `destinatario` con `CryptoService` (AES-256-GCM, C-02) antes de pasar el dato al repository, y descifra solo al construir el schema de respuesta (`ComunicacionRead`). El repository y el modelo nunca ven el email en claro... el campo en DB es ciphertext.

**Razón**: regla dura 12 (PII en reposo AES-256). El cifrado en service mantiene el repository agnóstico de cripto. El preview (que muestra el email al usuario autorizado) descifra solo en memoria; no persiste.

### D-04: Worker como proceso/loop independiente con interfaz de canal inyectable

**Decisión**: `comunicacion_worker.py` expone `procesar_pendientes(db, canal)` donde `canal` implementa `enviar(destinatario, asunto, cuerpo) -> ResultadoEnvio`. El worker: (1) lista mensajes despachables, (2) transiciona a `Enviando`, (3) llama `canal.enviar(...)` envuelto en try/except, (4) transiciona a `Enviado`/`Error` según resultado. Una excepción del canal se captura y transiciona a `Error`; nunca se propaga.

**Razón**: la interfaz `canal` permite mockear el envío real en tests (mockear el canal, NUNCA la DB — python-testing-patterns). El aislamiento de fallos cumple §5.2: el worker no debe tumbar el flujo principal. Alternativa rechazada: invocar SMTP directo dentro del service HTTP → acopla el request a un I/O externo lento y frágil.

### D-05: Sustitución de variables como función pura sobre plantilla

**Decisión**: `render_plantilla(plantilla: str, variables: dict) -> str` reemplaza tokens (p. ej. `{{nombre_alumno}}`, `{{materia}}`) por sus valores. Función pura, sin DB, sin side effects.

**Razón**: el preview (RN-16) y el render del cuerpo persistido comparten esta función. Testeable con casos: token presente, token ausente (se deja literal o se documenta el comportamiento), múltiples ocurrencias. El service arma el `variables` dict desde el contexto (alumno, materia) y lo pasa a la función pura.

### D-06: Encolado de lote atómico con `lote_id` compartido

**Decisión**: `encolar_lote(...)` genera un único `lote_id` (UUID) y crea N `Comunicacion` en estado `Pendiente`, una por destinatario, todas con el mismo `lote_id`, en una sola transacción. Emite un único evento de auditoría `COMUNICACION_ENVIAR` por la acción de encolado (no uno por destinatario).

**Razón**: el `lote_id` agrupa el envío masivo para aprobación/cancelación/tracking por lote (F3.2, F3.3). La atomicidad evita lotes parciales si falla a mitad. Índice `(tenant_id, lote_id)` soporta las consultas de cola por lote.

## Risks / Trade-offs

- [Risk] El worker procesa en el mismo proceso que la API en dev (loop disparado manualmente / scheduler simple) → **Mitigation**: la interfaz `procesar_pendientes(db, canal)` es agnóstica del disparador; en prod se ejecuta como proceso separado. Tests llaman la función directamente.
- [Risk] `Error` es terminal: un fallo transitorio de SMTP deja el mensaje muerto → **Mitigation**: aceptado para esta versión; los reintentos con backoff quedan como Non-Goal explícito. El estado `Error` queda visible en el tracking para re-encolar manualmente desde el frontend más adelante.
- [Risk] Carrera entre worker tomando `Pendiente → Enviando` y un usuario cancelando `Pendiente → Cancelado` → **Mitigation**: la transición a `Enviando` se hace con bloqueo/condición sobre el estado actual (`WHERE estado = 'Pendiente'` en el UPDATE); si la cancelación ganó, la fila ya no está `Pendiente` y el worker la salta.
- [Risk] Tenant sin `requiere_aprobacion_comunicaciones` definido → **Mitigation**: D-02 hace fail-safe a "exige aprobación"; ningún mensaje se despacha sin gate explícito si la config es ambigua.
- [Risk] Descifrar `destinatario` en listados grandes tiene costo → **Mitigation**: dataset por lote acotado (alumnos de una asignación); descifrado solo en la capa de presentación, no en queries de filtro.

## Migration Plan

1. Generar una migración Alembic que crea la tabla `comunicacion` con columnas E21 + `BaseMixin` (soft delete, timestamps) + `aprobado_at`/`aprobado_por`, el tipo Enum de estado, e índices `(tenant_id, lote_id)` y `(tenant_id, estado)`.
2. Registrar el modelo en `models/__init__.py` y el router en `main.py`.
3. Agregar permisos `comunicacion:enviar`/`comunicacion:aprobar` y el código de auditoría `COMUNICACION_ENVIAR` al seed/catálogo.
4. **Rollback**: la migración es reversible (`downgrade` dropea tabla y Enum); no hay datos previos que migrar.

## Open Questions

- ¿Dónde vive exactamente la bandera `requiere_aprobacion_comunicaciones` — en el modelo `Tenant` o en una tabla de configuración por tenant? Esta versión la lee con un default fail-safe (exige aprobación); si C-06/tenancy ya expone configuración de tenant, se engancha ahí.
- ¿El canal de envío real es N8N o SMTP directo? No bloquea C-12: la interfaz `canal` lo desacopla; la implementación concreta se decide al integrar el canal de producción.
