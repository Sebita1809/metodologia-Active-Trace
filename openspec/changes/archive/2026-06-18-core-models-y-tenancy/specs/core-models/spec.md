## ADDED Requirements

### Requirement: Base model mixin
The system SHALL provide a `BaseModel` mixin that every domain model inherits. It MUST include:

- `id`: UUID v4 — primary key, auto-generated
- `tenant_id`: UUID — foreign key to `Tenant`, NOT NULL
- `created_at`: datetime with timezone — set on creation, auto-populated
- `updated_at`: datetime with timezone — set on creation, updated on every modification
- `deleted_at`: datetime with timezone, nullable — soft delete marker (NULL = active)

#### Scenario: Model inherits base columns
- **WHEN** a new model inherits from `BaseModel`
- **THEN** it automatically has `id`, `tenant_id`, `created_at`, `updated_at`, and `deleted_at` columns

#### Scenario: UUID auto-generation on create
- **WHEN** a new entity is created
- **THEN** its `id` is automatically set to a valid UUID v4

#### Scenario: Timestamps on creation
- **WHEN** a new entity is persisted
- **THEN** `created_at` and `updated_at` are set to the current timestamp

#### Scenario: Timestamp update on modification
- **WHEN** an existing entity is updated
- **THEN** `updated_at` is refreshed to the current timestamp

### Requirement: Soft delete behavior
The system SHALL enforce soft delete for all domain models. A soft-deleted record has `deleted_at` set to a non-null timestamp.

#### Scenario: Mark record as deleted
- **WHEN** a record is soft-deleted
- **THEN** its `deleted_at` field is set to the current timestamp

#### Scenario: Soft-deleted records excluded by default
- **WHEN** querying records without explicit `include_deleted` flag
- **THEN** records with non-null `deleted_at` are excluded from results
