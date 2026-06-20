## Why

C-21 dejó listo el shell del frontend (scaffolding, cliente HTTP con refresh, autenticación, navegación y guards), y el backend ya expone calificaciones+umbral (C-10), análisis de atrasados/ranking/notas/reportes (C-11) y la cola de comunicaciones con worker (C-12). Sin embargo no existe ninguna pantalla que permita al PROFESOR/TUTOR operar su comisión: importar calificaciones, configurar el umbral, ver atrasados, comunicar y hacer seguimiento. C-22 construye esa capa de presentación académico-docente, que es el flujo de mayor valor del producto (importar → analizar → comunicar) llevado a la interfaz.

## What Changes

- **Feature `gestion-comision`**: pantalla central del PROFESOR para operar una asignación (materia × cohorte). Selección de comisión y orquestación de las sub-vistas (importación, umbral, atrasados, ranking, notas finales, reportes rápidos).
- **Importación de calificaciones con preview** (FL-02 pasos 3-5): subir el archivo del LMS, previsualizar las actividades detectadas (`POST /api/calificaciones/preview`), seleccionar cuáles incluir y confirmar la importación (`POST /api/calificaciones/import`). Estado informativo cuando aún no hay datos.
- **Configuración de umbral de aprobación**: formulario para ver y fijar el umbral porcentual y los valores aprobatorios de la asignación (`GET`/`PUT /api/calificaciones/umbral`), con default 60 %.
- **Vistas de análisis** (consumen C-11): tabla de alumnos atrasados (`GET /api/v1/analisis/atrasados`), ranking de actividades aprobadas (`/ranking`), notas finales agrupadas (`/notas-finales`) y reportes rápidos por comisión (`/reporte`).
- **Detección de entregas sin corregir + export** (FL-02 paso 6): subir el reporte de finalización del LMS (`POST /api/calificaciones/finalizacion-preview`), mostrar la tabla de posibles entregas sin corregir y exportarla a archivo descargable (CSV/cliente).
- **Comunicación a alumnos atrasados** (FL-02 paso 7, FL-04): selección de destinatarios desde la tabla de atrasados, previsualización del mensaje por alumno (`POST /preview`), envío a la cola (`POST /` comunicaciones) y **tracking de estado en tiempo real** (Pendiente → Enviando → OK / Fallido / Cancelado) vía polling de la cola (`GET /` comunicaciones por `lote_id`).
- **Monitores de seguimiento** (F2.8): vista filtrable del estado de actividades de los alumnos de la comisión para TUTOR/PROFESOR (filtros por alumno, correo, comisión, actividad, mínimo cumplido), reutilizando los datos de atrasados/reportes.
- **Tests de componentes e integración** (con mocks de API, sin DB real): flujo de importación con preview/selección, tabla de atrasados, preview de comunicación y tracking de transiciones de estado.

## Capabilities

### New Capabilities
- `gestion-comision-ui`: pantalla de gestión de comisión del PROFESOR — selección de asignación, orquestación de las sub-vistas académicas y estados informativos cuando no hay datos.
- `importacion-calificaciones-ui`: flujo de importación con preview de actividades, selección de actividades a incluir, confirmación, y detección/exportación de entregas sin corregir.
- `umbral-configuracion-ui`: configuración del umbral de aprobación y valores aprobatorios por asignación.
- `analisis-academico-ui`: vistas de atrasados, ranking, notas finales y reportes rápidos consumiendo los endpoints de análisis.
- `monitor-seguimiento-ui`: monitor filtrable del estado de actividades de alumnos para la vista TUTOR/PROFESOR.
- `comunicacion-atrasados-ui`: selección de destinatarios, preview de comunicación, envío a la cola y tracking de estados en tiempo real.

### Modified Capabilities
<!-- Ninguna: C-22 introduce capacidades de presentación nuevas; consume los contratos de backend de C-10/C-11/C-12 sin modificar sus requisitos. -->

## Impact

- **Nuevo código**: features bajo `frontend/src/features/` (`gestion-comision/`, con sus `components`, `hooks`, `services`, `types`, `pages`), más servicios de API tipados que consumen los endpoints de calificaciones, análisis y comunicaciones. Tests de componentes e integración con mocks.
- **APIs consumidas** (sin cambios en backend): `POST /api/calificaciones/preview`, `POST /api/calificaciones/import`, `POST /api/calificaciones/finalizacion-preview`, `GET /api/calificaciones`, `GET`/`PUT /api/calificaciones/umbral`; `GET /api/v1/analisis/{atrasados,ranking,notas-finales,reporte}`; comunicaciones `POST /preview`, `POST /`, `GET /` (cola por `lote_id`).
- **Dependencias**: requiere C-21 (frontend shell + auth + http-client + route-guards, archivado) y C-12 (comunicaciones cola+worker). Consume C-10 (calificaciones+umbral) y C-11 (análisis).
- **Reutiliza** de C-21: `shared/services/api.ts` (Axios con refresh transparente), guards por rol/permiso, layout y navegación. Todo fetch pasa por hooks de TanStack Query; formularios con React Hook Form + Zod; estilos Tailwind.
- **Restricción de seguridad clave**: identidad, roles y tenant salen EXCLUSIVAMENTE del JWT. El frontend nunca envía identidad por parámetro; `asignacion_id`/`materia_id` son datos de negocio. Los guards de UI son UX; la autoridad de autorización es el backend (403). Governance del dominio: BAJO.
- **Gap conocido**: el router de comunicaciones existe en el backend pero su montaje/prefijo en `main.py` debe confirmarse durante la implementación; el contrato a consumir es el de la spec `comunicaciones`.
