## 1. Migración

- [x] 1.1 Crear `backend/alembic/versions/014_tareas_internas.py` (revises 013, Create Date 2026-06-18)
- [x] 1.2 Definir tabla `tarea` con columnas BaseTenantModel (id, tenant_id, created_at, updated_at, deleted_at) + materia_id (nullable, FK materias RESTRICT), asignado_a (FK usuarios RESTRICT), asignado_por (FK usuarios RESTRICT), estado (VARCHAR 20), descripcion (texto), contexto_id (UUID nullable)
- [x] 1.3 Definir tabla `comentario_tarea` con columnas BaseTenantModel + tarea_id (FK tarea RESTRICT), autor_id (FK usuarios RESTRICT), texto (texto), creado_at (timestamptz server_default now)
- [x] 1.4 Agregar CheckConstraint `ck_tarea_estado_valid` (estado IN Pendiente, En progreso, Resuelta, Cancelada)
- [x] 1.5 Crear índices `ix_tarea_tenant_asignado_a`, `ix_tarea_tenant_estado`, `ix_tarea_tenant_asignado_por`, `ix_comentario_tarea_tenant_tarea`
- [x] 1.6 Seed RBAC del permiso `tareas:gestionar` (PROFESOR, COORDINADOR, ADMIN; TUTOR sobre lo propio)
- [x] 1.7 Implementar `downgrade` que dropea índices, constraints y ambas tablas

## 2. Modelos

- [x] 2.1 Crear `EstadoTarea(StrEnum)` con Pendiente, En progreso, Resuelta, Cancelada
- [x] 2.2 Crear `backend/app/models/tarea.py` (`Tarea(BaseTenantModel)`) con columnas y CheckConstraint
- [x] 2.3 Crear `backend/app/models/comentario_tarea.py` (`ComentarioTarea(BaseTenantModel)`) con `creado_at` server-side
- [x] 2.4 Registrar ambos modelos en `backend/app/models/__init__.py`

## 3. Repositories

- [x] 3.1 Crear `backend/app/repositories/tarea_repository.py` (`TareaRepository(BaseRepository)`)
- [x] 3.2 Implementar `listar(filtros, limit, offset)` tenant-scoped con filtros opcionales estado/asignado_a/asignado_por/materia_id
- [x] 3.3 Implementar `get_by_id` tenant-scoped (excluye soft-deleted)
- [x] 3.4 Crear `backend/app/repositories/comentario_tarea_repository.py` (`ComentarioTareaRepository(BaseRepository)`)
- [x] 3.5 Implementar `listar_por_tarea(tarea_id)` ordenado por `creado_at` asc, tenant-scoped

## 4. Schemas

- [x] 4.1 Crear `backend/app/schemas/tareas.py` con `model_config = ConfigDict(extra='forbid')`
- [x] 4.2 `TareaCreate` (asignado_a, descripcion, materia_id?, contexto_id?) — sin asignado_por
- [x] 4.3 `TareaDelegar` (nuevo_asignado_a)
- [x] 4.4 `TareaCambioEstado` (nuevo_estado: EstadoTarea)
- [x] 4.5 `TareaResponse` (todos los campos persistidos)
- [x] 4.6 `TareaFiltros` (estado?, asignado_a?, asignado_por?, materia_id?, limit, offset)
- [x] 4.7 `ComentarioTareaCreate` (texto) y `ComentarioTareaResponse`

## 5. Services

- [x] 5.1 Crear `backend/app/services/tarea_service.py`
- [x] 5.2 `crear_tarea` — set asignado_por = sesión, estado inicial Pendiente, tenant de sesión
- [x] 5.3 Definir `_TRANSICIONES_VALIDAS` y `cambiar_estado` con validación de la máquina de estados
- [x] 5.4 `delegar_tarea` — valida pertenencia al equipo (C-07), actualiza asignado_a, conserva asignado_por
- [x] 5.5 `mis_tareas` — listado con asignado_a = usuario de sesión
- [x] 5.6 `listar_admin` — listado global con filtros (scoping por rol COORDINADOR/ADMIN)
- [x] 5.7 `agregar_comentario` — set autor_id = sesión, valida existencia de la tarea en el tenant
- [x] 5.8 `listar_comentarios` — hilo ordenado de la tarea

## 6. Router

- [x] 6.1 Crear `backend/app/api/v1/routers/tareas.py` con prefix `/api/v1/tareas`
- [x] 6.2 `POST /` crear tarea — `require_permission("tareas:gestionar")`
- [x] 6.3 `GET /mias` mis tareas — guard
- [x] 6.4 `GET /` administración con filtros + paginación — guard
- [x] 6.5 `PATCH /{id}/estado` cambiar estado — guard
- [x] 6.6 `PATCH /{id}/delegar` delegar — guard
- [x] 6.7 `POST /{id}/comentarios` agregar comentario — guard
- [x] 6.8 `GET /{id}/comentarios` listar hilo — guard
- [x] 6.9 Registrar el router en `backend/app/main.py`

## 7. Tests

- [x] 7.1 Test alta de tarea: asignado_por desde sesión, estado inicial Pendiente, tenant correcto
- [x] 7.2 Test auto-asignación permitida (asignado_a = asignado_por)
- [x] 7.3 Test alta de nivel institucional (materia_id NULL)
- [x] 7.4 Test schema rechaza asignado_por en el body (extra='forbid')
- [x] 7.5 Test delegación a miembro del equipo conserva asignado_por original
- [x] 7.6 Test delegación a usuario fuera del equipo rechazada (422/403)
- [x] 7.7 Test transición Pendiente → En progreso
- [x] 7.8 Test transición En progreso → Resuelta
- [x] 7.9 Test cancelación desde Pendiente
- [x] 7.10 Test transición inválida desde Cancelada rechazada (409/422)
- [x] 7.11 Test reapertura Resuelta → En progreso
- [x] 7.12 Test mis tareas devuelve sólo asignado_a = sesión
- [x] 7.13 Test mis tareas excluye tareas de otros usuarios
- [x] 7.14 Test admin lista todas las tareas del tenant
- [x] 7.15 Test filtro por estado + asignado_a
- [x] 7.16 Test filtro por asignado_por
- [x] 7.17 Test aislamiento: tarea de otro tenant → 404
- [x] 7.18 Test listado global acotado al tenant de la sesión
- [x] 7.19 Test acceso sin permiso tareas:gestionar → 403
- [x] 7.20 Test agregar comentario: autor_id desde sesión, creado_at server-side
- [x] 7.21 Test schema comentario rechaza autor_id en el body
- [x] 7.22 Test comentario sobre tarea inexistente → 404
- [x] 7.23 Test hilo ordenado cronológicamente ascendente
- [x] 7.24 Test hilo vacío devuelve lista vacía
- [x] 7.25 Test aislamiento de comentarios entre tenants → 404
