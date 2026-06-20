## Context

C-14 implementa la Épica 7 (Evaluaciones y Coloquios) sobre la base ya construida: `Usuario`/`Asignacion` (C-07), `Materia`/`Cohorte` (C-06), `BaseRepository` tenant-scoped (C-02), `require_permission` (C-04) y `get_current_user` (C-03). Governance MEDIO: lógica de dominio con control de cupo, implementable con checkpoints.

El dominio tiene tres entidades (E14: `Evaluacion`, `ReservaEvaluacion`, `ResultadoEvaluacion`) y un núcleo de reglas: control de cupo por día, unicidad de reserva activa, cancelación propia que libera cupo y unicidad de resultado por alumno. Clean Architecture estricta: Routers → Services → Repositories → Models, sin lógica en routers, sin DB en services.

## Goals / Non-Goals

**Goals:**
- Modelar evaluaciones, reservas y resultados con `tenant_id`, soft delete y timestamps.
- Crear convocatorias con `cupo_por_dia` e importar el padrón de candidatos (bulk).
- Reservar turno con control de cupo por día (lleno → 409) y unicidad de reserva activa (duplicada → 409).
- Cancelar la propia reserva (Activa → Cancelada) mientras la evaluación siga Activa, liberando cupo.
- Registrar y consultar la nota final, única por `(evaluacion_id, alumno_id)`.
- Panel de métricas (convocados / instancias activas / reservas activas / notas registradas) y agenda consolidada.
- RBAC fail-closed por verbo: gestionar / ver / reservar.

**Non-Goals:**
- Notificaciones/recordatorios de turnos (cola de comunicaciones es C-09…C-12).
- Publicación de resultados a Moodle vía Web Services (fuera de alcance).
- Asignación automática de turnos o balanceo de cupos entre días.
- Reprogramación masiva de una evaluación (mover todas las reservas a otra fecha).

## Decisions

### D1 — `cupo_por_dia` en `Evaluacion` (no en el modelo KB original)
El modelo KB de `Evaluacion` define `dias_disponibles` (ventana de inscripción) pero NO un campo de cupo, mientras que el scope exige "cupos por día" y "reserva resta cupo / sin cupo rechaza". Se agrega **`cupo_por_dia: int`** a `Evaluacion`: es el dato mínimo necesario para implementar la restricción de cupo. `dias_disponibles` se conserva como ventana temporal; `cupo_por_dia` es el tope concurrente por fecha/turno.
- *Alternativa descartada*: tabla `TurnoEvaluacion` con cupo propio por día. Más flexible (cupos distintos por día) pero sobre-modela el scope actual, que asume un cupo uniforme por día. Si más adelante se requieren cupos heterogéneos, se promueve a tabla sin romper la API.

### D2 — Control de cupo: validación en el Service, conteo en el Repository
La regla "lleno → 409" vive en el `EvaluacionService`: pide al repo `contar_reservas_activas(evaluacion_id, fecha)` y compara contra `cupo_por_dia`. El conteo es una query tenant-scoped en el repository; la decisión (rechazar/crear) es lógica de negocio en el service. El cupo se calcula sobre la **fecha** (día) de `fecha_hora`, no sobre el datetime exacto.
- *Alternativa descartada*: validar cupo con un `CHECK` en DB. Imposible: el cupo es un conteo agregado, no una restricción de fila.

### D3 — Concurrencia: unicidad por índice parcial + manejo de IntegrityError
Dos requests concurrentes podrían pasar el chequeo de cupo a la vez (TOCTOU). Mitigación en dos capas:
1. **Unicidad de reserva activa** vía índice UNIQUE parcial `(evaluacion_id, alumno_id) WHERE estado='Activa'`: garantiza que un alumno nunca tenga dos reservas activas aunque haya carrera. El service captura el `IntegrityError` y responde 409.
2. **Cupo por día**: el conteo + insert se hace dentro de una transacción; ante sobreventa por carrera extrema, el invariante duro lo sostiene la unicidad por alumno (un alumno = una reserva), y el cupo se valida en transacción. Se documenta como riesgo aceptado (ver Risks) — no se usa `SELECT ... FOR UPDATE` de fila de cupo en esta iteración por no existir fila de turno.
- *Alternativa descartada*: lock pesimista sobre una fila de turno. Requeriría la tabla `TurnoEvaluacion` (D1) — fuera de alcance.

### D4 — Estados como VARCHAR + CHECK (enum a nivel app)
`Evaluacion.estado` (`Activa|Cerrada`), `Evaluacion.tipo` (`Parcial|TP|Coloquio|Recuperatorio`) y `ReservaEvaluacion.estado` (`Activa|Cancelada`) se modelan como `VARCHAR` con constraint `CHECK`, con un `Enum` de Python para tipado. Evita migraciones de tipo ENUM de PostgreSQL al agregar valores futuros. `nota_final` es texto libre (numérica o cualitativa), sin CHECK.

### D5 — Cálculo de métricas: función/queries agregadas, no en memoria
Las métricas (F7.1) y la columna "cupos libres" del listado (F7.4) se calculan con queries agregadas tenant-scoped en el repository (`count` por estado/evaluación), no cargando filas a memoria. `cupos_libres(evaluacion, fecha) = cupo_por_dia - count(reservas Activas en fecha)`. La lógica de derivación (resta, agregación por evaluación) se prueba con tests del service sobre datos reales.

### D6 — Cancelación: transición de estado, no delete
Cancelar una reserva es `estado: Activa → Cancelada`, no soft delete ni hard delete. Así la reserva cancelada queda en la traza y libera cupo (el conteo solo cuenta `Activa`). El soft delete (`deleted_at`) se reserva para baja administrativa de la fila. La regla "solo mientras la evaluación siga Activa" se valida en el service; si la evaluación está `Cerrada` → error de dominio.

### D7 — Identidad y propiedad de la reserva desde el JWT
`POST /reservas` y `DELETE /reservas/{rid}` derivan el `alumno_id` del `get_current_user` (JWT), nunca del body/URL. Al cancelar, el service verifica que la reserva pertenece al `current_user` (ALUMNO propio); si no, 403. COORDINADOR/ADMIN no usan estos endpoints de reserva (usan agenda/gestión).

### D8 — RBAC: tres permisos por verbo, fail-closed
- `coloquios:gestionar` (COORDINADOR/ADMIN): crear convocatoria, importar padrón, registrar resultados.
- `coloquios:ver` (COORDINADOR/ADMIN/PROFESOR): listado, métricas, agenda, registro académico.
- `coloquios:reservar` (ALUMNO): reservar y cancelar la propia reserva.
Cada endpoint declara `require_permission(...)`. Sin permiso explícito → 403.

### D9 — Repositories tenant-scoped por defecto
Los tres repos extienden `BaseRepository`; todo query filtra por `tenant_id` del JWT por defecto. Importación de padrón, agenda y métricas son transversales **dentro del tenant** (no cross-tenant): siguen filtrando por `tenant_id`.

## Risks / Trade-offs

- **Sobreventa de cupo por carrera concurrente (TOCTOU)** → Mitigación: conteo + insert en transacción; la unicidad por alumno (índice parcial) impide duplicados; se acepta una ventana mínima de sobreventa de cupo bajo concurrencia extrema, a cerrar con `TurnoEvaluacion` + lock si el negocio lo exige. Test de cupo lleno → 409 cubre el caso secuencial.
- **Segunda reserva activa del mismo alumno** → Mitigación: índice UNIQUE parcial `(evaluacion_id, alumno_id) WHERE estado='Activa'`; el service captura `IntegrityError` → 409.
- **Importación de padrón con `alumno_id`s inexistentes o de otro tenant** → Mitigación: validar que cada `alumno_id` exista y pertenezca al tenant antes del bulk; rechazar el lote inválido.
- **Registro de resultado duplicado** → Mitigación: UNIQUE `(evaluacion_id, alumno_id)` en `resultado_evaluacion`; segundo registro → error/409.
- **Cancelar sobre evaluación Cerrada** → Mitigación: el service valida `evaluacion.estado == 'Activa'` antes de cancelar; test explícito.
- **Archivo de service supera 500 LOC** → Mitigación: separar `evaluacion_service.py`, `reserva_service.py`, `resultado_service.py` y helpers de métricas si excede.

## Migration Plan

1. Una migración Alembic (`012_evaluaciones_coloquios.py`) crea `evaluacion`, `reserva_evaluacion`, `resultado_evaluacion` con FKs, `deleted_at`, timestamps e índices:
   - `(tenant_id, materia_id)` en `evaluacion`.
   - `(tenant_id, evaluacion_id)` en `reserva_evaluacion` y `resultado_evaluacion`.
   - UNIQUE `(evaluacion_id, alumno_id)` en `resultado_evaluacion`.
   - UNIQUE parcial `(evaluacion_id, alumno_id) WHERE estado='Activa'` en `reserva_evaluacion`.
2. Alta de `coloquios:gestionar`, `coloquios:ver`, `coloquios:reservar` en el seed/catálogo de permisos RBAC.
3. Rollback: `downgrade` elimina las tres tablas (sin datos productivos previos).

## Open Questions

- ¿`cupo_por_dia` es uniforme por día o puede variar por fecha/turno? Se asume uniforme (D1); si varía, promover a `TurnoEvaluacion`.
- ¿La sobreventa por concurrencia extrema es aceptable o requiere lock pesimista desde el día 1? Se asume aceptable con la mitigación de D3 hasta confirmación.
- ¿El padrón importado HABILITA a reservar (lista cerrada) o es informativo? Se asume que la reserva no exige estar en el padrón en esta iteración; confirmar con coordinación.
