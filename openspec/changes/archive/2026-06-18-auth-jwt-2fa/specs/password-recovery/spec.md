# Password Recovery

Flujo forgot/reset con token de un solo uso, expiración corta, invalidación post-uso.

## ADDED Requirements

### Requirement: Forgot Password
The system SHALL generate a single-use UUID token upon user request, store its SHA-256 hash in the `password_recovery_token` table with a 15-minute expiration window, and return the raw token to the caller. The system MUST validate that the email exists before issuing a token. The raw token SHALL NOT be persisted — only its hash.

#### Scenario: Successful forgot request returns a raw token
- **WHEN** an unauthenticated user POSTs a forgot-password request with a valid registered email
- **THEN** the system SHALL return `201 Created` with a JSON body containing a `token` field (the raw UUID), SHALL store the SHA-256 hash of that token in `password_recovery_token` with `used=false` and `expires_at = now() + 15 minutes`, and SHALL return the raw token in the response body

#### Scenario: Forgot request with unregistered email is rejected
- **WHEN** an unauthenticated user POSTs a forgot-password request with an email that does not exist in the `users` table
- **THEN** the system SHALL return `404 Not Found` and SHALL NOT create any `password_recovery_token` row

#### Scenario: Forgot request invalidates any previous unused token for the same user
- **WHEN** a user requests a second forgot-password before using the first token
- **THEN** the system SHALL mark the previous unused token as `used=true` before creating the new one

### Requirement: Reset Password
The system SHALL accept a raw token and a new password, validate the token is not expired and not previously used, update the user's password hash with Argon2id, and mark the token as used. All operations SHALL be atomic within a single database transaction.

#### Scenario: Successful reset with valid token and new password
- **WHEN** an unauthenticated user POSTs a reset-password request with a valid raw token and a new password meeting policy requirements
- **THEN** the system SHALL update the user's `password_hash` using Argon2id, SHALL set `used=true` on the matching `password_recovery_token` row, and SHALL return `200 OK`

#### Scenario: Reset with mismatched token hash is rejected
- **WHEN** an unauthenticated user POSTs a reset-password request with a raw token whose SHA-256 hash does not match any row in `password_recovery_token`
- **THEN** the system SHALL return `404 Not Found` and SHALL NOT modify any user record

### Requirement: Token Expiration
The system MUST reject any recovery token whose `expires_at` timestamp is in the past, regardless of whether it has been used or not.

#### Scenario: Expired token is rejected on reset
- **WHEN** an unauthenticated user POSTs a reset-password request with a raw token whose SHA-256 hash matches a row where `expires_at < now()`
- **THEN** the system SHALL return `410 Gone` and SHALL NOT update the password hash

### Requirement: Token Single-Use
A recovery token SHALL be usable exactly once. Once marked as `used=true`, the system MUST reject any subsequent reset attempt with that same token.

#### Scenario: Already-used token is rejected on subsequent attempt
- **WHEN** an unauthenticated user POSTs a reset-password request with a raw token whose SHA-256 hash matches a row where `used=true`
- **THEN** the system SHALL return `410 Gone` and SHALL NOT update the password hash
