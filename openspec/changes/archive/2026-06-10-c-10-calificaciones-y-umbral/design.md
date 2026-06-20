## Context

C-09 provee `EntradaPadron` (alumno por materia × cohorte). C-07 provee `Asignacion` (docente × materia × cohorte). Este change introduce los modelos `Calificacion` y `UmbralMateria`, el pipeline de importación desde el LMS y la configuración del umbral por asignación. Es el last-mile del camino crítico antes de C-11 (análisis de atrasados), que consume directamente las calificaciones persistidas.

Stack: FastAPI + SQLAlchemy async, openpyxl para xlsx, csv stdlib para csv, Argon2/AES ya disponibles en `encryption_util`.

## Goals / Non-Goals

**Goals:**
- Persistir `Calificacion` con campo `aprobado` derivado al momento del import (numérico vs. umbral; textual vs. conjunto aprobatorio).
- Persistir `UmbralMateria` por asignación con `umbral_pct` y `valores_aprobatorios`.
- Endpoint de import xlsx/csv en dos fases (preview → confirm) con selección de actividades.
- Endpoint de preview de finalización (stateless, no persiste).
- Endpoint `PUT` para configurar el umbral por asignación.
- Migración `0007_calificacion_umbral_materia`.
- Audit `CALIFICACIONES_IMPORTAR` por cada confirmación.

**Non-Goals:**
- Cómputo de atrasados ni ranking (→ C-11).
- Exportación de datos de calificaciones (→ C-11).
- UI de importación (→ C-22 frontend).
- Import de padrón de coordinación (F1.4) — queda fuera del scope de este change.

## Decisions

### D-01: `aprobado` se computa y almacena en import, no on-the-fly

**Decisión**: el campo `aprobado` de `Calificacion` se calcula en la capa de servicio al persistir cada fila y se almacena en BD.

**Rationale**: C-11 (atrasados) necesita filtrar `aprobado = false` en queries agregados sobre potencialmente miles de alumnos × actividades. Computar el booleano cada vez requeriría joins con `UmbralMateria` en cada query, lo que es costoso y complejo. Almacenarlo evita ese join y simplifica C-11 a un `WHERE aprobado = false`.

**Trade-off**: si el docente cambia el umbral después de importar, los `aprobado` ya persistidos no se recalculan automáticamente. Se acepta este trade-off: el docente debe re-importar para actualizar. Se documenta en la API.

**Alternativa descartada**: columna generada (computed column en PostgreSQL). Requiere SQL complejo con subconsulta a `umbral_materia`, no portable a SQLAlchemy sin raw DDL.

### D-02: `UmbralMateria` tiene scope de Asignación, no de Materia

**Decisión**: FK a `asignacion_id` (no a `materia_id` sola), con `materia_id` desnormalizado para queries directos.

**Rationale**: RN-04 — el umbral es del docente para esa materia, no de la materia globalmente. Dos docentes en la misma materia pueden tener umbrales distintos. Usar solo `materia_id` mezclaría configuraciones entre docentes.

**Unicidad**: constraint `UNIQUE (tenant_id, asignacion_id)` — un umbral por asignación.

### D-03: Import en dos fases (preview → confirm)

**Decisión**: dos endpoints separados — `POST /api/calificaciones/preview` (parseo, no persiste) y `POST /api/calificaciones/import` (persiste actividades seleccionadas).

**Rationale**: consistente con el patrón ya establecido en C-09 (padrón). El usuario elige qué actividades incluir antes de persistir. El estado de selección viaja en el body del confirm (lista de nombres de actividades a incluir).

**No se guarda estado de sesión** entre preview y confirm: el confirm re-parsea el archivo o recibe los datos del preview en el body. Se opta por re-parsear con lista de actividades seleccionadas como filtro — más simple, evita TTL/session storage.

### D-04: Finalización preview es stateless

**Decisión**: `POST /api/calificaciones/finalizacion-preview` devuelve el análisis cruzado (entregadas sin calificar) sin persistir nada.

**Rationale**: este resultado es efímero y cambia con cada importación. No tiene sentido almacenarlo; el docente lo consulta, exporta (C-11) o descarta.

### D-05: Migración 0007 crea ambas tablas en una sola revisión

**Decisión**: `alembic/versions/0007_calificacion_umbral_materia.py` crea `calificacion` y `umbral_materia` en la misma migración.

**Rationale**: son co-dependientes conceptualmente (el campo `aprobado` necesita el umbral para derivarse). Una sola migración reduce el número de revisiones Alembic y mantiene la convención "una migración por cambio de schema" del proyecto (son parte del mismo cambio C-10).

## Risks / Trade-offs

- **`aprobado` desactualizado tras cambio de umbral** → Mitigation: el endpoint `PUT /umbral` documenta explícitamente que los registros anteriores no se recalculan. El docente debe re-importar.
- **Archivos xlsx grandes (>10k filas)** → Mitigation: parseo en streaming con openpyxl (read_only=True). Sin límite fijo por ahora; se puede añadir en C-11 si hay problemas de performance.
- **Columnas del LMS con nombres variables** → Mitigation: RN-01 define la convención `(Real)` como criterio de detección. Si el LMS exporta con otro formato, el docente no verá actividades numéricas; se documenta.

## Migration Plan

1. `alembic upgrade head` aplica `0007_calificacion_umbral_materia`.
2. Sin datos existentes a migrar (tablas nuevas).
3. Rollback: `alembic downgrade -1` borra ambas tablas (DROP TABLE).
