## ADDED Requirements

### Requirement: Enrolamiento TOTP
El sistema SHALL permitir a un usuario autenticado iniciar el enrolamiento de 2FA TOTP. SHALL generar un secret aleatorio, cifrarlo con AES-256 antes de persistirlo, y retornar la URI `otpauth://` para que el cliente genere el código QR. El enrolamiento queda PENDIENTE hasta que el usuario confirme con un código TOTP válido.

#### Scenario: Inicio de enrolamiento exitoso
- **WHEN** un usuario autenticado envía `POST /api/auth/2fa/enroll`
- **THEN** el sistema genera un TOTP secret, lo persiste cifrado en `totp_secrets` con `confirmed=false`, y responde `200 OK` con el `otpauth_uri` (compatible con apps TOTP estándar como Google Authenticator)

#### Scenario: Enrolamiento duplicado
- **WHEN** un usuario que ya tiene 2FA confirmado activo envía `POST /api/auth/2fa/enroll`
- **THEN** el sistema responde `409 Conflict` indicando que ya tiene 2FA activo

### Requirement: Confirmación de enrolamiento TOTP
El sistema SHALL verificar que el usuario puede generar códigos TOTP correctos antes de activar el segundo factor. Solo después de la confirmación el 2FA queda activo en la cuenta.

#### Scenario: Confirmación exitosa
- **WHEN** el usuario envía `POST /api/auth/2fa/verify` con un código TOTP válido generado con el secret recién enrolado
- **THEN** el sistema marca `totp_secrets.confirmed = true` y responde `200 OK`; a partir de ese momento el login exigirá 2FA

#### Scenario: Confirmación con código incorrecto
- **WHEN** el usuario envía `POST /api/auth/2fa/verify` con un código TOTP inválido o expirado
- **THEN** el sistema responde `422 Unprocessable Entity` y el enrolamiento sigue PENDIENTE (no activo)

#### Scenario: Confirmación sin enrolamiento previo
- **WHEN** el usuario envía `POST /api/auth/2fa/verify` sin haber iniciado el enrolamiento
- **THEN** el sistema responde `400 Bad Request`

### Requirement: Gate de 2FA en el flujo de login
El sistema SHALL exigir la verificación TOTP como paso intermedio cuando el usuario tiene 2FA activo. El `partial_token` emitido tras las credenciales válidas es el único token aceptado por el endpoint de gate; no da acceso a ningún otro recurso.

#### Scenario: Verificación TOTP exitosa en gate de login
- **WHEN** el cliente envía `POST /api/auth/2fa/login-verify` con un `partial_token` válido (scope `"2fa_pending"`) y un código TOTP correcto
- **THEN** el sistema responde `200 OK` con `access_token` y `refresh_token` (sesión completa)

#### Scenario: Código TOTP incorrecto en gate de login
- **WHEN** el cliente envía `POST /api/auth/2fa/login-verify` con `partial_token` válido pero código TOTP incorrecto
- **THEN** el sistema responde `401 Unauthorized`; el `partial_token` sigue válido hasta que expire

#### Scenario: `partial_token` expirado en gate de login
- **WHEN** el cliente envía `POST /api/auth/2fa/login-verify` con un `partial_token` expirado (TTL 5 min superado)
- **THEN** el sistema responde `401 Unauthorized`; el usuario debe relanzar el login completo

#### Scenario: `partial_token` rechazado en endpoints no-2FA
- **WHEN** cualquier handler protegido diferente de `2fa/login-verify` recibe un `partial_token`
- **THEN** el sistema responde `401 Unauthorized` (el scope `"2fa_pending"` no es válido fuera del gate)
