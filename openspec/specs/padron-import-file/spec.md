## ADDED Requirements

### Requirement: Preview padron file
The system SHALL accept an uploaded .xlsx or .csv file, parse it, auto-detect columns (nombre, apellidos, email, comision, regional), and return a server-side preview with: detected column mapping, total row count, sample rows (first 5), and any parse errors per row. This SHALL NOT persist any data.

#### Scenario: Preview valid xlsx
- WHEN a user uploads a valid .xlsx file with expected columns
- THEN the system returns JSON with column mapping, row count, sample rows, and zero errors

#### Scenario: Preview file with missing required columns
- WHEN a user uploads a .csv file missing the "email" column
- THEN the system returns a validation error indicating which columns are missing

#### Scenario: Preview file with row-level errors
- WHEN a .xlsx file has rows with invalid data (empty required fields)
- THEN the system returns the preview with per-row errors listed, not fail-fast

#### Scenario: Reject unsupported format
- WHEN a user uploads a .pdf file
- THEN the system returns 400 Bad Request

### Requirement: Confirm import and persist version
After preview, the user SHALL confirm to persist. The system creates a new VersionPadron (origen="archivo") with all validated EntradaPadron entries, then activates it (deactivating previous).

#### Scenario: Confirm import creates version
- WHEN a user confirms after preview with valid data
- THEN the system creates a VersionPadron with origen="archivo" and all entries, activates it, and returns the version id

#### Scenario: Confirm import auto-matches existing usuarios
- WHEN an EntradaPadron has an email matching an existing Usuario in the same tenant
- THEN the system SHALL set usuario_id to the matched Usuario.id

#### Scenario: Confirm import leaves usuario_id null for unknown emails
- WHEN an EntradaPadron email does not match any Usuario
- THEN usuario_id SHALL be set to null

### Requirement: RBAC for import
PROFESOR can only import for materias they are assigned to (scope "propio"). COORDINADOR/ADMIN can import for any materia in their tenant.

#### Scenario: PROFESOR imports own materia
- WHEN a PROFESOR imports a file for a materia they are assigned to
- THEN the import succeeds

#### Scenario: PROFESOR cannot import other materia
- WHEN a PROFESOR tries to import for a materia they are NOT assigned to
- THEN the system returns 403
