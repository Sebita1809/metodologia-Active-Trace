## Context

C-13 implementa la Épica 6 (Encuentros y Guardias) sobre la base ya construida: `Asignacion`/`Usuario` (C-07), `Materia`/`Carrera`/`Cohorte` (C-06), `BaseRepository` tenant-scoped (C-02), `require_permission` (C-04) y `get_current_user` (C-03). Governance MEDIO: lógica de dominio con generación automática de instancias, implementable con checkpoints.

El dominio tiene tres entidades (E9 `SlotEncuentro`, E10 `InstanciaEncuentro`, E11 `Guardia`) y dos reglas centrales: RN-13 (dos modos de creación excluyentes) y RN-14 (independencia de estado entre instancias). Clean Architecture estricta: Routers → Services → Repositories → Models, sin lógica en routers, sin DB en services.

## Goals / Non-Goals

**Goals:**
- Modelar slots, instancias y guardias con `tenant_id`, soft delete y timestamps.
- Generación automática de N `InstanciaEncuentro` a partir de un slot recurrente (RN-13.1).
- Creación de encuentro único sin slot (RN-13.2).
- Edición de instancia que NO afecta slot ni otras instancias (RN-14).
- Generar un fragmento HTML (calendario + grabaciones) para el aula virtual.
- Registro/consulta/export de guardias con RBAC fail-closed.

**Non-Goals:**
- Integración con Moodle Web Services para publicar el HTML automáticamente (el endpoint solo devuelve el fragmento; el push lo hará otro change).
- Notificaciones/recordatorios de encuentros (cola de comunicaciones es C-09…C-12).
- Edición masiva de instancias de un slot (regenerar serie) — fuera de alcance en esta iteración.
- Conflictos de horario / detección de solapamientos entre slots.

## Decisions

### D1 — Modo de creación: validación en el Service, no en el modelo
RN-13 exige que recurrente y único sean **excluyentes**. La validación (`cant_semanas > 0` XOR `fecha_unica is not None`) vive en el `EncuentroService`, no en el schema Pydantic, porque cruza dos campos y dispara generación de filas. Pydantic valida formato; el service valida la regla de negocio y lanza error de dominio si ambos modos o ninguno vienen seteados.
- *Alternativa descartada*: un validator de Pydantic. Mantiene formato pero no debería decidir cuántas instancias generar; mezcla validación con orquestación.

### D2 — Generación de instancias: cálculo de fechas en función pura
La generación de las N fechas (a partir de `dia_semana` + `fecha_inicio` + `cant_semanas`) es una **función pura** `generar_fechas_recurrencia(dia_semana, fecha_inicio, cant_semanas) -> list[date]`, sin side effects, fácil de testear (TRIANGULATE con `cant_semanas=4` → 4 fechas con paso de 7 días alineadas al día de semana). El service la usa para crear las filas; el repository persiste en bulk.
- *Alternativa descartada*: generar fechas dentro del repository. Acopla cálculo a persistencia y dificulta el test sin DB.

### D3 — Encuentro único: `slot_id = NULL`
El encuentro único crea una `InstanciaEncuentro` con `slot_id` nullable. Así una sola tabla de instancias cubre ambos orígenes y RN-14 (independencia) es trivial: las instancias únicas nunca tienen serie.
- *Alternativa descartada*: tabla separada para únicos. Duplica modelo y queries del calendario.

### D4 — Estados como VARCHAR + CHECK (enum a nivel app)
Estados (`Programado|Realizado|Cancelado`, `Pendiente|Realizada|Cancelada`) y `dia_semana` se modelan como `VARCHAR` con constraint `CHECK`, y un `Enum` de Python para tipado. Evita migraciones de tipo ENUM de PostgreSQL al agregar valores futuros.

### D5 — HTML como fragmento generado en el service, no template Moodle
`GET /encuentros/html?asignacion_id=X` devuelve un fragmento HTML construido por una función pura `render_encuentros_html(instancias) -> str` (calendario + links a `video_url`/`meet_url`). Sin motor de templates externo; string building testeable por estructura.

### D6 — RBAC: un permiso para encuentros, reglas explícitas para guardias
- `encuentros:gestionar` cubre slots e instancias. PROFESOR queda acotado a su asignación (el service verifica que `asignacion.profesor_id == current_user.id`); COORDINADOR/ADMIN sin esa restricción.
- Guardias: el **registro** (`POST /guardias`) lo hace TUTOR; **consulta/export** (`GET /guardias`) COORDINADOR/ADMIN. Se modela con `require_permission` distinto por verbo. Fail-closed.

### D7 — Repositories tenant-scoped por defecto
Los tres repos extienden `BaseRepository`; todo query filtra por `tenant_id` del JWT por defecto. `GET /admin/encuentros` y `GET /guardias` son transversales **dentro del tenant** (no cross-tenant): siguen filtrando por `tenant_id`, solo amplían el conjunto de asignaciones visibles.

## Risks / Trade-offs

- **Generación de muchas instancias con `cant_semanas` grande** → Mitigación: validar un máximo razonable (p. ej. ≤ 52) en el service; insert en bulk en una transacción.
- **Profesor accede a asignación ajena** → Mitigación: el service compara `asignacion_id` contra las asignaciones del `current_user`; COORDINADOR/ADMIN exentos. Fail-closed.
- **RN-14 violada por una edición que toca el slot** → Mitigación: `PATCH /encuentros/{id}` opera SOLO sobre `instancia_encuentro`; test explícito de que slot y otras instancias del mismo slot quedan intactas.
- **`dia_semana` del slot inconsistente con fechas generadas** → Mitigación: la función pura alinea `fecha_inicio` al `dia_semana` indicado; test de borde con `fecha_inicio` que cae otro día.
- **Archivo de service supera 500 LOC** → Mitigación: separar `encuentro_service.py`, `guardia_service.py` y un módulo de helpers puros (`encuentro_recurrence.py`, `encuentro_html.py`).

## Migration Plan

1. Una migración Alembic crea `slot_encuentro`, `instancia_encuentro`, `guardia` con FKs, `deleted_at`, timestamps e índices `(tenant_id, asignacion_id)` (slots, guardias) y `(tenant_id, slot_id)` (instancias).
2. Alta del permiso `encuentros:gestionar` en el seed/catálogo de permisos RBAC.
3. Rollback: `downgrade` elimina las tres tablas (sin datos productivos previos).

## Open Questions

- ¿`cant_semanas` tiene tope de negocio definido? Se asume ≤ 52 hasta confirmación.
- ¿El TUTOR puede registrar guardia para cualquier asignación de su materia/cohorte o solo las propias? Se asume las asociadas a su asignación; confirmar con coordinación.
