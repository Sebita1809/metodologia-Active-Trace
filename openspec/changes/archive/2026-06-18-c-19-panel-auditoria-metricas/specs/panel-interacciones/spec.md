## ADDED Requirements

### Requirement: Acciones por día en un rango de fechas
El sistema SHALL exponer una agregación de acciones por día sobre `audit_log`, scoped por `tenant_id`, que cuente las acciones agrupadas por fecha (`date_trunc('day', fecha_hora)`) dentro de un rango `desde`/`hasta`. La consulta SHALL requerir el permiso `auditoria:ver` y respetar el alcance del solicitante.

#### Scenario: Conteo diario dentro del rango
- **WHEN** un usuario con `auditoria:ver` de alcance `global` solicita las acciones por día entre el 2026-06-01 y el 2026-06-03 y existen 5 acciones el día 01, 0 el día 02 y 3 el día 03
- **THEN** el sistema devuelve una serie con `{dia: 2026-06-01, total: 5}` y `{dia: 2026-06-03, total: 3}` para el tenant del solicitante

#### Scenario: Fuera del rango no se cuenta
- **WHEN** existe una acción con `fecha_hora` anterior a `desde`
- **THEN** esa acción NO aparece en la serie devuelta

### Requirement: Estado de comunicaciones por docente
El sistema SHALL exponer una agregación que, a partir de los códigos `accion` de la familia `COMUNICACION_*` en `audit_log`, cuente las comunicaciones agrupadas por docente (`actor_id`) y por estado (Pendiente / Enviando / Enviado / Fallido / Cancelado), scoped por `tenant_id` y por el alcance del solicitante.

#### Scenario: Distribución por estado y docente
- **WHEN** el docente D1 tiene 2 acciones de comunicación enviadas y 1 fallida registradas
- **THEN** el sistema devuelve para D1 `{Enviado: 2, Fallido: 1}`

#### Scenario: Acciones no comunicacionales excluidas
- **WHEN** existe una acción `CALIFICACIONES_IMPORTAR` para el docente D1
- **THEN** esa acción NO se cuenta en la distribución de estados de comunicación

### Requirement: Interacciones por docente y materia
El sistema SHALL exponer una agregación que cuente las acciones agrupadas por `actor_id` y `materia_id` sobre `audit_log`, scoped por `tenant_id` y por el alcance del solicitante. Las filas con `materia_id` nulo SHALL agruparse bajo una clave "sin materia".

#### Scenario: Conteo por docente y materia
- **WHEN** el docente D1 registró 4 acciones en la materia M1 y 1 acción sin materia
- **THEN** el sistema devuelve `{actor: D1, materia: M1, total: 4}` y `{actor: D1, materia: sin_materia, total: 1}`

### Requirement: Log de últimas N acciones con límite configurable
El sistema SHALL exponer las últimas N acciones de `audit_log` ordenadas por `fecha_hora` descendente, scoped por `tenant_id` y por el alcance del solicitante. El valor de N SHALL ser configurable, con un valor por defecto de **200**, y SHALL estar acotado por un máximo duro que proteja la performance.

#### Scenario: Default de 200 registros
- **WHEN** un usuario solicita las últimas acciones sin especificar el límite y existen 500 registros
- **THEN** el sistema devuelve los 200 registros más recientes ordenados por `fecha_hora` descendente

#### Scenario: Límite configurable respetado
- **WHEN** un usuario solicita las últimas acciones con límite 50
- **THEN** el sistema devuelve a lo sumo 50 registros, los más recientes primero

#### Scenario: Límite por encima del máximo es acotado
- **WHEN** un usuario solicita un límite mayor al máximo duro permitido
- **THEN** el sistema acota el límite al máximo permitido en lugar de devolver una cantidad ilimitada

### Requirement: Alcance propio del COORDINADOR sobre el panel
El sistema SHALL acotar todas las agregaciones del panel al equipo del solicitante cuando el alcance del permiso `auditoria:ver` es `propio`. El equipo se SHALL resolver a partir de las asignaciones (`Asignacion`) del COORDINADOR. Con alcance `global` (ADMIN, FINANZAS) el panel SHALL abarcar todo el tenant.

#### Scenario: COORDINADOR ve solo su equipo
- **WHEN** un COORDINADOR con alcance `propio` consulta el panel y su equipo está compuesto por los docentes D1 y D2
- **THEN** las agregaciones incluyen únicamente acciones cuyo `actor_id` pertenece a {D1, D2} y excluyen acciones de docentes fuera del equipo

#### Scenario: Equipo vacío produce panel vacío (fail-closed)
- **WHEN** un COORDINADOR con alcance `propio` no tiene docentes asignados a su equipo
- **THEN** las agregaciones devuelven resultados vacíos y NUNCA toda la auditoría del tenant

#### Scenario: Alcance global ve todo el tenant
- **WHEN** un ADMIN con alcance `global` consulta el panel
- **THEN** las agregaciones abarcan todas las acciones del tenant, independientemente del actor

### Requirement: Permiso requerido para el panel de interacciones
El sistema SHALL exigir el permiso `auditoria:ver` para acceder a cualquier agregación del panel. Sin el permiso, el sistema SHALL responder 403 (fail-closed).

#### Scenario: Sin permiso, acceso denegado
- **WHEN** un usuario sin `auditoria:ver` solicita cualquier agregación del panel
- **THEN** el sistema responde 403 y no devuelve datos
