### Requirement: Carrera tiene código único por tenant
El sistema SHALL garantizar que el par `(tenant_id, codigo)` sea único. Dos carreras dentro del mismo tenant no pueden compartir código; sí pueden existir carreras con el mismo código en tenants distintos.

#### Scenario: Código duplicado dentro del mismo tenant es rechazado
- **WHEN** un ADMIN intenta crear una Carrera con un `codigo` ya existente en el mismo tenant
- **THEN** el sistema responde HTTP 409 con mensaje que indica el conflicto de unicidad

#### Scenario: Código repetido en otro tenant es permitido
- **WHEN** un ADMIN crea una Carrera con un `codigo` que ya existe en un tenant diferente
- **THEN** el sistema crea la Carrera exitosamente (HTTP 201)

### Requirement: Carrera soporta estado activa/inactiva
El sistema SHALL permitir cambiar el estado de una Carrera entre `Activa` e `Inactiva`. El estado no afecta la visibilidad histórica de la carrera (soft delete es independiente del estado funcional).

#### Scenario: Carrera creada como Activa por defecto
- **WHEN** un ADMIN crea una Carrera sin especificar estado
- **THEN** la Carrera queda con `estado = Activa`

#### Scenario: Carrera se puede inactivar
- **WHEN** un ADMIN hace PATCH a una Carrera con `estado = Inactiva`
- **THEN** el sistema actualiza el estado y retorna HTTP 200

#### Scenario: Carrera inactiva bloquea apertura de cohortes
- **WHEN** se intenta crear o activar una Cohorte cuya Carrera tiene `estado = Inactiva`
- **THEN** el sistema retorna HTTP 422 con mensaje descriptivo

### Requirement: ABM de Carrera requiere permiso `estructura:gestionar`
El sistema SHALL proteger todos los endpoints de escritura (POST, PATCH, DELETE) de Carrera con el guard `require_permission("estructura:gestionar")`. Solo usuarios con ese permiso activo pueden crear, modificar o eliminar carreras.

#### Scenario: Usuario sin permiso no puede crear carrera
- **WHEN** un usuario sin permiso `estructura:gestionar` hace POST a `/api/admin/carreras`
- **THEN** el sistema retorna HTTP 403

#### Scenario: ADMIN puede crear carrera
- **WHEN** un ADMIN con permiso `estructura:gestionar` hace POST a `/api/admin/carreras` con datos válidos
- **THEN** el sistema crea la Carrera y retorna HTTP 201 con el recurso creado

### Requirement: Carrera está aislada por tenant
El sistema SHALL filtrar todas las consultas de Carrera por `tenant_id` derivado del JWT del usuario autenticado. Un usuario de un tenant no puede ver ni modificar carreras de otro tenant.

#### Scenario: Listado de carreras retorna solo las del tenant del usuario
- **WHEN** un ADMIN hace GET a `/api/admin/carreras`
- **THEN** el sistema retorna únicamente las carreras cuyo `tenant_id` coincide con el tenant del usuario autenticado

#### Scenario: Acceso a carrera de otro tenant retorna 404
- **WHEN** un usuario intenta hacer GET/PATCH/DELETE a una Carrera que pertenece a un tenant diferente al del usuario
- **THEN** el sistema retorna HTTP 404 (no expone la existencia del recurso)

### Requirement: Carrera soporta soft delete
El sistema SHALL marcar las Carreras como eliminadas (`deleted_at` no nulo) en lugar de borrarlas físicamente. Las carreras eliminadas no aparecen en los listados normales.

#### Scenario: Eliminar carrera la marca con deleted_at
- **WHEN** un ADMIN hace DELETE a una Carrera existente
- **THEN** el sistema setea `deleted_at` con la fecha/hora actual y retorna HTTP 204

#### Scenario: Carrera eliminada no aparece en el listado
- **WHEN** un ADMIN hace GET a `/api/admin/carreras` después de eliminar una carrera
- **THEN** la carrera eliminada no aparece en los resultados
