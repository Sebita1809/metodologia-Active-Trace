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

### Requirement: Tenant context resolution
The system SHALL provide a mechanism to resolve the current tenant context per request.

#### Scenario: Tenant resolution from development header
- **WHEN** a request includes `X-Tenant-ID` header in development mode
- **THEN** the system resolves the tenant UUID from that header

#### Scenario: Tenant resolution falls to default
- **WHEN** no `X-Tenant-ID` header is present in development mode
- **THEN** the system uses a default tenant for local development
