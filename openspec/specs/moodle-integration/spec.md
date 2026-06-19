## ADDED Requirements

### Requirement: MoodleWSClient connects to Moodle
The `MoodleWSClient` SHALL authenticate via per-tenant token and URL. It SHALL expose a `get_enrolled_users(course_id)` method that calls `core_enrol_get_enrolled_users`.

#### Scenario: Successful connection
- WHEN the Moodle WS URL and token are valid
- THEN the client can fetch enrolled users for a course

#### Scenario: Connection failure returns error
- WHEN the Moodle server is unreachable
- THEN the client raises a typed exception that maps to 502

### Requirement: On-demand padron sync from Moodle
An endpoint SHALL trigger on-demand sync for a specific (materia_id, cohorte_id). It maps the materia to a Moodle course, fetches enrolled users, and creates a new VersionPadron with origen="moodle".

#### Scenario: On-demand sync success
- WHEN a user triggers on-demand sync for a materia+cohorte mapped to a Moodle course
- THEN the system fetches users from Moodle, creates a new VersionPadron, and activates it

#### Scenario: On-demand sync with Moodle down returns 502
- WHEN Moodle is unreachable during on-demand sync
- THEN the system returns 502 Bad Gateway with retry info

### Requirement: Nightly scheduled sync
A worker SHALL run nightly, iterating all tenants, their active materias x cohortes, and trigger Moodle sync for each. It SHALL skip if previous sync is still running (lock mechanism).

#### Scenario: Nightly sync processes all tenants
- WHEN the nightly sync runs
- THEN it iterates all tenants and syncs their active materias x cohortes

#### Scenario: Nightly sync skips tenant with lock
- WHEN a tenant's previous nightly sync is still running
- THEN the sync skips that tenant and logs it

### Requirement: Error handling with retry
All Moodle WS calls SHALL implement retry (3 attempts, exponential backoff). If all retries fail, the error SHALL be logged and returned as 502.

#### Scenario: Retry succeeds on second attempt
- WHEN first Moodle call fails but second succeeds
- THEN the operation continues and succeeds

#### Scenario: All retries fail
- WHEN all 3 Moodle call attempts fail
- THEN the system returns 502 and logs the error

### Requirement: Tenant-scoped Moodle config
Each tenant SHALL have its own Moodle WS URL and token, configurable via tenant config (JSONB field on Tenant model or environment variables).

#### Scenario: Tenant has moodle config
- WHEN a tenant has MOODLE_WS_URL and MOODLE_WS_TOKEN configured
- THEN the client uses those values for that tenant's sync

#### Scenario: Tenant without moodle config skips sync
- WHEN a tenant has no Moodle config
- THEN sync returns a clear error that fallback import is available
