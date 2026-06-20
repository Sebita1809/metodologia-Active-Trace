### Requirement: Materia es catálogo único por tenant (ADR-006)
El sistema SHALL mantener un único catálogo de Materias por tenant. Una Materia representa la definición canónica de una unidad académica; cuando la misma materia se dicta en distintas carreras o cohortes, la asociación se modela en `Asignacion` (C-07), no como materias separadas.

#### Scenario: El catálogo de materias no duplica definiciones por carrera
- **WHEN** la misma materia (mismo código) se dicta en dos carreras distintas
- **THEN** existe una única entrada en la tabla `materia` referenciada desde múltiples `Asignacion`

### Requirement: Materia tiene código único por tenant
El sistema SHALL garantizar que el par `(tenant_id, codigo)` sea único. Dos materias dentro del mismo tenant no pueden compartir código.

#### Scenario: Código duplicado dentro del mismo tenant es rechazado
- **WHEN** un ADMIN intenta crear una Materia con un `codigo` ya existente en el mismo tenant
- **THEN** el sistema retorna HTTP 409 con mensaje que indica el conflicto de unicidad

#### Scenario: Código repetido en otro tenant es permitido
- **WHEN** un ADMIN crea una Materia con un `codigo` que ya existe en un tenant diferente
- **THEN** el sistema crea la Materia exitosamente (HTTP 201)

### Requirement: Materia soporta estado activa/inactiva
El sistema SHALL permitir cambiar el estado de una Materia entre `Activa` e `Inactiva`. Las materias inactivas se conservan en el histórico pero no deben ofrecerse en selección para nuevas asignaciones.

#### Scenario: Materia creada como Activa por defecto
- **WHEN** un ADMIN crea una Materia sin especificar estado
- **THEN** la Materia queda con `estado = Activa`

#### Scenario: Materia se puede inactivar
- **WHEN** un ADMIN hace PATCH a una Materia con `estado = Inactiva`
- **THEN** el sistema actualiza el estado y retorna HTTP 200

### Requirement: ABM de Materia requiere permiso `estructura:gestionar`
El sistema SHALL proteger todos los endpoints de escritura (POST, PATCH, DELETE) de Materia con el guard `require_permission("estructura:gestionar")`. Solo usuarios con ese permiso pueden crear, modificar o eliminar materias del catálogo.

#### Scenario: Usuario sin permiso no puede crear materia
- **WHEN** un usuario sin permiso `estructura:gestionar` hace POST a `/api/admin/materias`
- **THEN** el sistema retorna HTTP 403

#### Scenario: ADMIN puede crear materia
- **WHEN** un ADMIN con permiso `estructura:gestionar` hace POST a `/api/admin/materias` con datos válidos
- **THEN** el sistema crea la Materia y retorna HTTP 201 con el recurso creado

### Requirement: Materia está aislada por tenant
El sistema SHALL filtrar todas las consultas de Materia por `tenant_id` derivado del JWT del usuario autenticado. Un usuario de un tenant no puede ver ni modificar materias de otro tenant.

#### Scenario: Listado de materias retorna solo las del tenant del usuario
- **WHEN** un ADMIN hace GET a `/api/admin/materias`
- **THEN** el sistema retorna únicamente las materias cuyo `tenant_id` coincide con el tenant del usuario autenticado

#### Scenario: Acceso a materia de otro tenant retorna 404
- **WHEN** un usuario intenta acceder a una Materia de un tenant diferente al del usuario
- **THEN** el sistema retorna HTTP 404

### Requirement: Materia soporta soft delete
El sistema SHALL marcar las Materias como eliminadas (`deleted_at` no nulo) en lugar de borrarlas físicamente. Las materias eliminadas no aparecen en los listados normales.

#### Scenario: Eliminar materia la marca con deleted_at
- **WHEN** un ADMIN hace DELETE a una Materia existente
- **THEN** el sistema setea `deleted_at` con la fecha/hora actual y retorna HTTP 204

#### Scenario: Materia eliminada no aparece en el listado
- **WHEN** un ADMIN hace GET a `/api/admin/materias` después de eliminar una materia
- **THEN** la materia eliminada no aparece en los resultados

### Requirement: Materia mapea a una clave de categoría de Plus
El sistema SHALL permitir asociar a una Materia una `clave_plus` (string libre, nullable) que la mapea a una clave de categoría de Plus salarial. Las claves son configurables por tenant (PA-22). Una Materia con `clave_plus` nulo no aporta Plus al cálculo de liquidación (RN-33, RN-34).

#### Scenario: Asignar clave_plus a una materia
- **WHEN** un ADMIN con `estructura:gestionar` hace PATCH a una Materia seteando `clave_plus = "PROG"`
- **THEN** el sistema persiste la `clave_plus` y retorna HTTP 200

#### Scenario: Materia sin clave_plus no genera plus
- **WHEN** una Materia tiene `clave_plus = null` y un docente tiene comisiones de esa materia en un período
- **THEN** esas comisiones no aportan Plus al cálculo de la liquidación

#### Scenario: clave_plus es libre y no validada contra catálogo global
- **WHEN** un ADMIN asigna una `clave_plus` que no existe en otros tenants
- **THEN** el sistema acepta el valor sin validarlo contra un catálogo global
