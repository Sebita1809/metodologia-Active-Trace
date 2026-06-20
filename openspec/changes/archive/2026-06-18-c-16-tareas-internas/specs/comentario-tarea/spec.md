## ADDED Requirements

### Requirement: Agregar comentario al hilo de una tarea

El sistema DEBE permitir agregar un comentario a una tarea existente, registrando `autor_id` = usuario de la sesión (derivado del JWT, nunca del body), `texto`, `tenant_id` de la sesión y `creado_at` server-side.

#### Scenario: Agregar comentario a una tarea propia
- WHEN un docente autenticado agrega un comentario con `texto` a una tarea de su tenant
- THEN el comentario se persiste con `autor_id` = id del docente de la sesión, `creado_at` generado por el servidor y `tarea_id` = la tarea indicada

#### Scenario: autor_id nunca se toma del body
- WHEN una petición de comentario incluye `autor_id` en el body
- THEN el schema lo rechaza (`extra='forbid'`) o el service lo ignora y usa el id de la sesión

#### Scenario: Comentario sobre tarea inexistente es rechazado
- WHEN se intenta comentar una `tarea_id` que no existe o está soft-deleted en el tenant
- THEN el sistema responde 404 y no se crea el comentario

### Requirement: Listar el hilo de comentarios de una tarea

El sistema DEBE devolver los comentarios de una tarea ordenados cronológicamente ascendente por `creado_at`, acotados al tenant de la sesión y excluyendo los soft-deleted.

#### Scenario: Hilo ordenado cronológicamente
- WHEN se solicita el hilo de una tarea con varios comentarios creados en distintos momentos
- THEN el sistema devuelve los comentarios ordenados por `creado_at` ascendente

#### Scenario: Hilo vacío
- WHEN se solicita el hilo de una tarea sin comentarios
- THEN el sistema devuelve una lista vacía

### Requirement: Aislamiento por tenant de comentarios

El sistema DEBE garantizar que los comentarios de una tarea nunca se expongan ni se asocien a un tenant distinto.

#### Scenario: Comentario de tarea de otro tenant no es visible
- WHEN un usuario del tenant A solicita el hilo de una tarea cuyo `tenant_id` es el tenant B
- THEN el sistema responde 404 y no expone comentarios del tenant B
