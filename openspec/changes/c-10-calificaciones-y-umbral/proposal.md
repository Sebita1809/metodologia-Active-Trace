## Why

Los docentes necesitan importar las calificaciones de sus materias desde el LMS (Moodle) para poder analizar el rendimiento de los alumnos, detectar atrasados y generar reportes. Actualmente no existe un modelo de calificaciones ni umbrales de aprobación, lo que bloquea todo el flujo de análisis académico (C-11) y comunicaciones (C-12). Sin este cambio, el PROFESOR no puede trabajar con datos reales de notas.

## What Changes

- Nuevo modelo `Calificacion` con nota numérica y/o textual, aprobación derivada, origen (Importado/Manual), FK a `EntradaPadron` y `Materia`
- Modificación del modelo `UmbralMateria` existente: agregar campo `valores_aprobatorios` (JSONB lista de textos) para valores textuales que cuentan como aprobado
- Nueva migración Alembic `008` que crea la tabla `calificacion` y actualiza `umbral_materia`
- Nuevo repositorio `CalificacionRepository`
- Nuevo servicio `CalificacionService` con lógica de importación y derivación de `aprobado`
- Nuevo router `calificaciones.py` con endpoints para:
  - `POST /api/v1/calificaciones/import/preview` — vista previa de importación
  - `POST /api/v1/calificaciones/import/confirm` — confirmar importación
  - `PUT /api/v1/calificaciones/umbral` — configurar umbral por asignación
  - `GET /api/v1/calificaciones/{materia_id}/{cohorte_id}` — listar calificaciones
  - `DELETE /api/v1/calificaciones/{materia_id}/{cohorte_id}` — vaciar datos (F1.5, RN-04)
- Auditoría `CALIFICACIONES_IMPORTAR` en importaciones
- Actualización del modelo `UmbralMateriaRepository` con métodos para `valores_aprobatorios`

## Capabilities

### New Capabilities

- `grade-import`: Importación de calificaciones desde archivo LMS con preview, selección de actividades numéricas y textuales, y confirmación. Incluye derivación automática del campo `aprobado`.
- `umbral-configuration`: Configuración del umbral de aprobación por asignación docente, con porcentaje mínimo y valores textuales aprobatorios. Valor por defecto 60%.

### Modified Capabilities

- `user-management`: El modelo `UmbralMateria` se extiende con `valores_aprobatorios`. La creación de asignaciones (PROFESOR/TUTOR) ya auto-crea umbrales con defecto, ese comportamiento se mantiene.
- `padron-management`: El modelo `Calificacion` referencia `EntradaPadron` para asociar calificaciones a alumnos del padrón.

## Impact

- **Backend**: Nuevo modelo/servicio/repositorio/router para calificaciones. Modificación del modelo `UmbralMateria` existente + su repositorio. Nueva migración Alembic.
- **API**: Nuevos endpoints bajo `/api/v1/calificaciones/*` con guard `calificaciones:importar` (ya existe en seed de permisos).
- **Tests**: Nuevo directorio `tests/test_calificaciones/` con tests de importación, umbral, derivación de aprobado y aislamiento multi-tenant.
- **Dependencias**: Requiere `C-09` (padron-ingesta-moodle) completado — los modelos `EntradaPadron` y `VersionPadron` existen y están migrados.
