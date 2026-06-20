## ADDED Requirements

### Requirement: Listado completo del log con paginación
El sistema SHALL exponer el log completo de `audit_log` como un listado paginado (`limit`/`offset`) ordenado por `fecha_hora` descendente, scoped por `tenant_id` y por el alcance del solicitante. El permiso `auditoria:ver` SHALL ser obligatorio; sin él, el sistema SHALL responder 403 (fail-closed).

#### Scenario: Listado paginado más reciente primero
- **WHEN** un usuario con `auditoria:ver` solicita el log con `limit=2` y `offset=0` y existen 3 registros
- **THEN** el sistema devuelve los 2 registros más recientes ordenados por `fecha_hora` descendente

#### Scenario: Sin permiso, acceso denegado
- **WHEN** un usuario sin `auditoria:ver` solicita el log
- **THEN** el sistema responde 403 y no devuelve registros

### Requirement: Filtro por rango de fechas
El sistema SHALL permitir filtrar el log por un rango de fechas `desde`/`hasta` sobre `fecha_hora`. Los registros fuera del rango SHALL excluirse.

#### Scenario: Solo registros dentro del rango
- **WHEN** un usuario filtra el log con `desde=2026-06-01` y `hasta=2026-06-02` y existen registros del 31 de mayo, del 1 de junio y del 3 de junio
- **THEN** el sistema devuelve únicamente el registro del 1 de junio

### Requirement: Filtro por usuario
El sistema SHALL permitir filtrar el log por `usuario_id`, devolviendo solo los registros cuyo `actor_id` coincide. Cuando el alcance es `propio`, el filtro de usuario SHALL intersectarse con el equipo del solicitante.

#### Scenario: Filtro por actor específico
- **WHEN** un usuario con alcance `global` filtra el log por `usuario_id=U1`
- **THEN** el sistema devuelve únicamente registros con `actor_id = U1`

#### Scenario: COORDINADOR no puede consultar fuera de su equipo
- **WHEN** un COORDINADOR con alcance `propio` filtra el log por un `usuario_id` que NO pertenece a su equipo
- **THEN** el sistema devuelve un resultado vacío

### Requirement: Filtro por acción o estado
El sistema SHALL permitir filtrar el log por código de `accion` exacto y/o por estado de comunicación derivado de la familia `COMUNICACION_*`.

#### Scenario: Filtro por código de acción
- **WHEN** un usuario filtra el log por `accion=CALIFICACIONES_IMPORTAR`
- **THEN** el sistema devuelve únicamente registros con ese código de acción

#### Scenario: Filtro por estado de comunicación
- **WHEN** un usuario filtra el log por estado `Fallido`
- **THEN** el sistema devuelve únicamente registros de comunicación cuyo código mapea al estado Fallido

### Requirement: Filtro por materia
El sistema SHALL permitir filtrar el log por `materia_id`, devolviendo solo los registros asociados a esa materia.

#### Scenario: Solo registros de la materia
- **WHEN** un usuario filtra el log por `materia_id=M1`
- **THEN** el sistema devuelve únicamente registros con `materia_id = M1`

### Requirement: Alcance propio del COORDINADOR sobre el log
El sistema SHALL acotar el log al equipo del solicitante cuando el alcance del permiso `auditoria:ver` es `propio`, resolviendo el equipo a partir de las asignaciones (`Asignacion`). Con alcance `global` el log SHALL abarcar todo el tenant.

#### Scenario: COORDINADOR ve solo su equipo
- **WHEN** un COORDINADOR con alcance `propio` consulta el log y su equipo son {D1, D2}
- **THEN** el log incluye solo registros con `actor_id` en {D1, D2}

#### Scenario: Equipo vacío produce log vacío (fail-closed)
- **WHEN** un COORDINADOR con alcance `propio` no tiene docentes en su equipo
- **THEN** el log devuelve resultado vacío y NUNCA toda la auditoría del tenant

### Requirement: Aislamiento por tenant del log
El sistema SHALL filtrar toda consulta del log por `tenant_id` por defecto. Un tenant SHALL ver únicamente sus propios registros de auditoría, independientemente de cualquier filtro aplicado.

#### Scenario: Un tenant no ve el log de otro
- **WHEN** el tenant A tiene registros de auditoría y un usuario del tenant B consulta el log
- **THEN** ningún registro del tenant A aparece en los resultados del tenant B
