---
capability: totp-2fa
status: draft
---

# TOTP 2FA

## ADDED Requirements

### Requirement: TOTP enrollment

The system SHALL support optional TOTP enrollment per user. When a user requests enrollment, the system SHALL generate a TOTP secret, return an `otpauth://` URI for QR code display, and store the encrypted secret in the database.

#### Scenario: User enrolls in TOTP
- **WHEN** an authenticated user with a verified password requests TOTP enrollment
- **THEN** the system SHALL generate a TOTP secret, persist it AES-256 encrypted in the `user_2fa_secrets` table, and return an `otpauth://totp/<issuer>:<username>?secret=<encoded>&issuer=<issuer>` URI

#### Scenario: Enrollment re-request overwrites existing secret
- **WHEN** a user who already has a TOTP secret requests enrollment again
- **THEN** the system SHALL generate a new TOTP secret, overwrite the stored encrypted secret, and return the new `otpauth://` URI

### Requirement: TOTP verification

The system SHALL verify a submitted TOTP code against the user's stored secret. Upon successful verification it SHALL mark 2FA as enabled for the user.

#### Scenario: Valid TOTP code enables 2FA
- **WHEN** the user submits a valid TOTP code along with a temporary session token
- **THEN** the system SHALL verify the code against the stored secret using TOTP (RFC 6238) with a time-step window of ±1, mark `user_2fa_secrets.enabled = true`, and issue a full session token

#### Scenario: Invalid TOTP code is rejected
- **WHEN** the user submits an invalid or expired TOTP code
- **THEN** the system SHALL return a 401 error with `code: "INVALID_TOTP"` and SHALL NOT enable 2FA or issue a session token

### Requirement: Login with 2FA gate

After successful password validation, if the user has 2FA enabled, the system SHALL return a temporary session token instead of a full session. The login SHALL complete only after successful TOTP verification.

#### Scenario: 2FA-enabled user receives temp token after password
- **WHEN** a user with 2FA enabled submits correct credentials
- **THEN** the system SHALL NOT issue a full session token; it SHALL return HTTP 200 with `requires_2fa: true` and a short-lived temporary session token (TTL 5 minutes)

#### Scenario: Full login follows successful TOTP
- **WHEN** the user submits the temporary token and a valid TOTP code to the verification endpoint
- **THEN** the system SHALL issue a full session token (access + refresh) and SHALL mark the session as 2FA-verified in the session record

#### Scenario: Temp token expires before verification
- **WHEN** the user does not complete TOTP verification within 5 minutes of receiving the temporary token
- **THEN** the system SHALL reject the expired temporary token with a 401 error and SHALL require the user to re-authenticate with credentials

### Requirement: Login without 2FA

If the user does not have 2FA enabled, the login SHALL complete normally in a single step without requiring any additional verification.

#### Scenario: Login completes in one step when 2FA is disabled
- **WHEN** a user without 2FA enabled submits correct credentials
- **THEN** the system SHALL issue a full session token (access + refresh) directly, without requiring any temporary token or TOTP verification
