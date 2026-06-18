## ADDED Requirements

### Requirement: Generic repository with tenant scoping
The system SHALL provide a `BaseRepository` generic class that wraps SQLAlchemy async operations with automatic tenant filtering.

- Parameterized by model type `T`
- Receives `db: AsyncSession` and `tenant_id: UUID` at construction
- All CRUD methods apply `tenant_id = :tenant_id` filter automatically
- All CRUD methods apply `deleted_at IS NULL` filter automatically (unless overridden)

#### Scenario: Create record with tenant scope
- **WHEN** creating a record via the repository
- **THEN** the record is associated with the repository's tenant_id

#### Scenario: Get record scoped to tenant
- **WHEN** retrieving a record by ID
- **THEN** the query includes `WHERE tenant_id = :tenant_id AND deleted_at IS NULL`

#### Scenario: Get record from different tenant returns None
- **WHEN** attempting to get a record belonging to a different tenant
- **THEN** the repository returns `None`

#### Scenario: List records scoped to tenant
- **WHEN** listing records
- **THEN** only records belonging to the repository's tenant are returned

#### Scenario: Update record scoped to tenant
- **WHEN** updating a record
- **THEN** the update query includes tenant_id and deleted_at filters

#### Scenario: Soft delete via repository
- **WHEN** deleting a record via the repository
- **THEN** it performs an UPDATE setting `deleted_at` instead of a DELETE statement

#### Scenario: List with additional filters
- **WHEN** listing records with keyword filters
- **THEN** the filters are combined with the base tenant and soft-delete filters

### Requirement: Cross-tenant access for admin operations
The system SHALL provide an explicit method to bypass tenant scope, restricted to controlled administrative operations.

#### Scenario: Get record without tenant filter
- **WHEN** calling the explicit cross-tenant method
- **THEN** the query does NOT include the tenant_id filter
