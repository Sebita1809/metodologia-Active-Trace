## ADDED Requirements

### Requirement: Solicitud de recuperación de contraseña
El sistema SHALL permitir a un usuario no autenticado iniciar el flujo de recuperación indicando su email. SHALL generar un token de un solo uso, hashearlo con SHA-256 antes de persistirlo en `password_reset_tokens`, y notificar al usuario (por log/evento en este change; email real en C-12). La respuesta es siempre la misma independientemente de si el email existe o no.

#### Scenario: Solicitud para email existente
- **WHEN** el cliente envía `POST /api/auth/forgot` con un email que pertenece a un usuario del tenant
- **THEN** el sistema genera un token, lo persiste hasheado con TTL 15 min, emite el evento de notificación y responde `200 OK` con mensaje genérico

#### Scenario: Solicitud para email inexistente
- **WHEN** el cliente envía `POST /api/auth/forgot` con un email que no existe
- **THEN** el sistema responde `200 OK` con el mismo mensaje genérico (sin revelar si el email existe)

#### Scenario: Token previo pendiente
- **WHEN** el cliente solicita recuperación para un email que ya tiene un token válido no usado
- **THEN** el sistema invalida el token anterior, genera uno nuevo y responde `200 OK`

### Requirement: Reset de contraseña con token de un solo uso
El sistema SHALL permitir al usuario establecer una nueva contraseña presentando el token de recuperación. Una vez usado, el token SHALL quedar marcado como consumido y no podrá reutilizarse. La nueva contraseña SHALL hashearse con Argon2id.

#### Scenario: Reset exitoso
- **WHEN** el cliente envía `POST /api/auth/reset` con un token válido, no usado, no expirado y una nueva contraseña
- **THEN** el sistema actualiza la contraseña hasheada con Argon2id, marca el token como usado (`used_at = now()`) y responde `200 OK`

#### Scenario: Reutilización de token ya consumido
- **WHEN** el cliente envía `POST /api/auth/reset` con un token que ya fue usado
- **THEN** el sistema responde `400 Bad Request`

#### Scenario: Token expirado
- **WHEN** el cliente envía `POST /api/auth/reset` con un token cuyo `expires_at` ya pasó (TTL 15 min)
- **THEN** el sistema responde `400 Bad Request`

#### Scenario: Token inexistente
- **WHEN** el cliente envía `POST /api/auth/reset` con un token que no existe en el sistema
- **THEN** el sistema responde `400 Bad Request` con el mismo mensaje que token expirado (sin distinguir el caso)

#### Scenario: Reset invalida sesiones activas
- **WHEN** el reset de contraseña se completa exitosamente
- **THEN** todos los refresh tokens activos del usuario en ese tenant quedan revocados (forzar re-login)
