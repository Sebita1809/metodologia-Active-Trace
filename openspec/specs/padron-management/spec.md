## ADDED Requirements

### Requirement: Create VersionPadron with EntradaPadron entries
The system SHALL support creating a new `VersionPadron` with multiple `EntradaPadron` entries. When created, it is NOT active by default (`activa=False`). The version SHALL record: materia_id, cohorte_id, cargado_por (user), origen ("archivo" or "moodle").

#### Scenario: Create version from valid data
- WHEN a user with `padron:importar` permission sends a valid set of EntradaPadron records for a materia+cohorte
- THEN the system creates the VersionPadron with activa=False and returns it with id and metadata

#### Scenario: Create version without usuario_id (student without account)
- WHEN an EntradaPadron entry has usuario_id=null
- THEN the system SHALL accept it and store the entry with usuario_id=None

#### Scenario: Reject version with wrong tenant
- WHEN a request includes materia_id or cohorte_id from a different tenant
- THEN the system SHALL return 403 Forbidden

### Requirement: Activate a VersionPadron (deactivates previous)
The system SHALL support activating a VersionPadron. When a version is activated, any previously active version for the same (materia_id, cohorte_id) SHALL be deactivated (activa=False). There MUST be at most one active version per (materia, cohorte) at any time.

#### Scenario: Activate version deactivates previous
- WHEN there is an existing active version for (materia, cohorte) and a new version is activated
- THEN the old version's activa flag becomes False and the new version's activa flag becomes True

#### Scenario: Activate already-active version is idempotent
- WHEN a version is already active and is activated again
- THEN the system SHALL return success with no changes

### Requirement: Get active VersionPadron by materia + cohorte
The system SHALL return the current active VersionPadron with all its EntradaPadron entries for a given (materia_id, cohorte_id), scoped to the tenant.

#### Scenario: Retrieve active version
- WHEN a user requests the active padron for a materia+cohorte
- THEN the system returns the active version with all entries

#### Scenario: No active version returns empty
- WHEN there is no active version for the materia+cohorte
- THEN the system returns 404 or null

### Requirement: List all versions for a materia + cohorte
The system SHALL list all VersionPadron records for a given (materia_id, cohorte_id), ordered by cargado_at descending, with active version marked.

#### Scenario: List versions
- WHEN a user requests the version history for a materia+cohorte
- THEN the system returns all versions ordered by date descending

### Requirement: Clear subject data (F1.5, RN-04)
The system SHALL allow clearing all padron data for a (materia_id, cohorte_id), scoped to the tenant. PROFESOR can only clear their own subjects (verified via Asignacion). COORDINADOR/ADMIN can clear any. This SHALL hard-delete all VersionPadron and EntradaPadron records for the scope.

#### Scenario: PROFESOR clears own materia
- WHEN a PROFESOR clears padron data for a materia they are assigned to
- THEN the system removes all VersionPadron and EntradaPadron records for that materia+cohorte

#### Scenario: PROFESOR cannot clear another's materia
- WHEN a PROFESOR tries to clear padron data for a materia they are NOT assigned to
- THEN the system returns 403 Forbidden

#### Scenario: COORDINADOR clears any materia
- WHEN a COORDINADOR clears padron data for any materia
- THEN the system removes all records

### Requirement: Audit PADRON_CARGAR on write operations
Every write operation (version activation, clear data) SHALL generate an audit record with action `PADRON_CARGAR`.

#### Scenario: Activate version creates audit record
- WHEN a version is activated
- THEN an AuditLog entry with accion="PADRON_CARGAR" is created

#### Scenario: Clear data creates audit record
- WHEN subject data is cleared
- THEN an AuditLog entry with accion="PADRON_CARGAR" is created

### Requirement: Multi-tenant isolation
All operations SHALL be scoped to the authenticated user's tenant. A user from tenant A SHALL NOT see or affect padron data from tenant B.

#### Scenario: Tenant isolation
- WHEN user from tenant A queries padron data
- THEN they only see data from tenant A
