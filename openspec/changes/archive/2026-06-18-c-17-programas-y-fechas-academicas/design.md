# Design — C-17 programas-y-fechas-academicas

Implementa E15 (FechaAcademica), E16 (ProgramaMateria), F5.3 (gestión de programas) y F5.4 (gestión de fechas + fragmento LMS). Stack: FastAPI + SQLAlchemy 2.0 async + PostgreSQL, Routers → Services → Repositories → Models, multi-tenant row-level, RBAC `modulo:accion` fail-closed.

## D1 — ProgramaMateria: clave natural y reemplazo

`ProgramaMateria` (E16) representa el programa oficial de una materia para una combinación **materia × carrera × cohorte**. Esa terna es la clave natural del documento.

- **Unicidad**: índice único parcial `uq_programa_materia_combo` sobre `(tenant_id, materia_id, carrera_id, cohorte_id) WHERE deleted_at IS NULL`. Garantiza un único programa vivo por combinación, sin romper el soft-delete (filas borradas no colisionan con un alta posterior).
- **Reemplazo (F5.3 "subir y asociar")**: el alta es idempotente sobre la combinación. Si ya existe un programa vivo para la terna, el service hace **soft-delete del anterior** y crea uno nuevo (append-only / auditable). Así "reemplazar" deja rastro histórico en lugar de mutar la fila. No se versiona con un campo `version` explícito en este change: el historial queda implícito en las filas soft-deleted ordenadas por `created_at`.
- **`referencia_archivo`**: `String` opaco. Solo almacena la ruta/URL que entrega el servicio de almacenamiento externo. **Este change NO sube binarios** ni valida el archivo; trata la referencia como dato de texto. Cualquier integración de storage es responsabilidad de otro change.
- **`titulo`**: texto descriptivo obligatorio (F5.3 "con un título descriptivo").

## D2 — FechaAcademica: clave natural y tipo

`FechaAcademica` (E15) representa una instancia evaluativa calendarizada por **materia × cohorte**.

- **Clave natural**: `(tenant_id, materia_id, cohorte_id, tipo, numero)`. No puede haber dos "2º Parcial" para la misma materia × cohorte. Índice único parcial `uq_fecha_academica_combo` con `WHERE deleted_at IS NULL`.
- **`tipo`**: enum `TipoFechaAcademica` = `Parcial | TP | Coloquio | Recuperatorio`. Se modela como `StrEnum` en Python → columna `VARCHAR(20)` + `CheckConstraint` (NO PG ENUM type), consistente con `EstadoTarea` (C-16) y `EstadoGuardia` (C-13). Evita migraciones de ALTER TYPE.
- **`numero`**: entero ≥ 1 (1º parcial, 2º parcial, etc.). CheckConstraint `numero >= 1`.
- **`fecha`**: `DATE` (no timestamp — es una fecha de calendario, no un instante).
- **`periodo`**: texto (ej: "2026-1") para el cuatrimestre/año. Opcional.
- **`titulo`**: texto descriptivo obligatorio.

## D3 — Generación de fragmento LMS (F5.4)

Endpoint read-only `GET /api/v1/fechas-academicas/fragmento-lms?materia_id=&cohorte_id=`.

- Lee las `FechaAcademica` vivas de la combinación materia × cohorte, ordenadas por `fecha` ascendente.
- Devuelve un fragmento **formateado** (texto/HTML estructurado) listo para pegar en el aula virtual del LMS. El formato lo arma el `FechaAcademicaService` a partir de las filas: una línea/ítem por instancia con `tipo`, `numero`, `titulo` y `fecha`.
- **No hay llamada a Moodle ni a ninguna API de LMS en este change** — solo se construye el string. La publicación efectiva queda fuera de alcance.
- Respuesta: `{ "materia_id", "cohorte_id", "formato": "html"|"texto", "contenido": "<string>" }`.

## D4 — Guard `estructura:gestionar`

Ambos routers exigen el permiso `estructura:gestionar` vía `require_permission("estructura:gestionar")` en cada endpoint (fail-closed: sin permiso → 403).

- **Roles que lo reciben**: COORDINADOR y ADMIN (F5.3/F5.4 "Quién: ADMIN, COORDINADOR"), alcance `global`.
- El permiso se siembra por tenant en la migración con `ON CONFLICT DO NOTHING` (idempotente), mismo patrón que `tareas:gestionar` en 014.
- Si C-06 ya introdujo `estructura:gestionar`, el seed es no-op por el `ON CONFLICT`; este change no rompe nada.

## D5 — Identidad y tenant desde la sesión

`tenant_id` SIEMPRE se deriva del JWT verificado (nunca del body/URL). Los schemas de entrada NO incluyen `tenant_id`. Los repositories filtran por `tenant_id` de la sesión por defecto y excluyen `deleted_at IS NOT NULL`.

## D6 — Interacción de FKs con el scoping de tenant

`materia_id`, `carrera_id` y `cohorte_id` son FKs `ondelete=RESTRICT` hacia `materias`, `carreras`, `cohortes` (C-06), que ya son tablas tenant-scoped. La integridad referencial de PostgreSQL NO conoce el tenant, por lo que el **service valida** que las entidades referenciadas pertenezcan al `tenant_id` de la sesión antes de insertar (si la materia/carrera/cohorte es de otro tenant → 404/422). Esto evita "fugas" cruzadas que un FK por sí solo no impide. Una referencia a otro tenant se trata como inexistente.

## D7 — Soft delete

`FechaAcademica` se elimina con soft-delete (`deleted_at`), nunca hard delete (regla dura 13). El reemplazo de `ProgramaMateria` (D1) también es soft-delete del anterior. Los índices únicos son parciales `WHERE deleted_at IS NULL` para permitir re-alta de una combinación previamente borrada.

## D8 — Estructura de archivos (≤500 LOC/archivo)

Dos capabilities → archivos separados por entidad: modelos, repositories, schemas, services y routers independientes para `programa_materia` y `fecha_academica`. Una sola migración (015) crea ambas tablas y siembra el permiso compartido.
