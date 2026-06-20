## Context

C-01 levantó el scaffold FastAPI. C-02 creó `BaseTenantModel`, `BaseRepository[T]` con scope de tenant obligatorio y `CryptoService`. C-03 implementó la identidad completa y expuso `get_current_user`, que retorna un `CurrentUser(user_id, tenant_id, roles)` derivado **exclusivamente** del JWT verificado. Hoy `app/core/permissions.py` y el `require_permission` de `app/core/dependencies.py` son stubs reservados: **no hay autorización**.

C-04 cierra el bloque fundacional de seguridad. Debe construir el catálogo RBAC como **datos administrables** (no hardcode), resolver permisos efectivos **server-side por request** contra la BD (los `roles` del JWT son informativos, los permisos nunca viajan en el token — ver C-03 design §3.1) y exponer el guard `require_permission` fail-closed que todo endpoint declara.

Governance: **CRÍTICO**. Cada decisión de modelado de permisos y de evaluación del guard tiene impacto de seguridad transversal y requiere revisión humana antes de implementar.

Restricciones del proyecto que enmarcan el diseño:
- Multi-tenancy row-level: toda tabla lleva `tenant_id`; los repositories filtran por tenant por defecto (`BaseRepository`).
- Identidad SIEMPRE desde el JWT verificado; jamás desde la petición.
- Fail-closed: sin permiso explícito → 403.
- Soft delete siempre; una migración Alembic por cambio de schema; Pydantic `extra='forbid'`; tests sin mocks de DB.

## Goals / Non-Goals

**Goals:**
- Catálogo administrable `roles`, `permisos`, `rol_permiso` (matriz como datos) + asignación `usuario_rol` con vigencia, todo scoped por tenant.
- Seed idempotente de los 7 roles del dominio y de la matriz base de `03_actores_y_roles.md` §3.3.
- Servicio de resolución de **permisos efectivos**: unión de permisos de los roles **vigentes** del usuario, acotada por tenant, calculada por request.
- Guard `require_permission("modulo:accion")` como dependency FastAPI, fail-closed (403), con soporte de alcance `(propio)` vs global.
- API de administración del catálogo (CRUD roles/permisos/matriz) protegida por permisos `rbac:*`.
- Cobertura ≥90% de las reglas de negocio del módulo.

**Non-Goals:**
- Asignación rol↔contexto-académico (materia/comisión) completa con clonado entre períodos → **C-07** (usuarios-y-asignaciones). C-04 modela `usuario_rol` a nivel tenant (vigencia simple), suficiente para resolver permisos hoy.
- Impersonación (`impersonacion:usar`) → se siembra el permiso en el catálogo, pero el mecanismo de sesión impersonada se implementa en **C-05** (audit-log).
- Persistir permisos en el JWT (decisión explícita: se resuelven server-side).
- Caché de permisos efectivos (Redis u otro) → optimización posterior si el profiling lo exige.
- UI de administración del catálogo → C-21+ (frontend).

## Decisions

### D-01: Catálogo como datos, no enums hardcodeados

**Decisión:** `roles`, `permisos` y `rol_permiso` son tablas. Los permisos se identifican por la clave canónica `modulo:accion` (columna `clave`, única por tenant). El código **nunca** define la matriz; la lee de la BD.

**Alternativa considerada:** enum de permisos en Python + decorador que chequea contra el enum. Descartado: viola la regla dura "catálogo en BD, no hardcode" y `03_actores_y_roles.md` §3.3 ("modelarla como datos … no hardcodearla"). Un enum impide que un ADMIN administre la matriz por tenant.

**Rationale:** las claves `modulo:accion` que los endpoints declaran en `require_permission(...)` son constantes en código (contrato del endpoint), pero **la pertenencia rol→permiso** vive en datos. El endpoint dice "exijo `comunicacion:enviar`"; quién lo tiene es configurable.

### D-02: Resolución de permisos efectivos server-side por request

**Decisión:** un `RbacService.resolver_permisos_efectivos(user_id, tenant_id, ahora)` calcula la **unión** de claves de permiso de todas las asignaciones `usuario_rol` **vigentes** del usuario en su tenant, vía join `usuario_rol → rol_permiso → permiso`. Devuelve un `set[str]` de claves (más el alcance por clave; ver D-04). Se invoca dentro del guard, una vez por request protegido.

**Alternativa considerada:** materializar los permisos en el JWT al hacer login. Descartado: C-03 design §3.1 fija que "los permisos se resuelven server-side en cada petición, nunca se almacenan en el token". Un cambio en la matriz debe surtir efecto inmediato sin reemitir tokens; un permiso revocado no puede sobrevivir en un token vigente.

**Rationale:** una query indexada por `(tenant_id, user_id)` con join sobre tablas pequeñas (catálogo) es barata. La corrección y la revocación inmediata pesan más que el micro-costo. Si el profiling lo exige, se cachea por request (no entre requests).

### D-03: `usuario_rol` con vigencia simple en C-04; contexto académico en C-07

**Decisión:** `usuario_rol(tenant_id, user_id, rol_id, vigente_desde, vigente_hasta NULL)`. Una asignación está **vigente** si `ahora ∈ [vigente_desde, vigente_hasta)` (hasta abierto = NULL). El histórico se conserva (soft delete + asignaciones vencidas no se borran).

**Alternativa considerada:** modelar ya la asignación rol↔materia/comisión con todo el contexto académico. Descartado: las entidades académicas (Materia, Comisión) no existen hasta C-06/C-07, y CHANGES.md asigna esa pieza a **C-07**. Adelantarlo bloquearía C-04 contra dependencias inexistentes.

**Rationale:** C-04 necesita resolver permisos **hoy** para habilitar GATE 4. Una asignación a nivel tenant con vigencia es el mínimo correcto. C-07 extiende el modelo (FK a contexto académico) sin romper el resolver: el resolver ya contempla vigencia.

### D-04: Alcance `(propio)` vs global en `rol_permiso`

**Decisión:** `rol_permiso` lleva una columna `alcance` con valores `global` | `propio` (default `global`). El resolver devuelve, por cada clave de permiso, el **alcance más amplio** otorgado por los roles del usuario (`global` gana sobre `propio`). El guard `require_permission(clave, scope="global"|"propio")` declara qué exige el endpoint:
- endpoint con `scope="global"` → requiere alcance `global`.
- endpoint con `scope="propio"` → acepta `propio` o `global`; expone al handler el alcance concedido para que filtre por dueño cuando sea `propio`.

**Alternativa considerada:** dos permisos distintos por capacidad (`atrasados:ver_propio` y `atrasados:ver`). Descartado: duplica el catálogo y la matriz, y la KB usa el modificador `(propio)` sobre la **misma** capacidad. Una columna `alcance` modela la matriz §3.3 fielmente.

**Rationale:** la matriz expresa `✅ (propio)` como una restricción sobre la misma capacidad, no como otra capacidad. El handler recibe el alcance efectivo y aplica el filtro de dueño en su query (la verificación de dueño es responsabilidad del Service/Repository, no del guard).

### D-05: `require_permission` como dependency factory fail-closed

**Decisión:** `require_permission(clave: str, scope: str = "global")` retorna una dependency async que: (1) toma `CurrentUser` de `get_current_user`, (2) obtiene una sesión vía `get_db`, (3) llama a `RbacService.resolver_permisos_efectivos`, (4) si la clave no está presente con alcance suficiente → `HTTPException(403)`; si está → retorna un `PermisoConcedido(clave, alcance)` que el handler puede inyectar. Sin permiso explícito → 403 (nunca 401, que es "no autenticado"; nunca passthrough).

**Alternativa considerada:** middleware global que mapea ruta→permiso desde una tabla. Descartado: acopla autorización al routing, oculta el permiso requerido del endpoint y dificulta el test unitario. La dependency explícita hace el contrato visible en la firma del handler y es trivial de sobrescribir en tests.

**Rationale:** patrón idiomático de FastAPI, consistente con `get_current_user` (C-03 D-08). Fail-closed por construcción: el default de cualquier endpoint sin `require_permission` es que no expone datos protegidos; agregar el guard es una decisión positiva y declarativa.

### D-06: Seed idempotente por tenant, ejecutado en la migración + helper reutilizable

**Decisión:** la migración 004 crea las tablas y siembra permisos y roles globales del dominio + la matriz base. El seed es **idempotente** (upsert por `clave`/`nombre` dentro del tenant): re-ejecutarlo no duplica. Se factoriza en un helper (`app/services/rbac_seed.py`) reutilizable al alta de un nuevo tenant.

**Alternativa considerada:** seed solo en un script aparte fuera de Alembic. Descartado: dejaría una BD recién migrada sin la matriz base, rompiendo cualquier login funcional. El seed debe acompañar el schema.

**Rationale:** un tenant nuevo necesita la matriz base desde el minuto cero. Idempotencia permite re-correr el seed tras agregar permisos en futuros changes sin colisiones.

### D-07: Una migración (004) para todo el catálogo

**Decisión:** `004_rbac_catalog.py` crea `roles`, `permisos`, `rol_permiso`, `usuario_rol` y aplica el seed, en una sola migración (un cambio de schema cohesivo). Numeración 004 (003 fue `totp_secrets`).

**Rationale:** las cuatro tablas son un único concepto (el catálogo RBAC) y se despliegan juntas. La regla "una migración por cambio de schema" se respeta tratando el catálogo como el cambio atómico. Rollback: `downgrade` dropea las cuatro tablas (datos nuevos, sin pérdida de negocio).

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|------------|
| Resolver permisos por request agrega una query a cada endpoint protegido | Query indexada por `(tenant_id, user_id)` sobre catálogo pequeño; cachear por request si el profiling lo exige (no entre requests, para no romper revocación inmediata). |
| `usuario_rol` simple en C-04 podría chocar con el modelo de asignaciones de C-07 | D-03 deja el resolver ya consciente de vigencia; C-07 extiende con FK a contexto académico sin reescribir el resolver. Documentado como evolución, no breaking. |
| Alcance `(propio)` mal aplicado en un handler dejaría ver datos ajenos | El guard concede el alcance pero la verificación de dueño es responsabilidad del Service/Repository; los specs exigen escenario de test `(propio)` que falla si el handler no filtra. Code review CRÍTICO. |
| Seed no idempotente duplicaría permisos al re-correr | D-06: upsert por clave única dentro del tenant; test de idempotencia (re-seed no cambia el conteo). |
| Catálogo administrable mal protegido permitiría a un rol no-ADMIN editar la matriz (escalada de privilegios) | Los endpoints de administración exigen permisos `rbac:*`, sembrados solo para ADMIN; test de escalada (rol no autorizado → 403). |
| Confundir 401 vs 403 filtraría existencia de recursos o rompería el contrato | El guard SIEMPRE responde 403 ante falta de permiso (autenticado pero no autorizado); 401 queda exclusivo de `get_current_user`. |

## Migration Plan

1. `alembic upgrade head` → aplica `004_rbac_catalog` (crea `roles`, `permisos`, `rol_permiso`, `usuario_rol`) y ejecuta el seed idempotente de la matriz base por cada tenant existente.
2. No hay datos RBAC previos que migrar (C-01..C-03 no tenían catálogo de permisos).
3. Asignar roles iniciales a los usuarios existentes (si los hubiera) es responsabilidad operativa post-migración (no hay usuarios reales aún).
4. Rollback: `alembic downgrade -1` dropea las cuatro tablas. Sin pérdida de datos de negocio (tablas nuevas).

## Open Questions

- **OQ-C04-01**: ¿El rol **NEXO** tiene fila propia en la matriz §3.3? La matriz de §3.3 no lista NEXO como columna (PA-25 marca su semántica como pregunta abierta ALTA). → Para C-04: sembrar el rol NEXO en `roles` (existe como rol del dominio) pero **sin permisos asignados** en `rol_permiso` hasta que PA-25 se cierre. No bloquea el catálogo; un rol sin permisos simplemente no otorga acceso (fail-closed). Surfacear a revisión humana.
- **OQ-C04-02**: ¿La asignación `usuario_rol` permite múltiples roles activos simultáneos al mismo usuario? Sí (un usuario puede ser PROFESOR y COORDINADOR — §2). El resolver hace unión; no hay exclusión mutua entre roles.
- **OQ-C04-03**: ¿`impersonacion:usar` se siembra ya en C-04? → Sí, el permiso entra al catálogo (asignado a ADMIN), pero el mecanismo de impersonación se implementa en C-05. Confirmar alcance con el orquestador.
