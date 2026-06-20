## ADDED Requirements

### Requirement: Pantalla de login con email y contraseña
El sistema SHALL presentar una pantalla de login con un formulario de email y contraseña validado con React Hook Form + Zod. Al enviar, SHALL llamar a `POST /api/auth/login`. Si la respuesta contiene `access_token` y `refresh_token`, SHALL establecer la sesión y navegar a la aplicación. Si la respuesta indica `requires_2fa: true`, SHALL navegar al gate 2FA conservando el `partial_token`.

#### Scenario: Login exitoso sin 2FA
- **WHEN** el usuario envía credenciales válidas de una cuenta sin 2FA
- **THEN** el frontend recibe el par de tokens, establece la sesión y redirige a la pantalla principal de la app

#### Scenario: Login que requiere 2FA
- **WHEN** el usuario envía credenciales válidas de una cuenta con 2FA activo
- **THEN** el frontend recibe `partial_token` y `requires_2fa: true` y navega a la pantalla de verificación 2FA sin establecer la sesión completa

#### Scenario: Credenciales inválidas
- **WHEN** el backend responde `401` al login
- **THEN** el frontend muestra un mensaje de error genérico (sin revelar si el email existe) y permanece en la pantalla de login

#### Scenario: Validación de formulario
- **WHEN** el usuario intenta enviar el formulario con un email mal formado o la contraseña vacía
- **THEN** el formulario muestra los errores de validación de Zod y NO realiza la llamada al backend

#### Scenario: Bloqueo por rate limit
- **WHEN** el backend responde `429 Too Many Requests` al login
- **THEN** el frontend muestra un mensaje indicando que debe reintentar más tarde

### Requirement: Gate de verificación 2FA TOTP
El sistema SHALL presentar una pantalla de verificación 2FA cuando el login exija segundo factor. SHALL aceptar un código TOTP y llamar a `POST /api/auth/2fa/login-verify` usando el `partial_token`. Si el código es válido, SHALL establecer la sesión completa con el par de tokens recibido.

#### Scenario: Verificación 2FA exitosa
- **WHEN** el usuario ingresa un código TOTP válido en el gate 2FA
- **THEN** el frontend recibe el par de tokens, establece la sesión completa y redirige a la pantalla principal

#### Scenario: Código TOTP inválido
- **WHEN** el backend responde con error de verificación al código TOTP
- **THEN** el frontend muestra un mensaje de error y permite reintentar sin perder el `partial_token` (hasta su expiración)

#### Scenario: Partial token expirado
- **WHEN** el `partial_token` expira o es rechazado
- **THEN** el frontend redirige nuevamente al login para reiniciar el flujo

### Requirement: Solicitud de recuperación de contraseña
El sistema SHALL presentar una pantalla para solicitar la recuperación de contraseña ingresando el email, que llama a `POST /api/auth/forgot`. La pantalla SHALL mostrar siempre el mismo mensaje de confirmación, independientemente de si el email existe.

#### Scenario: Solicitud enviada
- **WHEN** el usuario envía su email en la pantalla de recuperación
- **THEN** el frontend llama a `/api/auth/forgot` y muestra un mensaje genérico de "si el email existe, recibirás instrucciones" sin revelar la existencia de la cuenta

### Requirement: Reset de contraseña con token
El sistema SHALL presentar una pantalla de reset que recibe el token de recuperación (desde el enlace del email) y permite establecer una nueva contraseña, validada con Zod, llamando a `POST /api/auth/reset`.

#### Scenario: Reset exitoso
- **WHEN** el usuario establece una nueva contraseña válida con un token vigente
- **THEN** el frontend llama a `/api/auth/reset`, muestra confirmación y redirige al login

#### Scenario: Token inválido o usado
- **WHEN** el backend responde con error porque el token está expirado o ya fue usado
- **THEN** el frontend muestra un mensaje indicando que el enlace ya no es válido y ofrece volver a solicitar la recuperación

#### Scenario: Validación de la nueva contraseña
- **WHEN** la nueva contraseña no cumple las reglas mínimas o no coincide con su confirmación
- **THEN** el formulario muestra el error de validación y NO llama al backend

### Requirement: Logout
El sistema SHALL ofrecer la acción de cerrar sesión, que llama a `POST /api/auth/logout` para revocar los tokens en el servidor, limpia la sesión local y redirige al login.

#### Scenario: Logout exitoso
- **WHEN** el usuario ejecuta la acción de cerrar sesión
- **THEN** el frontend llama a `/api/auth/logout`, limpia el access y refresh token locales y redirige a la pantalla de login

#### Scenario: Logout con fallo de red
- **WHEN** la llamada a `/api/auth/logout` falla por red
- **THEN** el frontend igualmente limpia la sesión local y redirige al login (no deja al usuario atrapado en sesión)
