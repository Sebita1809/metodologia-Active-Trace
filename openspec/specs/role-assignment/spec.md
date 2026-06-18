## ADDED Requirements

### Requirement: Asignacion — Crear

El sistema SHALL permitir asignar un rol a un usuario dentro de un contexto académico con vigencia.

#### Scenario: Crear asignación con datos válidos
- **WHEN** un usuario con permiso `equipos:asignar` envía una solicitud POST a `/api/asignaciones` con `usuario_id`, `rol`, `materia_id`, `carrera_id`, `cohorte_id`, `desde` y `hasta` válidos
- **THEN** el sistema SHALL crear la asignación y retornar 201 con los datos completos incluyendo `estado_vigencia` derivado

#### Scenario: Crear asignación sin contexto académico (rol global)
- **WHEN** un usuario con permiso `equipos:asignar` envía una solicitud POST a `/api/asignaciones` con un `rol` global (ADMIN, FINANZAS) y sin `materia_id`, `carrera_id` ni `cohorte_id`
- **THEN** el sistema SHALL crear la asignación y retornar 201

#### Scenario: Crear asignación para usuario inactivo
- **WHEN** un usuario con permiso `equipos:asignar` envía una solicitud POST a `/api/asignaciones` con `usuario_id` de un usuario inactivo
- **THEN** el sistema SHALL retornar 422 indicando que el usuario no está activo

#### Scenario: Crear asignación con `desde` posterior a `hasta`
- **WHEN** un usuario envía una solicitud POST a `/api/asignaciones` con `desde` posterior a `hasta`
- **THEN** el sistema SHALL retornar 422 indicando que el rango de fechas es inválido

#### Scenario: Crear asignación con responsable de distinto tenant
- **WHEN** un usuario envía una solicitud POST a `/api/asignaciones` con `responsable_id` de un usuario de otro tenant
- **THEN** el sistema SHALL retornar 422 indicando que el responsable no existe en el tenant

---

### Requirement: Asignacion — Leer

El sistema SHALL permitir consultar asignaciones por ID y listar asignaciones del tenant con filtros.

#### Scenario: Obtener asignación por ID
- **WHEN** un usuario con permiso `equipos:asignar` envía una solicitud GET a `/api/asignaciones/{id}` con un UUID válido
- **THEN** el sistema SHALL retornar 200 con los datos incluyendo `estado_vigencia` calculado

#### Scenario: Listar asignaciones por usuario
- **WHEN** un usuario envía una solicitud GET a `/api/asignaciones?usuario_id={uuid}`
- **THEN** el sistema SHALL retornar 200 con la lista de asignaciones de ese usuario en el tenant

#### Scenario: Listar asignaciones por materia
- **WHEN** un usuario envía una solicitud GET a `/api/asignaciones?materia_id={uuid}`
- **THEN** el sistema SHALL retornar 200 con las asignaciones de esa materia en el tenant

#### Scenario: Listar solo asignaciones vigentes
- **WHEN** un usuario envía una solicitud GET a `/api/asignaciones?solo_vigentes=true`
- **THEN** el sistema SHALL retornar solo las asignaciones con `desde <= hoy AND (hasta IS NULL OR hasta >= hoy)`

#### Scenario: Obtener asignación de otro tenant
- **WHEN** un usuario envía una solicitud GET a `/api/asignaciones/{id}` con un UUID de otro tenant
- **THEN** el sistema SHALL retornar 404 Not Found

---

### Requirement: Asignacion — Actualizar

El sistema SHALL permitir modificar una asignación existente.

#### Scenario: Extender vigencia de asignación
- **WHEN** un usuario con permiso `equipos:asignar` envía una solicitud PATCH a `/api/asignaciones/{id}` actualizando `hasta` a una fecha posterior
- **THEN** el sistema SHALL actualizar la asignación y retornar 200

#### Scenario: Cambiar responsable de asignación
- **WHEN** un usuario envía una solicitud PATCH a `/api/asignaciones/{id}` con un nuevo `responsable_id`
- **THEN** el sistema SHALL actualizar el responsable y retornar 200

#### Scenario: Asignación vencida no se puede modificar
- **WHEN** un usuario envía una solicitud PATCH a `/api/asignaciones/{id}` sobre una asignación ya vencida (`hasta` < hoy)
- **THEN** el sistema SHALL permitir la modificación (la asignación vencida sigue siendo un registro editable — decisión de diseño)

---

### Requirement: Asignacion — Eliminar (soft delete)

El sistema SHALL permitir eliminar lógicamente una asignación.

#### Scenario: Eliminar asignación vigente
- **WHEN** un usuario con permiso `equipos:asignar` envía una solicitud DELETE a `/api/asignaciones/{id}` sobre una asignación vigente
- **THEN** el sistema SHALL marcar `deleted_at` y retornar 204 No Content

#### Scenario: Eliminar asignación ya vencida
- **WHEN** un usuario envía una solicitud DELETE a `/api/asignaciones/{id}` sobre una asignación vencida
- **THEN** el sistema SHALL marcar `deleted_at` y retornar 204 No Content (el histórico se puede borrar igual que una vigente)

---

### Requirement: Vigencia — Cálculo de estado_vigencia

Toda asignación SHALL exponer un campo `estado_vigencia` derivado calculado en tiempo de consulta.

#### Scenario: Asignación con `hasta` futuro es vigente
- **WHEN** se consulta una asignación con `desde <= CURRENT_DATE` y `hasta >= CURRENT_DATE`
- **THEN** el campo `estado_vigencia` SHALL ser `"vigente"`

#### Scenario: Asignación sin `hasta` (abierta) es vigente
- **WHEN** se consulta una asignación con `hasta IS NULL` y `desde <= CURRENT_DATE`
- **THEN** el campo `estado_vigencia` SHALL ser `"vigente"`

#### Scenario: Asignación con `hasta` anterior a hoy es vencida
- **WHEN** se consulta una asignación con `hasta < CURRENT_DATE`
- **THEN** el campo `estado_vigencia` SHALL ser `"vencida"`

#### Scenario: Asignación con `desde` futuro es no vigente
- **WHEN** se consulta una asignación con `desde > CURRENT_DATE`
- **THEN** el campo `estado_vigencia` SHALL ser `"vencida"` (aún no iniciada)

---

### Requirement: Jerarquía — Cadena de supervisión

El sistema SHALL permitir modelar una relación jerárquica entre usuarios a través de `responsable_id`.

#### Scenario: Asignación con responsable
- **WHEN** se crea una asignación con `responsable_id` válido
- **THEN** el sistema SHALL registrar la relación jerárquica y retornarla en la respuesta

#### Scenario: Responsable de otro tenant es rechazado
- **WHEN** se crea una asignación con `responsable_id` de un usuario de otro tenant
- **THEN** el sistema SHALL retornar 422

---

### Requirement: Multi-tenancy — Aislamiento entre tenants

Todas las operaciones sobre asignaciones SHALL respetar el tenant del usuario autenticado.

#### Scenario: Usuario de tenant A no ve asignaciones de tenant B
- **WHEN** un usuario del tenant A consulta asignaciones
- **THEN** el sistema SHALL retornar exclusivamente las asignaciones con `tenant_id = tenant_A`

#### Scenario: Asignación referenciando usuario de otro tenant es rechazada
- **WHEN** un usuario del tenant A intenta crear una asignación para un `usuario_id` del tenant B
- **THEN** el sistema SHALL retornar 404 (el usuario no existe en el scope del tenant)
