## ADDED Requirements

### Requirement: Usuario autenticado puede leer su propio perfil
El sistema SHALL exponer `GET /api/perfil` para que cualquier usuario autenticado obtenga su propia ficha de `Usuario`. La identidad del usuario SHALL resolverse exclusivamente desde el JWT (`current_user.user_id`); ningún parámetro de path, body o header puede seleccionar otra ficha. Los campos de PII (email, dni, cuil, cbu, alias_cbu) se retornan descifrados; `email_hash` NUNCA se incluye.

#### Scenario: Usuario obtiene su propia ficha
- **WHEN** un usuario autenticado hace GET a `/api/perfil`
- **THEN** el sistema retorna HTTP 200 con la ficha del usuario cuyo `id` coincide con el `user_id` del JWT

#### Scenario: Petición sin token es rechazada
- **WHEN** se hace GET a `/api/perfil` sin token de autenticación
- **THEN** el sistema retorna HTTP 401

#### Scenario: La respuesta no expone email_hash
- **WHEN** un usuario autenticado hace GET a `/api/perfil`
- **THEN** la respuesta no incluye el campo `email_hash`

### Requirement: Usuario autenticado puede editar los campos editables de su perfil
El sistema SHALL exponer `PATCH /api/perfil` para que el usuario autenticado edite su propia ficha. Los campos editables SHALL ser: `nombre`, `apellidos`, `email`, `sexo`, `banco`, `cbu`, `alias_cbu`, `regional`, `legajo_profesional` y `modalidad_cobro`. La identidad se resuelve desde el JWT; el usuario solo puede editarse a sí mismo. Los campos de PII editados se cifran antes de persistir.

#### Scenario: Usuario actualiza sus datos bancarios
- **WHEN** un usuario autenticado hace PATCH a `/api/perfil` con `cbu` y `alias_cbu` nuevos
- **THEN** el sistema persiste los valores cifrados y retorna HTTP 200 con la ficha actualizada

#### Scenario: Usuario actualiza su modalidad de cobro
- **WHEN** un usuario autenticado hace PATCH a `/api/perfil` con `modalidad_cobro = "Factura"`
- **THEN** el sistema actualiza el campo y retorna HTTP 200

#### Scenario: La edición afecta solo a la ficha del solicitante
- **WHEN** un usuario autenticado hace PATCH a `/api/perfil`
- **THEN** el sistema modifica únicamente la ficha cuyo `id` coincide con el `user_id` del JWT, sin aceptar ningún identificador de usuario desde la petición

### Requirement: El CUIL es de solo lectura desde la autogestión de perfil
El sistema SHALL impedir la modificación del campo `cuil` a través de `PATCH /api/perfil`. El schema de actualización NO declara el campo `cuil`, por lo que enviarlo SHALL ser rechazado (campo no permitido). El `cuil` SHALL retornarse descifrado en `GET /api/perfil` como dato de solo lectura.

#### Scenario: Intento de editar CUIL por el perfil propio es rechazado
- **WHEN** un usuario autenticado hace PATCH a `/api/perfil` incluyendo el campo `cuil`
- **THEN** el sistema retorna HTTP 422 (campo no permitido) y no modifica el CUIL almacenado

#### Scenario: El CUIL se muestra como solo lectura
- **WHEN** un usuario autenticado hace GET a `/api/perfil`
- **THEN** la respuesta incluye el `cuil` descifrado, y no existe forma de modificarlo por este endpoint

### Requirement: La autogestión de perfil está aislada por tenant
El sistema SHALL garantizar que la lectura y edición del perfil propio operen sobre el `tenant_id` derivado del JWT. Un usuario nunca puede leer ni modificar una ficha de otro tenant a través de `/api/perfil`.

#### Scenario: El perfil resuelto pertenece al tenant del JWT
- **WHEN** un usuario autenticado accede a `/api/perfil`
- **THEN** el sistema retorna la ficha cuyo `tenant_id` coincide con el del JWT

### Requirement: Cierre de sesión explícito (F11.3)
El sistema SHALL permitir que el usuario autenticado cierre su sesión de forma explícita reutilizando `POST /api/auth/logout` (C-03), que revoca el refresh token activo. No se introduce lógica de logout nueva en esta capacidad.

#### Scenario: Logout revoca el refresh token
- **WHEN** un usuario autenticado hace POST a `/api/auth/logout` con su refresh token
- **THEN** el sistema revoca el token y posteriores intentos de refresh con ese token son rechazados con HTTP 401
