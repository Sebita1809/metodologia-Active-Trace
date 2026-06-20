## Context

C-10 persiste `Calificacion` y `UmbralMateria`. Con esos datos el sistema puede responder preguntas analíticas: ¿quién está atrasado?, ¿quiénes aprobaron más actividades?, ¿cuál es la nota final de cada alumno? Este change agrega la capa de análisis — sin nuevas tablas, solo lógica de servicio sobre los datos ya existentes.

El dataset por asignación es acotado (típicamente < 200 alumnos × < 30 actividades). La computación en memoria en Python es suficiente y más legible que SQL complejo.

## Goals / Non-Goals

**Goals:**
- Endpoint `GET /api/analisis/atrasados` — lista de alumnos atrasados con detalle (RN-06)
- Endpoint `GET /api/analisis/ranking` — ranking de actividades aprobadas (RN-09)
- Endpoint `GET /api/analisis/notas-finales` — nota final agrupada por alumno (F2.5)
- Endpoint `GET /api/analisis/reporte` — métricas rápidas de la asignación (F2.4)
- Permiso `analisis:ver` para PROFESOR, TUTOR, COORDINADOR
- Sin nuevas tablas, sin migraciones

**Non-Goals:**
- Monitor transversal multi-asignación (F2.7/F2.8 — queda para C-22 frontend)
- Exportación a archivo de los reportes (F2.6 — queda para C-22)
- Persistencia de resultados analíticos (no hay tabla de cache ni snapshots)

## Decisions

### D-01: Computación en memoria en Python, no SQL agregado

**Decisión**: `AnalisisService` carga todas las `Calificacion` de la asignación via `CalificacionRepository.list_by_asignacion`, y computa atrasados/ranking/notas-finales en Python.

**Alternativa rechazada**: SQL con GROUP BY, HAVING, subqueries → más eficiente a escala, pero más difícil de mantener y testear. El dataset por asignación es pequeño; las reglas de negocio (RN-06, RN-09) son más claras expresadas en Python.

### D-02: Un router `/api/analisis/` separado de `/api/calificaciones/`

**Decisión**: Router propio `analisis.py` bajo el prefijo `/api/v1/analisis`. No se extiende el router de calificaciones.

**Razón**: Los endpoints de análisis tienen semántica distinta (lectura agregada) y audiencia más amplia (TUTOR también ve atrasados). Mantenerlos separados facilita versionar o restringir permisos de forma independiente.

### D-03: `asignacion_id` como parámetro obligatorio en todos los endpoints

**Decisión**: Todos los endpoints de análisis reciben `asignacion_id` como query param y lo usan como scope de los datos.

**Razón**: Consistent con C-10. El tenant se deriva del JWT, no del parámetro. El PROFESOR ve solo sus propias asignaciones (validación en service: la asignacion debe pertenecer al tenant del JWT).

### D-04: Atrasado = union de dos condiciones (RN-06)

**Decisión**: Un alumno es atrasado si (a) tiene actividades numéricas o textuales en el padrón activo sin `Calificacion` registrada, O (b) tiene calificaciones con `aprobado = False`. Ambas condiciones se evalúan con el `UmbralMateria` vigente de la asignación.

**Implicación**: el service necesita las `EntradaPadron` del padrón activo para detectar alumnos sin ninguna calificación (condición a). Esto requiere acceder a `PadronRepository` además de `CalificacionRepository`.

### D-05: Nota final = promedio ponderado o conteo de aprobadas (configurable)

**Decisión simplificada**: para el MVP de C-11, la nota final es el conteo de actividades aprobadas sobre el total de actividades importadas para esa asignación. No hay ponderación por actividad en esta versión. F2.5 queda cubierta con esta semántica simple.

## Risks / Trade-offs

- [Risk] Si una asignación tiene miles de calificaciones (dataset anómalo), la carga en memoria puede ser lenta → **Mitigation**: agregar paginación en C-22 si se detecta en producción; el endpoint actual devuelve todos los datos de la asignación.
- [Risk] Las `EntradaPadron` del padrón activo pueden no existir (C-09 no corrió) → **Mitigation**: el endpoint retorna lista vacía con campo `sin_padron: true` en el reporte; no lanza error.
- [Risk] Un TUTOR puede ver datos de cualquier asignación del tenant → **Mitigation**: validar en service que la `asignacion_id` pertenece al tenant del JWT. Si el TUTOR necesita scope propio, se resuelve en C-22.
