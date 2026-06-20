## ADDED Requirements

### Requirement: Login con credenciales email + password
El sistema SHALL validar el email y la contraseña del usuario contra el registro del tenant. Si las credenciales son válidas y el usuario no tiene 2FA activo, SHALL emitir un par de tokens (access + refresh). Si el usuario tiene 2FA activo, SHALL emitir un `partial_token` en lugar del par completo.

#### Scenario: Login exitoso sin 2FA
- **WHEN** el cliente envía `POST /api/auth/login` con email y contraseña válidos y el usuario no tiene 2FA activo
- **THEN** el sistema responde `200 OK` con `access_token` (JWT, 15 min), `refresh_token` (opaco, 7 días) y `token_type: "bearer"`

#### Scenario: Login exitoso con 2FA activo
- **WHEN** el cliente envía `POST /api/auth/login` con email y contraseña válidos y el usuario tiene 2FA confirmado activo
- **THEN** el sistema responde `200 OK` con `partial_token` (JWT scope `"2fa_pending"`, TTL 5 min) y `requires_2fa: true`; NO emite access_token ni refresh_token

#### Scenario: Login fallido por contraseña incorrecta
- **WHEN** el cliente envía `POST /api/auth/login` con un email existente y contraseña incorrecta
- **THEN** el sistema responde `401 Unauthorized` con mensaje genérico (sin indicar si el email existe)

#### Scenario: Login fallido por email inexistente
- **WHEN** el cliente envía `POST /api/auth/login` con un email que no existe en el tenant
- **THEN** el sistema responde `401 Unauthorized` con el mismo mensaje genérico que contraseña incorrecta (sin distinguir el caso)

#### Scenario: Login bloqueado por rate limit
- **WHEN** el mismo par IP + email realiza 5 intentos de login en 60 segundos
- **THEN** el sexto intento dentro de la ventana responde `429 Too Many Requests` con header `Retry-After`

### Requirement: JWT con claims mínimos
El sistema SHALL incluir en el access token únicamente los claims: `sub` (UUID del usuario), `tenant_id` (UUID del tenant), `roles` (lista de strings), `exp` (timestamp de expiración). El token SHALL estar firmado con HS256 usando `SECRET_KEY`.

#### Scenario: Claims del access token
- **WHEN** se emite un access token tras login exitoso
- **THEN** el token decodificado contiene `sub`, `tenant_id`, `roles` y `exp`; no contiene permisos ni datos sensibles

#### Scenario: Access token expirado rechazado
- **WHEN** un handler protegido recibe un access token cuya `exp` ya pasó
- **THEN** el sistema responde `401 Unauthorized`

### Requirement: Refresh token con rotación
El sistema SHALL almacenar el refresh token como `SHA-256(token_value)` en la tabla `refresh_tokens`. Al usar un refresh token válido SHALL emitir un nuevo par y revocar el anterior en la misma transacción.

#### Scenario: Rotación exitosa del refresh token
- **WHEN** el cliente envía `POST /api/auth/refresh` con un refresh token válido y no revocado
- **THEN** el sistema responde `200 OK` con nuevo `access_token` y nuevo `refresh_token`; el refresh token anterior queda marcado como revocado

#### Scenario: Reuso de refresh token revocado detectado
- **WHEN** el cliente envía `POST /api/auth/refresh` con un refresh token que ya fue revocado
- **THEN** el sistema revoca TODOS los refresh tokens activos del usuario en ese tenant y responde `401 Unauthorized`

#### Scenario: Refresh token expirado rechazado
- **WHEN** el cliente envía `POST /api/auth/refresh` con un refresh token cuyo `expires_at` ya pasó
- **THEN** el sistema responde `401 Unauthorized`

### Requirement: Logout y revocación de sesión
El sistema SHALL permitir al usuario autenticado invalidar su sesión activa revocando el refresh token.

#### Scenario: Logout exitoso
- **WHEN** el cliente envía `POST /api/auth/logout` con un access token válido (y opcionalmente el refresh token en el body)
- **THEN** el sistema revoca el refresh token asociado a la sesión y responde `200 OK`

#### Scenario: Logout con sesión ya revocada
- **WHEN** el cliente envía `POST /api/auth/logout` con un refresh token ya revocado
- **THEN** el sistema responde `200 OK` (idempotente — no es un error)
