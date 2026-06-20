## Why

Con el padrón versionado (C-09) y los equipos docentes (C-07/C-08) operativos, el sistema carece aún de la capacidad de ingerir las notas reales del LMS y calcular aprobación por alumno. Sin `Calificacion` y `UmbralMateria`, la detección de atrasados (C-11) y la comunicación masiva (C-12) son imposibles — este change cierra ese hueco central del camino crítico.

## What Changes

- **Nuevo modelo `Calificacion`**: registra nota numérica y/o textual por alumno por actividad, con campo `aprobado` derivado automáticamente (RN-01, RN-02).
- **Nuevo modelo `UmbralMateria`**: configuración de umbral de aprobación (%) y valores textuales aprobatorios por asignación docente (RN-03). Scope aislado: no afecta datos de otros docentes.
- **Import calificaciones desde LMS (F1.1)**: endpoint multipart que parsea xlsx/csv, detecta columnas `(Real)` como numéricas (RN-01) y columnas textuales (RN-02), genera vista previa, permite selección de actividades a incluir y persiste solo las seleccionadas.
- **Import reporte de finalización (F1.2)**: endpoint que parsea el reporte de finalización del LMS, cruza con calificaciones existentes y devuelve actividades finalizadas sin calificación (RN-07, RN-08) — sin persistir datos, solo como resultado de análisis.
- **Configurar umbral (F2.1)**: endpoint `PUT /api/calificaciones/umbral` para que el PROFESOR establezca umbral_pct y valores_aprobatorios en su asignación.
- **Migración `0007_calificacion_umbral_materia`**: tablas `calificacion` y `umbral_materia`.
- **Audit**: código `CALIFICACIONES_IMPORTAR` en cada importación.

## Capabilities

### New Capabilities

- `calificaciones`: modelos `Calificacion` + `UmbralMateria`, import xlsx/csv con preview y selección de actividades, cálculo de `aprobado`, configuración de umbral por asignación. Alimenta el análisis de atrasados (C-11).

### Modified Capabilities

- `padron-versionado`: la relación `EntradaPadron → Calificacion` (1→N) se establece aquí; la spec existente no cambia en requerimientos, solo se documenta la nueva FK saliente.

## Impact

- **Nuevas tablas**: `calificacion`, `umbral_materia`
- **Nuevos endpoints**: `POST /api/calificaciones/import`, `POST /api/calificaciones/finalizacion-preview`, `GET /api/calificaciones/`, `PUT /api/calificaciones/umbral`, `GET /api/calificaciones/umbral`
- **Nuevos permisos RBAC**: `calificaciones:importar`, `calificaciones:ver`, `calificaciones:configurar`
- **Audit codes**: `CALIFICACIONES_IMPORTAR`
- **Dependencias**: `EntradaPadron` (C-09), `Asignacion` (C-07), `Materia` (C-06)
- **Desbloquea**: C-11 `analisis-atrasados-reportes`
