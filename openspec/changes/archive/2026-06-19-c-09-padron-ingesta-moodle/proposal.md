## Why

C-07 completó el modelo de identidad (`Usuario`) y el eslabón que conecta personas con roles y contextos académicos (`Asignacion`). Sin embargo, el sistema aún no tiene forma de cargar el **padrón de alumnos** —el listado de quiénes cursan cada materia—, lo cual es requisito fundacional para todo el flujo de valor del producto: sin padrón no hay `Calificacion` que importar (C-10), no hay análisis de atrasados (C-11), no hay destinatarios para comunicaciones (C-12). El padrón es el punto de partida de la cadena `importar → analizar → comunicar`.

Este cambio debe ejecutarse ahora porque C-07 ya está disponible (la identidad de usuarios existe), y C-09 es la base sobre la que se construirá C-10. Además, introduce la **integración con Moodle Web Services**, un componente de infraestructura que habilitará no solo la importación on-demand del padrón sino también la sincronización automática nocturna, y que será reutilizado por C-10 para la ingesta de calificaciones.

## What Changes

- **Nuevos modelos `VersionPadron` + `EntradaPadron`** con enfoque **snapshot versionado**: cada importación crea una nueva `VersionPadron` con todas las `EntradaPadron` del padrón en ese momento. Activar una nueva versión desactiva la anterior (solo una versión activa por `materia_id` + `cohorte_id`). No hay delta ni diff entre versiones.
- **Migración Alembic** para tablas `version_padron`, `entrada_padron` + seed del permiso `padron:importar` en la matriz RBAC (rol COORDINADOR y ADMIN con acceso global, PROFESOR con scope `(propio)`).
- **Importación desde archivo** (`.xlsx` / `.csv`): endpoint que recibe el archivo, parsea filas, y retorna una **vista previa server-side** (JSON con filas detectadas, columnas mapeadas). Confirmación posterior para persistir la versión.
- **Cliente Moodle Web Services** (`integrations/moodle_ws.py`): integración para sincronizar el padrón desde el LMS. Soporta dos modalidades:
  - **On-demand**: el usuario dispara manualmente la sincronización desde la UI (vía endpoint).
  - **Nocturna programada**: worker automático que sincroniza los padrones de todas las materias activas del tenant.
  - Los errores de conexión con Moodle se mapean a HTTP `502` con reintento configurable.
- **Vaciar datos de materia** (F1.5, RN-04): endpoint que elimina todas las versiones de padrón (y en el futuro, calificaciones) de una materia, aislado por tenant y con guard de permiso `padron:importar(propio)` para PROFESOR.
- **Permiso `padron:importar`**: nuevo permiso en la matriz RBAC con dos variantes:
  - `padron:importar(propio)` — PROFESOR: solo sus materias asignadas.
  - `padron:importar` — COORDINADOR y ADMIN: cualquier materia del tenant.
- **Evento de auditoría `PADRON_CARGAR`**: el código ya existe en `app/core/audit_codes.py` como `AuditAction.PADRON_CARGAR`. Se integra en cada operación de escritura (carga de versión, vaciado de materia).

## Capabilities

### New Capabilities

- `padron-management`: Gestión del padrón de alumnos — `VersionPadron` y `EntradaPadron` CRUD vía repositorio, activación/desactivación de versiones (snapshot), consulta de versión activa por materia + cohorte, vaciado completo de datos de materia con scope por tenant y guard de permisos. Auditoría con `PADRON_CARGAR`.
- `padron-import-file`: Importación de padrón desde archivo `.xlsx`/`.csv` con vista previa server-side (parseo, detección de columnas, devolución de filas como JSON), confirmación para persistir como nueva versión. Soporta importación manual (PROFESOR en materias propias, COORDINADOR/ADMIN global).
- `moodle-integration`: Cliente Moodle Web Services para sincronización de padrón (listado de participantes por curso). Soporta sincronización on-demand vía endpoint REST y sincronización nocturna programada via worker asíncrono. Manejo de errores de conectividad con mapeo a `502` + reintento. Base reutilizable por C-10 para importación de calificaciones desde Moodle.

### Modified Capabilities

*(Ninguna. C-09 no modifica capabilities existentes — introduce capabilities nuevas.)*

## Impact

- **Backend**: nuevos modelos (`version_padron.py`, `entrada_padron.py`), repositorio (`VersionPadronRepository`), servicio (`PadronService`), router (`/api/v1/routers/padron.py`), integración (`integrations/moodle_ws.py`), worker de sincronización nocturna.
- **Base de datos**: migración Alembic con tablas `version_padron` y `entrada_padron` + seed del permiso `padron:importar` en matriz RBAC.
- **Permisos**: nuevo permiso `padron:importar` con scope `(propio)` para PROFESOR y global para COORDINADOR/ADMIN.
- **Auditoría**: reutiliza `AuditAction.PADRON_CARGAR` ya existente en `app/core/audit_codes.py`.
- **Integraciones**: nuevo módulo `integrations/moodle_ws.py` que será la base para la integración de C-10 (calificaciones desde Moodle).
- **Workers**: nuevo worker asíncrono para sincronización nocturna de padrón.
- **No requiere cambios frontend** — todo el cambio es backend.
- **Tests**: suite completa en `tests/test_padron/` con cobertura ≥80% líneas, ≥90% reglas de negocio. Tests de integración con mock de Moodle WS, fallback a `502`, versionado snapshot, import xlsx/csv, entradas con `usuario_id` nulo (alumno sin cuenta), aislamiento multi-tenant.
