### Requirement: Cohorte tiene nombre único por tenant y carrera
El sistema SHALL garantizar que el triplete `(tenant_id, carrera_id, nombre)` sea único. No pueden existir dos cohortes con el mismo nombre dentro de la misma carrera y tenant.

#### Scenario: Nombre duplicado en la misma carrera del mismo tenant es rechazado
- **WHEN** un ADMIN intenta crear una Cohorte con un `nombre` ya existente para la misma `carrera_id` y `tenant_id`
- **THEN** el sistema retorna HTTP 409 con mensaje que indica el conflicto de unicidad

#### Scenario: El mismo nombre en carreras distintas del mismo tenant es permitido
- **WHEN** un ADMIN crea una Cohorte con `nombre = "MAR-2026"` en una carrera diferente que ya tiene una cohorte con ese nombre
- **THEN** el sistema crea la Cohorte exitosamente (HTTP 201)

### Requirement: Cohorte no puede ser Activa si su Carrera es Inactiva
El sistema SHALL impedir que una Cohorte tenga `estado = Activa` cuando su Carrera asociada tiene `estado = Inactiva`. Esto aplica tanto al crear una nueva Cohorte como al reactivar una existente.

#### Scenario: Crear cohorte activa sobre carrera inactiva es rechazado
- **WHEN** un ADMIN intenta crear una Cohorte con `estado = Activa` referenciando una Carrera con `estado = Inactiva`
- **THEN** el sistema retorna HTTP 422 con mensaje indicando que la carrera está inactiva

#### Scenario: Reactivar cohorte sobre carrera inactiva es rechazado
- **WHEN** un ADMIN intenta hacer PATCH a una Cohorte inactiva para setear `estado = Activa`, y su Carrera tiene `estado = Inactiva`
- **THEN** el sistema retorna HTTP 422 con mensaje descriptivo

#### Scenario: Crear cohorte activa sobre carrera activa es permitido
- **WHEN** un ADMIN crea una Cohorte con `estado = Activa` referenciando una Carrera con `estado = Activa`
- **THEN** el sistema crea la Cohorte exitosamente (HTTP 201)

### Requirement: Cohorte tiene vigencia temporal (vig_desde / vig_hasta)
El sistema SHALL registrar el rango de vigencia de cada Cohorte. `vig_hasta` puede ser nulo (cohorte abierta sin fecha de cierre). El estado derivado `Activa/Inactiva` es el campo funcional; la vigencia es informativa.

#### Scenario: Cohorte creada sin vig_hasta queda abierta
- **WHEN** un ADMIN crea una Cohorte sin especificar `vig_hasta`
- **THEN** la Cohorte se crea con `vig_hasta = null`

#### Scenario: Cohorte con vig_hasta anterior a vig_desde es rechazada
- **WHEN** un ADMIN intenta crear una Cohorte con `vig_hasta` anterior a `vig_desde`
- **THEN** el sistema retorna HTTP 422 con mensaje de validación

### Requirement: ABM de Cohorte requiere permiso `estructura:gestionar`
El sistema SHALL proteger todos los endpoints de escritura (POST, PATCH, DELETE) de Cohorte con el guard `require_permission("estructura:gestionar")`. La lectura puede ser consultada por roles que necesitan el catálogo.

#### Scenario: Usuario sin permiso no puede crear cohorte
- **WHEN** un usuario sin permiso `estructura:gestionar` hace POST a `/api/admin/cohortes`
- **THEN** el sistema retorna HTTP 403

#### Scenario: ADMIN puede crear cohorte válida
- **WHEN** un ADMIN con permiso `estructura:gestionar` hace POST a `/api/admin/cohortes` con datos válidos y carrera activa
- **THEN** el sistema crea la Cohorte y retorna HTTP 201 con el recurso creado

### Requirement: Cohorte está aislada por tenant
El sistema SHALL filtrar todas las consultas de Cohorte por `tenant_id` derivado del JWT del usuario autenticado.

#### Scenario: Listado de cohortes retorna solo las del tenant del usuario
- **WHEN** un ADMIN hace GET a `/api/admin/cohortes`
- **THEN** el sistema retorna únicamente las cohortes cuyo `tenant_id` coincide con el tenant del usuario autenticado

#### Scenario: Acceso a cohorte de otro tenant retorna 404
- **WHEN** un usuario intenta acceder a una Cohorte de un tenant diferente
- **THEN** el sistema retorna HTTP 404

### Requirement: Cohorte soporta soft delete
El sistema SHALL marcar las Cohortes como eliminadas (`deleted_at` no nulo) en lugar de borrarlas físicamente.

#### Scenario: Eliminar cohorte la marca con deleted_at
- **WHEN** un ADMIN hace DELETE a una Cohorte existente
- **THEN** el sistema setea `deleted_at` y retorna HTTP 204

#### Scenario: Cohorte eliminada no aparece en el listado
- **WHEN** un ADMIN hace GET a `/api/admin/cohortes` después de eliminar una cohorte
- **THEN** la cohorte eliminada no aparece en los resultados
