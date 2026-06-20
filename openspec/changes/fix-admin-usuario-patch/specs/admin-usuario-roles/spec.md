## ADDED Requirements

### Requirement: Backend UsuarioResponse includes roles array
The GET /api/admin/usuarios and GET /api/admin/usuarios/{id} responses MUST include a `roles` array with the user's asignaciones. Each role entry MUST include: rol name, materia context (if applicable), and vigencia.

#### Scenario: List usuarios returns roles
- **WHEN** the client calls GET /api/admin/usuarios
- **THEN** each usuario in the response MUST include a `roles` array with all active role assignments from the Asignacion table

#### Scenario: Get single usuario returns roles
- **WHEN** the client calls GET /api/admin/usuarios/{id}
- **THEN** the response MUST include a `roles` array with all active role assignments

#### Scenario: Role entry contains required fields
- **WHEN** the response includes a role entry
- **THEN** each entry MUST contain `rol` (string), `materia` (string or null), and `vigencia` (date or null)

### Requirement: Backend PATCH treats empty strings as null for CBU/alias/modalidad
When the backend receives an empty string `""` for `cbu`, `alias_cbu`, or `modalidad_cobro`, it MUST treat it as if the field was not sent — no update is performed on that field.

#### Scenario: PATCH with empty cbu does not update cbu
- **WHEN** the client sends PATCH /api/admin/usuarios/{id} with `{"cbu": ""}`
- **THEN** the `cbu` field MUST NOT be modified and the existing value MUST be preserved

#### Scenario: PATCH with empty alias_cbu does not update alias
- **WHEN** the client sends PATCH /api/admin/usuarios/{id} with `{"alias_cbu": ""}`
- **THEN** the `alias_cbu` field MUST NOT be modified and the existing value MUST be preserved

#### Scenario: PATCH with empty modalidad_cobro does not update modalidad
- **WHEN** the client sends PATCH /api/admin/usuarios/{id} with `{"modalidad_cobro": ""}`
- **THEN** the `modalidad_cobro` field MUST NOT be modified and the existing value MUST be preserved

#### Scenario: PATCH with all three empty preserves all fields
- **WHEN** the client sends PATCH /api/admin/usuarios/{id} with `{"cbu": "", "alias_cbu": "", "modalidad_cobro": ""}`
- **THEN** none of those three fields MUST be modified and existing values MUST be preserved

### Requirement: Frontend user table displays roles
The admin user table MUST show the user's current role(s) in a dedicated column.

#### Scenario: User table has roles column
- **WHEN** the admin user table renders
- **THEN** each row MUST display a roles column showing the user's role(s) as badges or tags

#### Scenario: Multiple roles shown in table
- **WHEN** a user has more than one role
- **THEN** all roles MUST be visible in the roles column

### Requirement: Frontend edit form shows read-only roles
The edit user form MUST display the user's current role(s). The role field SHALL be read-only because role management is handled via the equipos feature.

#### Scenario: Edit form displays roles
- **WHEN** the edit user form opens
- **THEN** the user's current role(s) MUST be displayed

#### Scenario: Roles are read-only in edit form
- **WHEN** the edit user form is submitted
- **THEN** the roles field MUST NOT be sent in the PATCH payload

### Requirement: Frontend CBU/alias/modalidad submission accepts empty values
The form MUST allow submission when `cbu`, `alias_cbu`, and `modalidad_cobro` are empty or null. Empty values MUST be sent as `null`, not as empty string.

#### Scenario: Form submits with empty CBU fields
- **WHEN** the user submits the form with `cbu`, `alias_cbu`, and `modalidad_cobro` left empty
- **THEN** the submission MUST succeed and those fields MUST be sent as `null` in the payload

#### Scenario: Form does not block on empty optional financial fields
- **WHEN** the user tries to submit the form with empty `cbu`, `alias_cbu`, or `modalidad_cobro`
- **THEN** no validation error MUST block the submission due to those fields being empty
