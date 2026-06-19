## Context

C-07 completed the identity layer (`Usuario`) and assignment model (`Asignacion`) that links people to roles and academic contexts. However, no padron data exists yet — the system has no way to know which students are enrolled in which subject. This is a foundational prerequisite for the entire value chain: without padron there is no `Calificacion` to import (C-10), no late-student analysis (C-11), and no communication recipients (C-12).

This change introduces the first integration with Moodle Web Services. The Moodle WS client built here will be reused by C-10 for grade ingestion, making this the shared integration foundation. C-09 is backend-only; no frontend changes are included.

---

## Goals / Non-Goals

**Goals:**
- Snapshot-based versioned padron storage (`VersionPadron` + `EntradaPadron`)
- File-based import (`.xlsx`/`.csv`) with server-side preview
- Moodle WS client for on-demand sync + nightly scheduled sync
- Clear subject data endpoint (destroy all padron versions for materia+cohorte)
- Full multi-tenant row-level isolation
- Permission `padron:importar` with scope `(propio)` for PROFESOR
- Audit trail via `PADRON_CARGAR` on every write operation

**Non-Goals:**
- No frontend (pure backend change)
- No grade import (deferred to C-10)
- No delta/diff tracking (snapshot-only approach confirmed)
- No REST API exposed from Moodle (client calls out, does not serve)

---

## Decisions

### D-01 Snapshot versioning

Each import creates a complete `VersionPadron` row and all its `EntradaPadron` rows in a single transaction. Activating a new version sets `activa=True` on the new version and `activa=False` on the previous active version for that `(materia_id, cohorte_id)` pair. There is no delta computation, no diff tracking — the full snapshot is always stored.

**Rationale**: Simpler than delta (no diff logic, no merge conflicts), full history preserved for audit, aligns with KB §E6. Delta tracking can be added later as an optimization if storage growth becomes an issue.

### D-02 Preview as separate step (two-phase flow)

Two sequential endpoints:

1. `POST /padron/import/preview` — receives the file, parses rows, auto-detects columns (`nombre`, `apellido(s)`, `email`, `comision`, `regional` from headers), validates per-row, and returns parsed rows as JSON without persisting anything.

2. `POST /padron/import/confirm` — receives a `{ file_hash: str }` (or re-uploads the file identified by a preview token) and creates the `VersionPadron` + all `EntradaPadron` rows. Returns the created version.

**Rationale**: User reviews the parsed data before committing. Server returns all detected rows so the client can present them for confirmation. Validation errors are collected per-row (no fail-fast) so the user sees all issues at once.

### D-03 Moodle WS client as isolated module

Standalone `MoodleWSClient` class in `integrations/moodle_ws.py`. Per-tenant configuration (`MOODLE_WS_URL`, `MOODLE_WS_TOKEN`) read from environment variables via tenant config. Supports two modes:

- **On-demand**: triggered by `POST /padron/sync/moodle` endpoint
- **Nightly scheduled**: self-contained loop in the worker that iterates all active `(materia, cohorte)` pairs for each tenant

Connection errors with Moodle map to HTTP `502` with configurable retry (3 attempts, exponential backoff). The client is designed to be reused by C-10 for grade ingestion.

**Rationale**: Isolation lets the module evolve independently. Worker independence (no external cron dependency) keeps deployment simple for MVP.

### D-04 File parsing via openpyxl + csv

Use `openpyxl` for `.xlsx` and stdlib `csv` for `.csv`. Auto-detect columns by fuzzy-matching header names to known fields (`nombre`, `apellido(s)`, `email`, `comision`, `regional`). Row-level validation collects errors without failing fast.

**Rationale**: Both libraries are widely adopted and well maintained. Per-row error collection gives the user a complete picture of issues.

### D-05 usuario_id nullable on EntradaPadron

The `usuario_id` foreign key in `EntradaPadron` is nullable. A null value means "no matching `Usuario` found yet." This allows importing padron data before students have user accounts in the system.

**Rationale**: Matches KB §E6 rule: "Una EntradaPadron puede existir antes de que el alumno tenga cuenta de usuario en el sistema." A future background matching process can link them.

### D-06 Nightly sync as standalone worker loop

The nightly sync uses the same `MoodleWSClient` class in a self-contained loop: iterate all tenants, for each tenant iterate active `(materia, cohorte)` pairs, call Moodle's `core_enrol_get_enrolled_users`, create new `VersionPadron`. Sleep between iterations. No external cron or scheduler — keeps the worker self-contained.

**Rationale**: Simpler deployment (no cron setup). A proper scheduler can be introduced later. A lock flag on tenant config prevents overlapping runs.

### D-07 Clear subject data as service-level hard delete

The "clear subject data" endpoint destroys all `VersionPadron` and `EntradaPadron` rows for the target `(materia_id, cohorte_id)` within the tenant scope. This uses a hard delete (not soft delete) via a dedicated repository method (`hard_delete=True` flag or direct SQL).

**Rationale**: Per RN-04 the intent is a clean slate — removing all imported padron (and in the future, grade) data for the materia. Hard delete is irreversible, which is the desired semantic. If recovery is needed later, it can be built on top of audit log replay.

### D-08 Permission seed in same migration

The `padron:importar` permission and its `rol_permiso` assignments are seeded in the same Alembic migration that creates `version_padron` and `entrada_padron` tables. Follows the exact pattern from migration `003_rol_permiso.py`: deterministic UUIDs, `rol_permiso` rows for COORDINADOR (global scope) and PROFESOR (`propio` scope).

**Rationale**: Atomic deployment — the tables and their permission guard arrive together. No dangling permissions.

---

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Hard delete is irreversible** for clear subject data | Data loss if recovery is needed later | Accepted per RN-04 intent. Audit log provides a record for manual reconstruction if absolutely necessary. |
| **Moodle WS dependency** | Import fails with 502 if Moodle is down | File-based import (xlsx/csv) always available as manual fallback. Retry with backoff on transient errors. |
| **Snapshot storage growth** | Each import duplicates ALL rows; large cohorts (1000+) + frequent imports = linear growth | Accepted for MVP. An archive/purge policy or delta mode can be added later. |
| **Nightly sync overlap** | If sync takes >24h, overlapping runs could race on version activation | Lock flag on tenant config: skip if previous sync is still running. |
| **Column auto-detection accuracy** | Headers may vary across institutions | Acceptable for MVP — a manual column mapping endpoint can be added if needed. |
| **Null usuario_id in EntradaPadron** | Unlinked students cannot receive communications or have grades | Background matching (future) links by email hash. |
