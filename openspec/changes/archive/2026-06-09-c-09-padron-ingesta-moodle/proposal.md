## Why

El sistema necesita conocer qué alumnos están habilitados en cada materia para poder, más adelante (C-10/C-11), consolidar calificaciones, detectar atrasados y comunicar. Hoy no existe forma de cargar ese padrón ni de mantener su historial. Esta es la puerta de entrada de datos del LMS al sistema: sin padrón, ningún módulo de análisis tiene sobre qué operar.

El padrón debe ser **versionado** (no destructivo): cada carga genera una nueva versión y conserva las anteriores, con una sola versión activa por `materia × cohorte`. Esto contradice la redacción de RN-05 ("upsert destructivo") y resuelve la pregunta abierta **PA-01** a favor del modelo de datos E6 y del scope de C-09 en `CHANGES.md`, que son la fuente de verdad vigente. RN-05 queda **superseded** por esta decisión (ver Impact).

## What Changes

- **Modelos `VersionPadron` y `EntradaPadron`** (KB §E6): una `VersionPadron` agrupa las `EntradaPadron` de una carga; al activar una versión nueva, la anterior de ese `(materia, cohorte)` se desactiva (no se borra). Una `EntradaPadron` puede existir sin `usuario_id` (alumno aún sin cuenta). El `email` de la entrada es PII → cifrado AES-256-GCM en reposo, igual que en `Usuario` (C-07).
- **Importación de padrón por archivo** (F1.3 / F1.4): subir `.xlsx` o `.csv`, generar una **vista previa** server-side (alumnos detectados, columnas mapeadas, errores de parseo) y luego **confirmar** para crear la nueva versión activa. El parseo no persiste nada hasta la confirmación.
- **Cliente de integración Moodle Web Services** (`app/integrations/moodle_ws.py`): cliente dedicado y aislado que sincroniza usuarios/actividades del LMS. Soporta **sync nocturna** programada y **sync on-demand**. Sus errores mapean a **HTTP 502** con mecanismo de reintento. Para tenants sin Web Services, el flujo de importación por archivo es el **fallback manual**.
- **Vaciar datos de padrón de una materia** (F1.5 / RN-04): desactiva (soft-delete) las versiones/entradas de padrón del `(materia, cohorte)` en scope, sin afectar otras materias ni datos de otros docentes.
- **Permisos RBAC nuevos**: `padron:cargar`, `padron:ver`, `padron:vaciar` (seed idempotente para todos los tenants activos; asignados a PROFESOR scope `propio` y COORDINADOR/ADMIN scope `global`).
- **Auditoría**: toda carga de padrón emite el evento `PADRON_CARGAR` (ya presente en el catálogo `AccionAuditoria`) con `filas_afectadas` y `detalle` (materia, cohorte, versión, origen archivo/moodle).
- **Migración `008_padron_y_moodle`**: tablas `version_padron` y `entrada_padron` + índices + seed de permisos.

## Capabilities

### New Capabilities
- `padron-versionado`: gestión versionada del padrón de alumnos por materia×cohorte — modelos, repositorios, servicio de import (xlsx/csv) con preview+confirm, activación/desactivación de versiones, vaciado scope-isolated, endpoints y permisos `padron:*`.
- `moodle-integration`: cliente aislado de Moodle Web Services para sync de usuarios/actividades (nocturna + on-demand), con mapeo de errores a HTTP 502 + reintento y fallback a importación manual.

### Modified Capabilities
<!-- Ninguna capability existente cambia sus requisitos a nivel spec. PADRON_CARGAR ya existe en el catálogo de auditoría (audit-log, C-05) y se consume sin modificar su contrato. -->

## Impact

- **Nuevo código backend**: `app/models/{version_padron,entrada_padron}.py`, `app/repositories/{version_padron_repository,entrada_padron_repository}.py`, `app/services/padron_service.py`, `app/schemas/padron.py`, `app/api/v1/routers/padron.py`, `app/integrations/moodle_ws.py`. Registro del router en el agregador de la API.
- **Migración**: `backend/alembic/versions/008_padron_y_moodle.py` (una sola migración por cambio de schema). Down_revision `007`.
- **RBAC**: 3 permisos nuevos + filas de matriz. Reutiliza el patrón de seed idempotente `ON CONFLICT DO NOTHING` de migraciones previas.
- **Auditoría**: consume `AccionAuditoria.PADRON_CARGAR` (C-05) sin cambios al contrato.
- **PII**: `entrada_padron.email` cifrado con `CryptoService` (C-03), descifrado solo en la capa de servicio; nunca en logs ni en `__repr__`.
- **Dependencias**: requiere C-06 (`Materia`, `Cohorte`) y C-07 (`Usuario`) — ya implementados y archivados. Habilita C-10 (calificaciones) y C-11 (atrasados), que referencian `EntradaPadron`.
- **Nueva dependencia de librería**: parser de planillas (`openpyxl` para `.xlsx`; `csv` stdlib para `.csv`). A confirmar en design.
- **Regla de negocio superseded**: RN-05 ("upsert destructivo, sin historial") queda reemplazada por el modelo versionado de E6/C-09. Debe anotarse en `knowledge-base/05_reglas_de_negocio.md` / `10_preguntas_abiertas.md` (PA-01) al archivar.
- **Pendiente operativo (no bloqueante para esta capa)**: el scheduler concreto de la sync nocturna (cron del worker) se define junto con la infraestructura de jobs; C-09 entrega el cliente y el endpoint on-demand, dejando la activación nocturna como punto de integración.
