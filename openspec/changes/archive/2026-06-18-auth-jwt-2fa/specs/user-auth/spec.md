## ADDED Requirements

### Requirement: Login with email and password
The system SHALL authenticate a user by validating their email and password against the stored Argon2id hash. On success, the system SHALL issue a JWT access token (15-minute expiry) and a refresh token with rotation support. On failure, the system SHALL increment the rate-limit counter and return 401.

#### Scenario: Successful login emits access and refresh tokens
- **WHEN** a user provides a registered email and the correct password
- **THEN** the system returns a 200 response containing a JWT access token (exp=15 min) and a refresh token; the refresh token is stored in the `refresh_token` table with `revoked_at IS NULL`

#### Scenario: Login with wrong password returns 401
- **WHEN** a user provides a registered email and an incorrect password
- **THEN** the system returns 401 Unauthorized and does NOT create any refresh token

#### Scenario: Login with unregistered email returns 401
- **WHEN** a user provides an email that does not exist in the system
- **THEN** the system returns 401 Unauthorized to prevent email enumeration

### Requirement: Refresh token rotation
The system SHALL accept a valid, non-expired, non-revoked refresh token. Upon validation, the system SHALL revoke that token (set `revoked_at`) and issue a new access token + new refresh token pair. The new refresh token SHALL link to the revoked token via `replaced_by`. If a revoked refresh token is reused, the system SHALL revoke the entire token family (all tokens in the replacement chain) and force re-authentication.

#### Scenario: Successful rotation issues new pair and revokes old
- **WHEN** a client sends a valid non-expired refresh token to the refresh endpoint
- **THEN** the system revokes the old token (`revoked_at` set), inserts a new `refresh_token` row linked via `replaced_by`, and returns a 200 response with a new access token and new refresh token

#### Scenario: Reuse of revoked refresh token invalidates the family
- **WHEN** a client sends a refresh token that has already been revoked
- **THEN** the system revokes ALL tokens in the same family chain and returns 401 Unauthorized; the user MUST re-authenticate with credentials

#### Scenario: Expired refresh token is rejected
- **WHEN** a client sends an expired refresh token
- **THEN** the system returns 401 Unauthorized without modifying token state

### Requirement: Logout
The system SHALL revoke the active refresh token upon logout, rendering it unusable for future refresh or access operations.

#### Scenario: Logout revokes the refresh token
- **WHEN** an authenticated user sends a logout request with a valid refresh token
- **THEN** the system sets `revoked_at` on that token and returns 204 No Content

#### Scenario: Logout with invalid token returns 401
- **WHEN** a user sends a logout request with an expired, revoked, or malformed refresh token
- **THEN** the system returns 401 Unauthorized

### Requirement: Access token verification
The system SHALL verify that an incoming JWT access token has a valid signature, has not expired, and contains the required claims (`sub` = user_id, `tenant_id`, `email`, `type` = "access"). Verification SHALL fail-closed: any invalid or missing claim SHALL cause rejection.

#### Scenario: Valid access token passes verification
- **WHEN** a request includes a JWT access token with valid signature, future `exp`, and all required claims
- **THEN** the system extracts `user_id`, `tenant_id`, and `email` from the token and grants access

#### Scenario: Expired access token is rejected
- **WHEN** a request includes a JWT access token whose `exp` is in the past
- **THEN** the system returns 401 Unauthorized

#### Scenario: Tampered access token is rejected
- **WHEN** a request includes a JWT access token whose signature does not match the payload
- **THEN** the system returns 401 Unauthorized

### Requirement: Current user dependency
The system SHALL provide a FastAPI dependency `get_current_user` that extracts identity (user_id, tenant_id, email) from a verified JWT access token. This dependency SHALL replace the placeholder `get_current_tenant` from C-02. The resolved `tenant_id` SHALL be used by downstream repositories for tenant-scoped queries.

#### Scenario: get_current_user resolves identity and tenant from valid JWT
- **WHEN** a protected endpoint calls `get_current_user`
- **THEN** the dependency verifies the JWT, extracts `user_id`, `tenant_id`, and `email` from claims, and returns a `UserContext` object

#### Scenario: get_current_user rejects request without Authorization header
- **WHEN** a protected endpoint is called without an `Authorization` header
- **THEN** `get_current_user` raises a 401 Unauthorized

#### Scenario: Tenant ID in repository scope comes from JWT
- **WHEN** a repository operation executes with an authenticated user
- **THEN** `tenant_id` SHALL be sourced from `get_current_user` (JWT), not from any request header
