## Context

C-03 (auth-jwt-2fa) está completo: los usuarios se autentican con JWT, `get_current_user` resuelve identidad + roles + tenant. Pero **no existe autorización** — cualquier usuario autenticado llega a cualquier endpoint. El archivo `app/core/permissions.py` es un placeholder con un comentario "RESERVADO para C-04".

La KB (`03_actores_y_roles.md`) define 7 roles y una matriz de ~20 capacidades con permisos finos `modulo:accion`. Este diseño implementa esa matriz como datos administrables y un guard que la hace cumplir.

## Goals / Non-Goals

**Goals:**
- Modelos `Rol`, `Permiso`, `RolPermiso` como catálogo administrable en DB
- Seed de los 7 roles del dominio con su matriz de permisos basal
- Guard `require_permission("modulo:accion")` como FastAPI dependency
- Resolución server-side de permisos efectivos (rol → permisos) por tenant
- Migración Alembic 003 con seed data
- Tests: sin permiso → 403, unión de roles, catálogo administrable, aislamiento por tenant

**Non-Goals:**
- CRUD de roles/permisos como endpoints administrables (se hará en C-06 o posterior como parte de `estructura:gestionar`)
- Cache de permisos (la tabla es pequeña, se optimiza después si hace falta)
- Modelo `Asignacion` o vigencia contextual (C-07) — este change solo modela qué permisos tiene cada rol, no quién tiene cada rol
- Scope `(propio)` — se resuelve en cada endpoint que lo requiere, no es atributo del permiso

## Decisions

### D1 — Resolución server-side, no JWT claims
El JWT lleva `roles` como identificador secundario, pero la resolución de qué permisos tiene cada rol se hace en DB por request. Esto evita tener que reemitir tokens cuando cambia la matriz de permisos y mantiene el JWT mínimo (solo identidad + roles + tenant).

### D2 — `modulo:accion` como string con columnas separadas
La tabla `Permiso` tiene columnas `modulo` y `accion` por separado, más un `codigo` unique generado como `{modulo}:{accion}`. Esto permite queries por módulo (ej: listar todos los permisos de `calificaciones`) y mantiene la legibilidad.

### D3 — `(propio)` es responsabilidad del endpoint, no del permiso
Los permisos marcados como `(propio)` en la matriz (ej: PROFESOR solo importa calificaciones de sus materias) no se modelan como atributo del permiso. El guard `require_permission` verifica que el rol tenga el permiso, y cada endpoint que lo necesita agrega su validación de alcance. Esto evita falsa sensación de seguridad y mantiene el modelo de permisos simple.

### D4 — Seed en migración, no en código
Los 7 roles y su matriz de permisos se insertan en `003_rol_permiso.py` como datos de migración. Si la matriz cambia en el futuro, se crea una nueva migración. Esto mantiene el historial versionado.

### D5 — Guard inyecta UserContext, no hace segunda consulta
`require_permission` recibe el `UserContext` de `get_current_user` y consulta la DB una sola vez para resolver roles → permisos. No vuelve a validar el token ni resuelve el usuario de nuevo.

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|------------|
| **Latencia por consulta DB en cada request**: resolver permisos agrega un round-trip a PostgreSQL. | La tabla RolPermiso es pequeña (~140 filas). Se agrega índice compuesto en `(tenant_id, rol_id)`. Si escala, se implementa cache con invalidación por cambio en catálogo (post-MVP). |
| **Seed desincronizado con la KB**: los cambios en la matriz de permisos requieren actualizar la migración. | El CHANGES.md marca "Leer antes" la KB para cada change. Al agregar un nuevo módulo (ej: C-12 comunicaciones), el change correspondiente debe actualizar el seed en una nueva migración. |
| **Falsa seguridad por `(propio)` delegado al endpoint**: si un endpoint olvida agregar la validación de scope propio, un usuario podría operar sobre datos ajenos. | Code review obligatorio en endpoints que usan permisos `(propio)`. Se puede agregar un test helper que verifique que los endpoints documentan su scope. |
