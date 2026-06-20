## Why

La coordinación y los equipos docentes necesitan un canal de seguimiento estructurado y auditable para repartir trabajo entre roles (revisar entregas, contactar alumnos atrasados, preparar coloquios). Hoy esa coordinación es informal y no deja trazabilidad de quién pidió qué, a quién, ni en qué estado está. C-16 introduce el workflow de tareas internas (Épica 8, FL-05), un módulo de alto uso que gestiona varios cientos de tareas en simultáneo durante el período activo.

## What Changes

- Nuevo modelo `Tarea` (E12): `materia_id` (nullable, nivel institucional), `asignado_a` (FK Usuario), `asignado_por` (FK Usuario), `estado` (enum Pendiente | En progreso | Resuelta | Cancelada), `descripcion`, `contexto_id` (referencia opcional a otra entidad del dominio).
- Nuevo modelo `ComentarioTarea` (E12): hilo de comentarios sobre una tarea (`tarea_id`, `autor_id`, `texto`, `creado_at`).
- Enum `EstadoTarea` con transiciones controladas: Pendiente → En progreso → Resuelta; cancelación posible desde cualquier estado no terminal.
- Alta de tarea con auto-asignación permitida (un usuario puede asignarse a sí mismo).
- Delegación / asignación a otro docente del equipo con trazabilidad completa (asignador + asignado registrados).
- Vista "Mis tareas" (F8.1) filtrada por `asignado_a` = usuario de sesión.
- Administración global (F8.3) con filtros por `estado`, `asignado_a`, `asignado_por`, `materia_id`, todos tenant-scoped.
- Comentarios en hilo sobre cada tarea (F8.2 evidencias / observaciones de cierre).
- Endpoints `/api/v1/tareas/*` protegidos por `require_permission("tareas:gestionar")`.
- Migración Alembic `014_tareas_internas`: tablas `tarea` y `comentario_tarea` con índices compuestos para el alto volumen de consultas.

## Capabilities

### New Capabilities

- `tarea`: alta, asignación, delegación con trazabilidad, transiciones de estado, listado "mis tareas", administración global con filtros, todo aislado por tenant.
- `comentario-tarea`: hilo de comentarios/evidencias asociado a una tarea, ordenado cronológicamente y aislado por tenant.

### Modified Capabilities

(ninguna — C-16 sólo agrega capacidades nuevas)

## Impact

- **Modelos**: `backend/app/models/tarea.py`, `backend/app/models/comentario_tarea.py`; registro en `backend/app/models/__init__.py`.
- **Migración**: `backend/alembic/versions/014_tareas_internas.py` (revises 013).
- **Repositories**: `backend/app/repositories/tarea_repository.py`, `comentario_tarea_repository.py` (extienden BaseRepository, filtran por tenant y `deleted_at IS NULL`).
- **Schemas**: `backend/app/schemas/tareas.py` (Pydantic v2, `extra='forbid'`).
- **Services**: `backend/app/services/tarea_service.py` (reglas de transición, validación de delegación, scoping).
- **Router**: `backend/app/api/v1/routers/tareas.py`; registro en `backend/app/main.py`.
- **RBAC**: seed del permiso `tareas:gestionar` (PROFESOR, COORDINADOR, ADMIN; TUTOR sobre lo propio).
- **Dependencias**: requiere C-07 (equipos/asignaciones) para validar pertenencia al equipo docente en la delegación.
- **Governance**: MEDIO — implementar con checkpoints; surfacear decisiones de transición de estado.
