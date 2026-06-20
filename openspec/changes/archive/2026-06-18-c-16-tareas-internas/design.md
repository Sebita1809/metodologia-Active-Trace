## Context

C-16 implementa la Épica 8 (Workflow de Tareas Internas) descrita en `knowledge-base/06_funcionalidades.md` (F8.1–F8.3), `knowledge-base/04_modelo_de_datos.md` §E12 y el flujo FL-05 de `knowledge-base/07_flujos_principales.md`.

Estado actual: el repo ya tiene la base multi-tenant (C-02 `BaseTenantModel`: `id`, `tenant_id`, `created_at`, `updated_at`, `deleted_at`), RBAC `modulo:accion` (C-04) con `require_permission`, `BaseRepository` con filtro automático por tenant y `deleted_at IS NULL`, y el módulo de equipos/asignaciones (C-07) del que C-16 depende. La última migración aplicada es `013`; C-16 usa `014`.

Restricciones del proyecto: snake_case en Python, Pydantic v2 con `extra='forbid'`, queries SOLO en repositories, soft delete siempre, identidad SIEMPRE desde la sesión JWT, ≤500 LOC por archivo, una migración por cambio de schema. FL-05 advierte que es un módulo de **alto uso** (cientos de tareas en simultáneo): el diseño debe priorizar índices y consultas eficientes.

Nota de consistencia: FL-05 menciona estados narrativos ("Abierta", "completada"); la fuente autoritativa para el modelo de datos es §E12, que fija el enum **Pendiente | En progreso | Resuelta | Cancelada**. Se sigue §E12.

## Goals / Non-Goals

**Goals:**
- Modelar `Tarea` y `ComentarioTarea` según §E12 con aislamiento por tenant.
- Permitir alta con auto-asignación y delegación a otro docente, con trazabilidad de `asignado_por` y `asignado_a`.
- Controlar las transiciones de estado válidas (máquina de estados explícita).
- Soportar la vista "mis tareas" (F8.1) y la administración global con filtros (F8.3).
- Hilo de comentarios cronológico por tarea (F8.2).
- Endpoints `/api/v1/tareas/*` con guard `tareas:gestionar`, fail-closed.
- Índices compuestos para el alto volumen de consultas.

**Non-Goals:**
- Notificaciones push / emails al asignar o cambiar estado (se integra con C-comunicación, fuera de alcance).
- UI / frontend de tareas (change de frontend aparte).
- Adjuntar archivos/evidencias binarias (sólo texto en comentarios por ahora).
- Resolución del workflow de "elevar a coordinación" como entidad propia: se modela como una delegación normal (reasignación de `asignado_a`).

## Decisions

**D1 — `EstadoTarea` como `StrEnum` (VARCHAR + CHECK), no PG ENUM.**
Coherente con `EstadoGuardia` (C-13) y `EstadoInstanciaEncuentro`. Almacena VARCHAR con `CheckConstraint("estado IN (...)")`. Evita migraciones de tipo PG ENUM (que requieren `ALTER TYPE` no transaccional) y simplifica agregar estados futuros. Alternativa descartada: PG ENUM nativo (más rígido para evolucionar).

**D2 — Máquina de transiciones en el Service, no en el modelo.**
Mapa `_TRANSICIONES_VALIDAS: dict[EstadoTarea, set[EstadoTarea]]`:
- `Pendiente → {En progreso, Cancelada}`
- `En progreso → {Resuelta, Cancelada, Pendiente}` (permite devolver a pendiente al reabrir)
- `Resuelta → {En progreso}` (reapertura controlada; no a Cancelada directa)
- `Cancelada → {}` (terminal)
Una transición inválida levanta error de dominio → 409/422. La lógica vive en `TareaService`, nunca en el router ni en el repository. Alternativa descartada: transiciones libres validadas sólo por permisos (no deja trazabilidad de un flujo coherente).

**D3 — Auto-asignación permitida; delegación = cambio de `asignado_a`.**
Al crear, `asignado_por` = usuario de sesión; `asignado_a` puede ser el mismo usuario (auto-asignación) o cualquier miembro del equipo docente. La "delegación" (F8.2) es una operación que actualiza `asignado_a` dejando `asignado_por` original intacto y registrando el cambio (timestamp en `updated_at`; el hilo de comentarios documenta el motivo). No se borra ni se pierde el historial — soft delete y append-only mantienen la trazabilidad. Identidad de `asignado_por` SIEMPRE desde el JWT, nunca del body.

**D4 — `contexto_id` como UUID opaco nullable, sin FK formal.**
Es una referencia opcional polimórfica a otra entidad del dominio (aviso, encuentro, entrega…). No se modela como FK porque apunta a tablas heterogéneas. Se valida sólo formato UUID; la resolución del contexto es responsabilidad del consumidor. Alternativa descartada: tabla de relación polimórfica (sobre-ingeniería para el alcance actual).

**D5 — `materia_id` nullable.**
§E12 lo permite: una tarea de nivel institucional (no ligada a una materia) tiene `materia_id = NULL`. FK con `ondelete="RESTRICT"` cuando está presente.

**D6 — Filtros de F8.3 en el repository con query compuesta tenant-scoped.**
`TareaRepository.listar(filtros)` arma un `select(Tarea)` aplicando siempre el filtro de tenant del `BaseRepository` más los filtros opcionales (`estado`, `asignado_a`, `asignado_por`, `materia_id`). "Mis tareas" (F8.1) es el mismo método con `asignado_a` = usuario de sesión. Paginación con `limit`/`offset` para el alto volumen.

**D7 — Comentarios append-only ordenados por `creado_at`.**
`ComentarioTarea` lleva `creado_at` server-side (como `Guardia.creada_at`). El hilo se devuelve ordenado ascendente. `autor_id` SIEMPRE del JWT. No se editan ni borran (soft delete disponible vía base por consistencia, pero la UX es append-only).

**D8 — Guard único `tareas:gestionar`.**
Todos los endpoints declaran `require_permission("tareas:gestionar")`. El scoping fino (un docente sólo ve/gestiona lo propio salvo COORDINADOR/ADMIN que ven todo el tenant) se resuelve en el Service según los roles de la sesión, fail-closed. Seed: PROFESOR, COORDINADOR, ADMIN; TUTOR sobre lo propio.

## Risks / Trade-offs

- **[Alto volumen de consultas degrada la lista global]** → Índices compuestos `ix_tarea_tenant_asignado_a (tenant_id, asignado_a)`, `ix_tarea_tenant_estado (tenant_id, estado)`, `ix_tarea_tenant_asignado_por (tenant_id, asignado_por)`; paginación obligatoria en F8.3; `deleted_at` filtrado por defecto.
- **[`contexto_id` sin FK puede quedar colgado si la entidad referida se borra]** → Es soft delete en todo el dominio (append-only), así que la entidad nunca desaparece físicamente; el consumidor maneja referencias a entidades soft-deleted. Documentado como referencia "best-effort".
- **[Transiciones de estado mal validadas dejan tareas en estado incoherente]** → Máquina de estados explícita y centralizada (D2) con tests de cobertura ≥90% sobre cada arista válida e inválida.
- **[Delegación a un usuario fuera del equipo docente]** → El Service valida pertenencia vía asignaciones (C-07) antes de reasignar; sin pertenencia → 403/422.
- **[Fuga cross-tenant en filtros de F8.3]** → Todo query nace del `BaseRepository` tenant-scoped; tests de aislamiento explícitos (tarea de tenant A nunca aparece para sesión de tenant B).
