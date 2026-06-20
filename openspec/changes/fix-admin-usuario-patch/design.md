## Context

The admin usuarios feature (PATCH /api/admin/usuarios/{id}) has two bugs:

1. **Missing `rol` field**: The user's role is stored in the `Asignacion` table (ADMIN, PROFESOR, TUTOR, COORDINADOR, NEXO, FINANZAS, ALUMNO), but `UsuarioResponse` does not expose it. The frontend table, detail view, and edit form have no way to display the current role.

2. **Empty string vs null for optional crypto fields**: CBU (22-digit bank code), `alias_cbu`, and `modalidad_cobro` are optional, but:
   - The frontend Zod schema uses `.or(z.literal(''))` to allow empty strings, but validation can still block submission.
   - `handleUpdate` maps `cbu: formData.cbu ?? null` — if cbu is `""`, it sends `""` instead of `null`.
   - The backend service checks `if cbu is not None:` — empty string passes, gets encrypted, and stored as encrypted empty string instead of `NULL`.

Current code state:
- `UsuarioResponse` — no `roles` field
- `UsuarioUpdate` — all fields optional (correct schema)
- Backend service `update_usuario` — encrypts any non-None CBU value
- Frontend Zod schema — allows empty string but inconsistently
- Frontend `handleUpdate` — `?? null` does not filter empty strings

## Goals / Non-Goals

**Goals:**

- Expose the current role(s) from `Asignacion` in `UsuarioResponse`
- Display role(s) in the frontend table, detail view, and edit form
- Make CBU, `alias_cbu`, and `modalidad_cobro` strictly optional end-to-end
- Fix PATCH handler to send `null` instead of `""` for crypto-encrypted optional fields
- Fix backend service to treat empty string as equivalent to `None` for encrypted fields

**Non-Goals:**

- Not modifying auth, RBAC, or permission checks
- Not redesigning how `Asignacion` works or how roles are assigned
- Not adding multi-role assignment in the admin edit form (read-only display only)
- Not migrating existing data where empty strings may already be stored

## Decisions

### D1 — Include roles in `UsuarioResponse` via relationship eager-loading

**Decision**: Extend `UsuarioResponse` with a `roles: list[str]` field populated from `Asignacion` via a SQLAlchemy relationship (or explicit query), eager-loaded in the handler.

**Rationale**: Adding a separate `/api/admin/usuarios/{id}/roles` endpoint would require an extra network round-trip on every detail load. The roles data is small, already in the same DB, and fundamentally belongs to the user resource. Co-locating it in the response is simpler and more efficient.

**Detail**: The service method `get_usuario` or `get_usuario_by_id` will join or `selectinload` the `asignaciones` relationship and extract unique role names. The schema field is `roles: list[str]` (not `Optional`) — an empty list is valid for users without assignments.

### D2 — Frontend: normalize empty strings to `null` before PATCH

**Decision**: In `handleUpdate`, transform all crypto-encrypted optional fields so that `""` becomes `null` before building the payload. No changes to the Zod schema beyond removing the `.or(z.literal(''))` clause.

**Rationale**: The cleanest fix is at the boundary where form data becomes the API payload. The Zod schema should simply declare these fields as `.nullable().optional()`. The transformation (`value === "" ? null : value`) lives in a small normalization helper or inline in `handleUpdate`. This keeps validation strict (no empty strings accepted) and ensures the backend always receives `null` for missing values.

### D3 — Backend: treat empty string as `None` for encrypted fields

**Decision**: In `update_usuario`, add an explicit normalization step before encryption checks:

```python
if cbu is not None and cbu.strip() == "":
    data["cbu"] = None
```

**Rationale**: Defense in depth. Even after the frontend fix, there may be clients (API consumers, scripts, future integrations) that send `""`. The service layer should be resilient to this. This normalization applies only to encrypted PII fields (CBU, and any future fields with the same pattern).

**Risk**: If `""` is ever a legitimate value for these fields (it is not — they are bank details), this would break. Acceptable given the domain.

### D4 — Role displayed as read-only text in the edit form

**Decision**: Show the role as a read-only `<span>` or `<Badge>` in the table column, detail view, and edit form. Not a dropdown or selectable input.

**Rationale**: Role assignment happens through a separate feature (likely managed via `Asignacion` CRUD). Including write access here would blur responsibilities, require permission checks for role changes, and expand scope. A read-only display is consistent with other fields that come from related tables (e.g., tenant name).

## Risks / Trade-offs

- **Risk: empty-string data already in the DB** — Existing records may have encrypted empty strings in the CBU column. This design does not include a migration to clean them up. A future `CLEANUP` migration or a background task could decrypt, detect empty, and set to NULL. Acceptable for now — the frontend will display an empty string instead of `"N/A"` for these records.

- **Risk: performance of eager-loading roles on list endpoints** — If `/api/admin/usuarios` lists hundreds of users, `selectinload` on `asignaciones` adds a second query. For current scale (institutional tenants, hundreds not thousands) this is negligible. If it becomes an issue, switch to a `subqueryload` or a dedicated lightweight endpoint.

- **Trade-off: D2 + D3 is redundancy** — Both layers normalize empty strings. This violates DRY but follows the principle of secure design: validate at every trust boundary. The frontend protects the user experience; the backend protects data integrity. Acceptable.

- **Trade-off: D4 limits UX** — A user viewing the edit form might expect to change the role. If this becomes a common request, a follow-up change can add role assignment with proper RBAC checks. The read-only display at least surfaces the information, which is the primary request.
