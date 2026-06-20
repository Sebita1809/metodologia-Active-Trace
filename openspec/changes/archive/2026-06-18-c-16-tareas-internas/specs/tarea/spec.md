## ADDED Requirements

### Requirement: Alta de tarea con trazabilidad de asignador

El sistema DEBE permitir crear una tarea registrando como `asignado_por` al usuario de la sesión (derivado del JWT, nunca del body) y persistiendo `asignado_a`, `descripcion`, `estado` inicial `Pendiente`, `tenant_id` de la sesión y, opcionalmente, `materia_id` y `contexto_id`.

#### Scenario: Crear tarea asignada a otro docente
- WHEN un COORDINADOR autenticado crea una tarea con `asignado_a` = otro docente del equipo, `descripcion` y `materia_id`
- THEN la tarea se persiste con `estado` = `Pendiente`, `asignado_por` = id del COORDINADOR de la sesión, `asignado_a` = el docente indicado y `tenant_id` = tenant de la sesión

#### Scenario: Auto-asignación permitida
- WHEN un PROFESOR autenticado crea una tarea con `asignado_a` = su propio id de usuario
- THEN la tarea se persiste con `asignado_por` = `asignado_a` = id del PROFESOR, sin error

#### Scenario: Tarea de nivel institucional sin materia
- WHEN un COORDINADOR crea una tarea sin `materia_id`
- THEN la tarea se persiste con `materia_id` = NULL y `estado` = `Pendiente`

#### Scenario: asignado_por nunca se toma del body
- WHEN una petición de alta incluye un campo `asignado_por` en el body
- THEN el schema lo rechaza (`extra='forbid'`) o el service lo ignora y usa el id de la sesión

### Requirement: Delegación de tarea con trazabilidad

El sistema DEBE permitir reasignar una tarea existente a otro miembro del equipo docente, actualizando `asignado_a` y conservando intacto el `asignado_por` original, manteniendo trazabilidad del cambio.

#### Scenario: Delegar a otro miembro del equipo
- WHEN un PROFESOR delega una tarea de la que es `asignado_a` hacia otro docente del mismo equipo
- THEN la tarea actualiza `asignado_a` al nuevo docente, conserva el `asignado_por` original y refresca `updated_at`

#### Scenario: Delegar a usuario fuera del equipo es rechazado
- WHEN se intenta delegar una tarea a un usuario que no pertenece al equipo docente de la materia
- THEN el sistema responde 422/403 y la tarea no cambia de `asignado_a`

### Requirement: Transiciones de estado controladas

El sistema DEBE permitir únicamente las transiciones válidas: `Pendiente → En progreso | Cancelada`, `En progreso → Resuelta | Cancelada | Pendiente`, `Resuelta → En progreso`. `Cancelada` es terminal. Cualquier otra transición DEBE ser rechazada.

#### Scenario: Avanzar de Pendiente a En progreso
- WHEN el `asignado_a` cambia el estado de una tarea de `Pendiente` a `En progreso`
- THEN la tarea queda en `En progreso`

#### Scenario: Resolver una tarea en progreso
- WHEN el `asignado_a` cambia el estado de `En progreso` a `Resuelta`
- THEN la tarea queda en `Resuelta`

#### Scenario: Cancelar desde Pendiente
- WHEN un usuario con permiso cancela una tarea en `Pendiente`
- THEN la tarea queda en `Cancelada`

#### Scenario: Transición inválida es rechazada
- WHEN se intenta cambiar el estado de una tarea `Cancelada` a `En progreso`
- THEN el sistema responde 409/422 y el estado no cambia

#### Scenario: Reapertura controlada de Resuelta
- WHEN se cambia el estado de una tarea `Resuelta` a `En progreso`
- THEN la tarea queda en `En progreso`

### Requirement: Vista mis tareas

El sistema DEBE listar las tareas cuyo `asignado_a` es el usuario de la sesión, dentro de su tenant, excluyendo las soft-deleted.

#### Scenario: Listar tareas propias
- WHEN un TUTOR autenticado solicita sus tareas
- THEN el sistema devuelve sólo las tareas con `asignado_a` = id del TUTOR y `tenant_id` de la sesión, sin las eliminadas

#### Scenario: No incluye tareas de otros usuarios
- WHEN un docente solicita "mis tareas" y existen tareas asignadas a otros docentes del mismo tenant
- THEN esas tareas NO aparecen en el resultado

### Requirement: Administración global con filtros

El sistema DEBE permitir a COORDINADOR/ADMIN listar todas las tareas del tenant con filtros opcionales por `estado`, `asignado_a`, `asignado_por` y `materia_id`, con paginación.

#### Scenario: Listar todas las tareas del tenant
- WHEN un COORDINADOR lista tareas sin filtros
- THEN el sistema devuelve todas las tareas del tenant (paginadas), excluyendo las soft-deleted

#### Scenario: Filtrar por estado y asignado_a
- WHEN un COORDINADOR lista tareas filtrando por `estado` = `En progreso` y `asignado_a` = un docente
- THEN el resultado contiene sólo tareas de ese docente en estado `En progreso`

#### Scenario: Filtrar por asignado_por
- WHEN un COORDINADOR lista tareas filtrando por `asignado_por` = su propio id
- THEN el resultado contiene sólo las tareas que él mismo asignó

### Requirement: Aislamiento por tenant

El sistema DEBE garantizar que ninguna operación sobre tareas exponga datos de otro tenant.

#### Scenario: Tarea de otro tenant no es visible
- WHEN un usuario del tenant A solicita una tarea cuyo `tenant_id` es el tenant B
- THEN el sistema responde 404 y no expone datos del tenant B

#### Scenario: Listado global acotado al tenant de la sesión
- WHEN un COORDINADOR del tenant A lista todas las tareas
- THEN el resultado contiene exclusivamente tareas con `tenant_id` = A

### Requirement: Control de acceso fail-closed

Todos los endpoints de tareas DEBEN exigir el permiso `tareas:gestionar`; sin permiso explícito el acceso se deniega.

#### Scenario: Acceso sin permiso es denegado
- WHEN un usuario sin el permiso `tareas:gestionar` invoca cualquier endpoint de `/api/v1/tareas/*`
- THEN el sistema responde 403
