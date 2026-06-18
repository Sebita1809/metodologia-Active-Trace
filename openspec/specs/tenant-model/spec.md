## ADDED Requirements

### Requirement: Tenant entity
The system SHALL define a `Tenant` model as the root aggregate of the multi-tenant architecture. Each tenant represents an institution.

- `id`: UUID v4 — primary key
- `nombre`: string — institution full name
- `codigo`: string — unique short code within the system (e.g., "UTN-FRBA")
- `estado`: enum — `Activo | Inactivo`
- `config`: JSONB — tenant-specific configuration (branding, templates, flags)
- `created_at`, `updated_at`, `deleted_at`: inherited from BaseModel

#### Scenario: Create a new tenant
- **WHEN** a new tenant is created with valid name and code
- **THEN** the system assigns a UUID, sets `created_at`, and marks it as `Activo`

#### Scenario: Tenant code uniqueness
- **WHEN** creating a tenant with a code that already exists
- **THEN** the system raises an integrity error (unique constraint)

#### Scenario: Deactivate a tenant
- **WHEN** an active tenant is deactivated
- **THEN** its `estado` changes to `Inactivo`

### Requirement: Tenant context resolution from JWT
The system SHALL provide a mechanism to resolve the current tenant context per request. The tenant SHALL be extracted exclusively from a verified JWT access token, not from any request header.

#### Scenario: Tenant resolution from verified JWT
- **WHEN** an authenticated request is processed
- **THEN** the `get_tenant_context` function reads `tenant_id` from the claims of the verified JWT access token

#### Scenario: Missing tenant claim in JWT is rejected
- **WHEN** a JWT access token lacks the `tenant_id` claim
- **THEN** the system raises a 401 Unauthorized and does not process the request

#### Scenario: Development fallback via test JWT
- **WHEN** a request is made in development mode without a valid JWT
- **THEN** the system returns 401 Unauthorized; development environments SHALL use a pre-issued test JWT instead of header-based tenant resolution
