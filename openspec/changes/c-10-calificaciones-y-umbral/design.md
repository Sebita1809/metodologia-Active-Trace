## Context

El sistema actual tiene el modelo `UmbralMateria` en código pero sin migración aplicada (la tabla no existe en BD). El modelo `Calificacion` no existe. El permiso `calificaciones:importar` ya está seedeado desde C-04 (migración 003) y asignado a PROFESOR (propio), COORDINADOR (global) y ADMIN (global).

C-09 (padron-ingesta-moodle) está completo, por lo que los modelos `EntradaPadron` y `VersionPadron` están disponibles como dependencias.

Este cambio se integra con el flujo FL-02 (pasos 3-5): importar calificaciones → configurar umbral → cómputo automático.

## Goals / Non-Goals

**Goals:**
- Modelar `Calificacion` y completar `UmbralMateria` con `valores_aprobatorios`
- Importar calificaciones desde archivo LMS con preview y selección de actividades
- Configurar umbral de aprobación por asignación docente (default 60%)
- Derivar automáticamente `aprobado` según reglas E7 (numérica vs umbral, textual vs valores aprobatorios)
- Registrar auditoría `CALIFICACIONES_IMPORTAR`

**Non-Goals:**
- No incluye análisis de atrasados ni ranking (son C-11)
- No incluye comunicación con alumnos (es C-12)
- No incluye sincronización automática con Moodle (solo import manual vía archivo)
- No incluye frontend (es C-22)

## Decisions

1. **Calificacion referencias `entrada_padron_id` en vez de `usuario_id`**: La calificación se asocia a una entrada del padrón (alumno en materia×cohorte), no directamente al usuario. Esto permite trackear alumnos que aún no tienen cuenta creada y mantiene consistencia con el versionado del padrón.

2. **`aprobado` como campo derivado en la app (no columna en BD)**: La KB define `aprobado` como booleano derivado de `nota_numerica >= umbral OR nota_textual ∈ valores_aprobatorios`. Se implementa como propiedad calculada en el modelo/service para evitar inconsistencias si cambia el umbral después de la importación.

3. **JSONB para `valores_aprobatorios`**: PostgreSQL JSONB con `ARRAY` de textos. Es flexible para diferentes conjuntos de valores aprobatorios sin necesidad de migraciones. Se usa `sqlalchemy.dialects.postgresql.JSONB` y se mapea como `list[str]` en Python.

4. **Preview antes de confirmar**: El flujo de importación es en dos pasos: (1) subir archivo → preview con actividades detectadas, (2) confirmar con selección de actividades. Esto replica el patrón de `padron-ingesta-moodle` (C-09).

5. **Umbral por defecto 60%**: Consistente con RN-03. Se crea automáticamente al asignar un PROFESOR/TUTOR a una materia (ya implementado en `AsignacionService.create()`).

## Risks / Trade-offs

- **[Riesgo medio] Umbral sin migración aplicada**: El modelo `UmbralMateria` existe en código y es referenciado pero su tabla no existe en BD. La migración 008 debe crearla. → **Mitigación**: Se incluye `CREATE TABLE IF NOT EXISTS` en la migración.
- **[Riesgo bajo] Dependencia de C-09**: `Calificacion` FK a `EntradaPadron`. Si hay datos de padrón corruptos, podría fallar la importación. → **Mitigación**: Los endpoints validan existencia de `VersionPadron` activa antes de importar.
- **[Trade-off] `aprobado` no persistido**: Al ser derivado, cada consulta recalcula. Podría ser costoso con muchas calificaciones. → Se acepta por consistencia; si es necesario en el futuro se puede agregar un caché o columna materializada.
