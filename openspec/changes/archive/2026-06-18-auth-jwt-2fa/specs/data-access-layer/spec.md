## ADDED Requirements

### Requirement: RefreshToken model

The system SHALL define a `RefreshToken` SQLAlchemy model that inherits from `BaseModel` (with tenant_id) with the following fields:
- `id`: UUID primary key
- `user_id`: UUID foreign key to `auth_user.id`, NOT NULL
- `token_hash`: string (e.g. VARCHAR(64)), NOT NULL, indexed
- `expires_at`: datetime (UTC), NOT NULL
- `revoked_at`: nullable datetime (UTC)
- `replaced_by`: nullable UUID self-referencing foreign key to `refresh_token.id`

The model SHALL use soft delete via `deleted_at` as defined by `BaseModel`.

#### Scenario: Create RefreshToken record
- **GIVEN** a user and tenant
- **WHEN** creating a RefreshToken via the user_id, token_hash, and expires_at
- **THEN** the record is persisted with the given tenant_id, and `revoked_at` and `replaced_by` default to NULL

#### Scenario: Revoke RefreshToken
- **GIVEN** an active RefreshToken for a user
- **WHEN** `revoked_at` is set to the current timestamp
- **THEN** the token is considered revoked and SHALL NOT be usable for refresh operations

#### Scenario: Token rotation via replaced_by
- **GIVEN** a token being rotated
- **WHEN** a new RefreshToken is issued with `replaced_by` pointing to the previous token's ID
- **THEN** the previous token's `replaced_by` references the new token, forming a chain

#### Scenario: Query by token_hash
- **GIVEN** a stored RefreshToken
- **WHEN** querying by `token_hash`
- **THEN** the repository returns the matching token scoped to the current tenant, or None if not found or belonging to a different tenant

### Requirement: Repository for RefreshToken

The system SHALL provide a `RefreshTokenRepository` that extends `BaseRepository[RefreshToken]` with the following methods:
- `create(user_id, token_hash, expires_at) -> RefreshToken`
- `get_by_token_hash(token_hash) -> RefreshToken | None`
- `revoke(token_id) -> None`
- `list_active_by_user_id(user_id) -> list[RefreshToken]`

All operations SHALL be scoped by tenant via the inherited `BaseRepository` tenant filter.

#### Scenario: Create token via repository
- **GIVEN** a tenant and user
- **WHEN** calling `create` with user_id, token_hash, and expires_at
- **THEN** a new RefreshToken is persisted with the repository's tenant_id

#### Scenario: Get by token_hash finds active token
- **GIVEN** an active token in the database
- **WHEN** calling `get_by_token_hash` with the matching hash
- **THEN** the token is returned

#### Scenario: Get by token_hash returns None for revoked token
- **GIVEN** a revoked token in the database
- **WHEN** calling `get_by_token_hash` with its hash
- **THEN** the token is still returned (the method does NOT filter by revoked status — revocation check is caller's responsibility)

#### Scenario: Revoke marks token as revoked
- **GIVEN** an active token
- **WHEN** calling `revoke` with its ID
- **THEN** the token's `revoked_at` is set to the current timestamp

#### Scenario: List active tokens returns non-revoked, non-expired tokens for user
- **GIVEN** a user with 2 active tokens and 1 revoked token in the same tenant
- **WHEN** calling `list_active_by_user_id`
- **THEN** only the 2 active (non-revoked, non-expired) tokens are returned

#### Scenario: List active tokens excludes tokens from other tenants
- **GIVEN** the same user_id exists in two tenants
- **WHEN** calling `list_active_by_user_id`
- **THEN** only tokens belonging to the repository's tenant are returned, even if the user_id matches
