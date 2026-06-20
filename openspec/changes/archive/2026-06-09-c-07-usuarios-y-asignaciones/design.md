## Context

Governance: **CRÍTICO** (core-models + PII + multi-tenancy). Toda decisión de seguridad debe ser explícita y justificada.

La plataforma ya provee: tenant isolation (C-02), auth JWT (C-03), RBAC fino `modulo:accion` (C-04), audit log append-only (C-05) y catálogo académico Carrera/Cohorte/Materia (C-06). Existe además `CryptoService` (AES-256-GCM, `backend/app/core/crypto.py`) sembrado en C-02 para cifrar PII en reposo.

Este change agrega las dos entidades que faltan para describir **personas y su trabajo**:
- `Usuario` — la ficha de la persona (datos personales + fiscales, PII cifrada).
- `Asignacion` — el contexto académico-temporal de esa persona (rol de negocio, materia/carrera/cohorte/comisiones, vigencia, responsable jerárquico).

Arquitectura target: Clean Architecture — Router → Service → Repository → Model. Routers viven bajo `backend/app/api/v1/routers/`.

## Goals / Non-Goals

**Goals:**
- Modelo `Usuario` con PII cifrada AES-256 (`email`, `dni`, `cuil`, `cbu`, `alias_cbu`) vía `CryptoService`; nunca texto plano en DB, logs ni `__repr__`.
- Unicidad `(tenant_id, email)` aplicada en DB **y** en Service.
- Modelo `Asignacion` con rol de negocio (texto/enum, NO FK al catálogo Rol de RBAC), contexto académico nullable, `responsable_id` (jerarquía), vigencia `desde`/`hasta`.
- `estado_vigencia` (Vigente | Vencida) **derivado** en query/serialización, jamás persistido.
- ABM usuarios bajo `/api/admin/usuarios` con `require_permission("usuarios:gestionar")` (ADMIN).
- CRUD asignaciones bajo `/api/asignaciones` con `require_permission("equipos:asignar")` (ADMIN, COORDINADOR), con filtros.
- Migración 007 con tablas, índices únicos, FKs y data-seed defensivo de permisos.
- Tests: PII no expuesta en logs/respuestas, unicidad de email por tenant, vigencia (vencida no autoriza), multi-rol, jerarquía por responsable, aislamiento multi-tenant.

**Non-Goals:**
- No fusionar `Usuario` (ficha) con `User` (credenciales de auth). Ver D-07.
- Liquidaciones (C-18), equipos/encuentros (C-09+), padrón/alumnos (C-08).
- Importación masiva de usuarios — ABM manual únicamente.
- Frontend (C-24).
- Login/credenciales para `Usuario` — la autenticación sigue siendo de `User` (C-03).

## Decisions

### D-01: PII cifrada en reposo con `CryptoService` (AES-256-GCM)

Los campos `email`, `dni`, `cuil`, `cbu`, `alias_cbu` se almacenan como **ciphertext** (token base64url producido por `CryptoService.encrypt`). El cifrado/descifrado ocurre en la **capa Service** (no en el modelo ni el router): el Service recibe DTOs en claro, cifra antes de pasar al Repository, y descifra al construir la respuesta. La columna en DB es `Text`/`String` y guarda solo el token.

**Por qué Service y no Model**: mantener el cifrado en el Service deja el modelo como POPO de persistencia, evita efectos colaterales en queries y hace explícito en code review dónde se cifra/descifra. El IV aleatorio por operación implica que el mismo plaintext produce ciphertext distinto cada vez (semántica segura) — por eso `email` cifrado **no** sirve para un índice único directo (ver D-02).

### D-02: Unicidad de email — columna `email_hash` determinística para el índice

Como AES-GCM con IV aleatorio no es determinístico, no se puede poner `UNIQUE(tenant_id, email_cifrado)`. Para garantizar unicidad `(tenant_id, email)` sin filtrar el plaintext, se persiste una columna adicional **`email_hash`** = HMAC-SHA256 del email normalizado (lowercase/trim) con la `ENCRYPTION_KEY` como clave. El índice único es `UNIQUE(tenant_id, email_hash)`.

- El Service valida unicidad consultando por `email_hash` antes de insertar → HTTP 409 con mensaje descriptivo.
- El índice DB es la red de seguridad final (IntegrityError → 409).
- `email_hash` es un hash con clave (no reversible, no es PII en claro) y nunca se expone en respuestas.

**Alternativa descartada**: cifrado determinístico (AES-SIV) — agrega una segunda primitiva criptográfica y complejidad; HMAC para el índice + GCM para el dato es más simple y ya cubierto por la lib `cryptography`.

### D-03: PII nunca en logs ni `__repr__`

`Usuario.__repr__` expone solo `id` y `tenant_id` (UUID truncados), nunca email/dni/cuil/cbu. Los schemas de respuesta descifran controladamente solo los campos que el endpoint debe devolver. Ningún log estructurado incluye campos PII; los servicios loguean por `usuario_id` (UUID), nunca por dato personal. Esto se verifica con un test que inspecciona logs y `repr`.

### D-04: `estado_vigencia` es DERIVADO, nunca persistido

`Asignacion` guarda `desde` (date, NOT NULL) y `hasta` (date, nullable = open-ended). `estado_vigencia` se calcula con `hoy`:
- `Vigente` si `desde <= hoy AND (hasta IS NULL OR hoy <= hasta)`.
- `Vencida` si `hasta IS NOT NULL AND hoy > hasta`.
- (Pendiente/futura: `desde > hoy` — se trata como **no vigente** a efectos de autorización; se reporta como `Vigente` solo cuando ya empezó. La derivación exacta se documenta en el spec.)

Se expone como property computada en el schema de respuesta. **Nunca** se agrega una columna `estado_vigencia` en DB: una columna persistida quedaría desincronizada al pasar el tiempo sin un job. La derivación al vuelo es la fuente de verdad.

### D-05: `Asignacion.rol` es el rol de **negocio** (texto/enum), NO FK al catálogo Rol de RBAC

`rol` almacena el nombre del rol académico (`PROFESOR | TUTOR | COORDINADOR | NEXO | ADMIN | FINANZAS`) como `String` validado por enum en el schema. **No** es una FK a la tabla `rol` de C-04.

**Por qué**: `UsuarioRol` (C-04) otorga permisos RBAC a nivel sistema (`require_permission(...)`); `Asignacion` describe el contexto de trabajo ("quién dicta qué, dónde, cuándo"). Son sistemas que coexisten con propósitos distintos. Acoplar `Asignacion.rol` al catálogo RBAC mezclaría autorización con contexto de negocio y forzaría que todo rol de negocio fuese un rol RBAC, lo que no es cierto.

**Consecuencia explícita**: una `Asignacion` vencida **no** otorga ni revoca permisos RBAC — los permisos viven en `UsuarioRol`. La vigencia de la asignación es información de negocio/histórico, no un gate de autorización del sistema RBAC.

### D-06: Contexto académico nullable + comisiones como lista

`materia_id`, `carrera_id`, `cohorte_id` son **nullable**: un rol tenant-global (p. ej. ADMIN o FINANZAS) puede no estar atado a una materia. `comisiones` es una lista de strings (Postgres `ARRAY(String)` o JSONB) que puede estar vacía. Las FKs apuntan a las tablas de C-06 con `ondelete="RESTRICT"` (no se borra una materia con asignaciones colgando; además todo es soft delete). `responsable_id` es FK a `usuario` (auto-referencia), nullable, modela jerarquía docente.

### D-07: `Usuario` (ficha de dominio) coexiste con `User` (credenciales de auth)

Ya existe `User` (tabla `users`, C-03) con email + password_hash para autenticación. Este change crea `Usuario` (tabla `usuario`) como **ficha de persona del dominio** con PII y datos fiscales. **No se fusionan en C-07**: `User` resuelve "¿quién se loguea?", `Usuario` resuelve "¿quién es esta persona del tenant y qué hace?".

**Por qué no fusionar ahora**: fusionar tocaría auth (dominio CRÍTICO ya en producción), forzaría migrar `users` y reescribir el flujo de login dentro de un change cuyo foco es la ficha de dominio y las asignaciones. Se mantiene la separación; un eventual vínculo `Usuario.user_id` o unificación se evalúa como ADR/change posterior. El comentario en `user.py` que anticipaba "C-07 agrega campos de perfil a User" queda **superado** por esta decisión.

### D-08: Permisos — ADMIN gestiona usuarios; ADMIN+COORDINADOR asignan

- ABM usuarios (`/api/admin/usuarios`, todos los verbos de escritura): `require_permission("usuarios:gestionar")` → solo ADMIN.
- CRUD asignaciones (`/api/asignaciones`): `require_permission("equipos:asignar")` → ADMIN, COORDINADOR.
- Permiso adicional `asignaciones:gestionar` (ADMIN, COORDINADOR) disponible para operaciones de gestión amplia si se requiere.
- **Fail-closed**: sin permiso explícito → 403. Identidad y tenant SIEMPRE desde el JWT.
- La migración 007 siembra defensivamente estos permisos y su asignación a roles si el seed de C-04 no los incluyó.

### D-09: Unicidad y validación en DB + Service (doble protección)

Igual que C-06: índices únicos en la migración (fuente de verdad) + validación previa en el Service (mejora UX con 409 descriptivo antes del IntegrityError). Aplica a `(tenant_id, email_hash)` en `usuario`.

## Risks / Trade-offs

- **[Riesgo] PII filtrada por descifrado descuidado**: mitigado concentrando encrypt/decrypt en el Service, `__repr__` sin PII, schemas que descifran solo lo necesario, y tests que inspeccionan logs/repr. Code review CRÍTICO obligatorio.
- **[Riesgo] `email_hash` con clave compartida**: usa `ENCRYPTION_KEY`; rotar la clave invalidaría hashes e index. Se asume clave estable; rotación de clave es un procedimiento operativo separado (re-cifrado + re-hash) fuera de scope.
- **[Trade-off] Columna `email_hash` extra**: agrega una columna por la limitación de GCM no determinístico; es el costo de poder indexar unicidad sin exponer plaintext.
- **[Riesgo] Migración 007 sobre DB con 001-006**: solo agrega tablas nuevas (no destructiva); rollback borra `usuario` y `asignacion` y el seed de permisos si aplica.
- **[Trade-off] `Usuario` ≠ `User`**: duplica el concepto "email por tenant" en dos tablas temporalmente. Aceptado para no tocar auth (CRÍTico) en este change; se resuelve en un change/ADR futuro.
- **[Trade-off] ABM manual sin import masivo**: scope acotado para no bloquear el camino crítico.

## Migration Plan

1. Ejecutar `Migración 007` (`backend/alembic/versions/007_usuarios_y_asignaciones.py`):
   - Crea tabla `usuario` con columnas cifradas (`email`, `dni`, `cuil`, `cbu`, `alias_cbu` como `Text`), `email_hash` (`String`, indexado), `nombre`, `apellidos`, `banco`, `regional`, `legajo`, `legajo_profesional`, `facturador` (bool), `estado` (String) + columnas del mixin base.
   - Índice único `uq_usuario_tenant_email_hash` sobre `(tenant_id, email_hash)`.
   - Crea tabla `asignacion` con `usuario_id` (FK), `rol` (String), `materia_id`/`carrera_id`/`cohorte_id` (FK nullable, RESTRICT), `comisiones` (ARRAY/JSONB), `responsable_id` (FK self-ref nullable), `desde` (date), `hasta` (date nullable) + mixin base.
   - Índices de apoyo para filtros (`tenant_id`, `usuario_id`, `materia_id`, `responsable_id`).
2. Data-seed defensivo: si faltan, sembrar permisos `usuarios:gestionar`, `equipos:asignar`, `asignaciones:gestionar` y asignarlos (ADMIN; +COORDINADOR donde corresponde).
3. Rollback: `alembic downgrade -1` — borra `asignacion`, luego `usuario`, y el seed de permisos sembrado por esta migración (si aplica).

## Open Questions

*(ninguna bloqueante para este change. PA-25 (semántica NEXO) no bloquea: `NEXO` es un valor válido del enum de `rol` de negocio; su lógica de permisos vive en RBAC, fuera de scope aquí. La eventual unificación `Usuario`/`User` queda como ADR futuro, ver D-07.)*
