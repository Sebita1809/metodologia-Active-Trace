## Context

C-05 introduce el log de auditoría append-only (E-AUD) y la impersonación legítima sobre una base ya provista por changes anteriores:

- **C-02**: `BaseTenantModel` (UUID PK, `tenant_id`, `created_at`, `updated_at`, `deleted_at` para soft-delete) y `BaseRepository[T]` que aplica scope de tenant + filtro `deleted_at IS NULL` en `_base_query()`.
- **C-03**: `CurrentUser` (DTO inmutable derivado del JWT), helpers de `security.py` (`create_access_token`, `verify_token` con `expected_scope`), y `get_current_user` que extrae identidad SOLO del JWT.
- **C-04**: RBAC fino — `RbacService.resolver_permisos_efectivos()`, `require_permission(clave, scope)` fail-closed, catálogo administrable (`roles`, `permisos`, `rol_permiso`, `usuario_rol`) y `rbac_seed` con la matriz base. Migración head actual: `004_rbac_catalog`.

Restricciones duras aplicables (CLAUDE.md): identidad SIEMPRE desde el JWT; multi-tenancy row-level; RBAC fail-closed; Routers→Services→Repositories→Models; tests sin mocks de DB; ≤500 LOC por archivo; una migración Alembic por cambio de schema; Pydantic `extra='forbid'`. Dominio **CRÍTICO**: requiere aprobación humana antes de implementar.

La matriz de capacidades (`03_actores_y_roles.md` §3.3) ya define que `auditoria:ver` lo tienen COORDINADOR (propio), ADMIN (global) y FINANZAS (global). `impersonacion:usar` no está en la matriz base de roles del dominio: es una capacidad de soporte/ADMIN que se asigna explícitamente.

## Goals / Non-Goals

**Goals:**
- Modelo `AuditLog` inmutable: sin `updated_at` ni `deleted_at`; nunca mutable ni soft-deletable.
- Inmutabilidad reforzada en DB (trigger), no solo por convención de aplicación.
- Helper/servicio de registro con código estandarizado y `filas_afectadas`, invocable desde cualquier service del dominio.
- Impersonación: permiso `impersonacion:usar`, sesión distinguible vía claim JWT, atribución al actor real, auditoría de inicio/fin.
- Consulta de auditoría protegida por `auditoria:ver` con semántica de alcance (propio/global) reutilizando el RBAC de C-04.

**Non-Goals:**
- No se implementa retención/rotación ni archivado del log (append-only sin límite, per `08 §3.4`).
- No se auditan TODAS las acciones del sistema en este change: C-05 entrega el mecanismo y los códigos; cada módulo de dominio (C-07+) instrumenta sus propias llamadas a `registrar(...)`.
- No se implementa UI de auditoría (frontend); solo el endpoint de consulta backend.
- No se cubre 2FA sobre impersonación ni límites temporales automáticos de sesión de impersonación (queda como pregunta abierta).

## Decisions

### D-01: `AuditLog` con mixin inmutable propio, NO `BaseTenantModel`
`BaseTenantModel` aporta `updated_at` (onupdate) y `deleted_at` (soft-delete), ambos incompatibles con append-only. Se define un mixin propio (`AuditBaseModel` o columnas directas en el modelo) que contribuye solo `id` (UUID PK), `tenant_id` (FK, indexado) y `fecha_hora`. No hay `updated_at` ni `deleted_at`.
- **Alternativa descartada**: heredar de `BaseTenantModel` e ignorar las columnas → deja `deleted_at`/`updated_at` presentes, abriendo la puerta a soft-delete/mutación accidental y contradiciendo el spec. Rechazada.

### D-02: Inmutabilidad reforzada con trigger PostgreSQL (`BEFORE UPDATE OR DELETE`)
La migración 005 crea una función trigger que hace `RAISE EXCEPTION` ante cualquier UPDATE o DELETE sobre `audit_log`. La inmutabilidad es contractual a nivel motor, no confiada a la app.
- **Alternativa descartada**: solo revocar permisos UPDATE/DELETE al rol de aplicación → frágil (depende de la config de roles del entorno) y no testeable de forma portable con la cuenta de migración. El trigger es explícito y testeable.
- **Trade-off**: un trigger bloquea también correcciones legítimas; es el comportamiento deseado para un log append-only.

### D-03: Repositorio append-only (`AuditLogRepository`) que NO hereda métodos de mutación
No se usa `BaseRepository[T]` (expone `update`/`soft_delete`). Se crea un repositorio dedicado con solo `crear(...)` y consultas (`listar(...)` con filtros y scope de tenant). Esto refuerza la inmutabilidad en la capa de aplicación además del trigger.
- **Alternativa descartada**: usar `BaseRepository` y "no llamar" update/soft_delete → la superficie de mutación existe y puede invocarse por error. Rechazada para un dominio CRÍTICO.

### D-04: `detalle` como JSONB
Per `08 §6` (JSONB para estructuras configurables) y E-AUD (`detalle: JSON`). Permite contexto heterogéneo por tipo de acción sin migrar schema por cada módulo.

### D-05: Código de acción como enum/`StrEnum` Python (`AccionAuditoria`)
El catálogo de códigos vive como `StrEnum` en `app/services/audit_codes.py` (o similar). El helper `registrar(...)` tipa el parámetro `accion: AccionAuditoria`, no `str` libre. La columna en DB es `String` (no enum nativo) para permitir extensión del catálogo sin migración, pero el helper valida contra el enum.
- **Alternativa descartada**: enum nativo PostgreSQL → cada código nuevo exige migración; el catálogo es administrable/evolutivo (`04 §Códigos de acción`). Rechazada.

### D-06: Impersonación expresada como claim en el access token
El access token de una sesión de impersonación incluye `actor_id` real en `sub` y un claim adicional `impersonando` = UUID del usuario impersonado (más, opcionalmente, los roles efectivos del impersonado para que el RBAC resuelva sus permisos). `verify_token` y `get_current_user` pueblan un nuevo campo `CurrentUser.impersonando_user_id` SOLO desde el JWT. La regla de oro se mantiene: identidad y modo de impersonación nunca vienen de un parámetro de la petición.
- **Decisión sobre permisos efectivos durante impersonación**: la sesión de impersonación resuelve permisos como el **usuario impersonado** (para reproducir su experiencia), pero la **atribución** de toda acción es al actor real. Esto se logra emitiendo el token con `tenant_id` y roles del impersonado en los claims de autorización, mientras `actor_id` (responsabilidad) se conserva aparte. → Surfacear a revisión humana: confirmar que el RBAC debe verse "como B" pero auditar "como A".

### D-07: Atribución en el helper de registro
`AuditService.registrar(...)` recibe el `CurrentUser` y deriva: `actor_id = current_user.user_id` (siempre el actor real), `impersonado_id = current_user.impersonando_user_id` (nullable). Ningún caller pasa `actor_id` manualmente — se toma de la sesión verificada. Esto garantiza que la atribución no pueda falsearse desde el dominio.

### D-08: `auditoria:ver` reutiliza la semántica de alcance de C-04
El endpoint de consulta declara `require_permission("auditoria:ver", scope="propio")`. El handler inspecciona `PermisoConcedido.alcance`: si `propio`, filtra `actor_id == current_user.user_id`; si `global`, devuelve todo el tenant. Reusa el patrón ya probado de C-04.

### D-09: `impersonacion:usar` y `auditoria:ver` se siembran como datos
Se extiende `rbac_seed` para incluir ambos permisos en el catálogo y su asignación en la matriz base (auditoria:ver → COORDINADOR/propio, ADMIN/global, FINANZAS/global; impersonacion:usar → ADMIN/global). No altera los requisitos del spec `rbac-catalog` (catálogo administrable), solo agrega filas semilla.

### D-10: Migración 005, revisa 004
`005_audit_log.py` con `down_revision = "004"`: tabla `audit_log`, índices (`tenant_id`; `tenant_id, fecha_hora`; `tenant_id, actor_id`), función + trigger de inmutabilidad. `downgrade()` elimina trigger, función y tabla.

## Risks / Trade-offs

- **[El trigger bloquea también migraciones futuras que toquen audit_log]** → Mitigación: las migraciones futuras que necesiten alterar la tabla deben deshabilitar/recrear el trigger dentro de la misma migración; documentarlo en la cabecera de 005.
- **[Sesión de impersonación con permisos del impersonado podría ampliar privilegios del actor]** → Mitigación: `impersonacion:usar` solo se asigna a ADMIN/soporte; el inicio se audita (`IMPERSONACION_INICIAR`); la sesión es distinguible y de vida corta (mismo TTL que access token, 15 min). Surfacear a revisión humana antes de implementar.
- **[`filas_afectadas` mal reportado por un caller]** → Mitigación: es responsabilidad del service que registra; los tests cubren el contrato del helper, no de cada caller. Documentar la convención.
- **[Crecimiento ilimitado del log (append-only sin retención)]** → Aceptado por diseño (`08 §3.4`: sin límite de retención). La partición/archivado es un non-goal de C-05; se revisará cuando el volumen lo exija.
- **[Datos PII en `detalle`]** → Mitigación: convención dura — nunca volcar campos `[cifrado]` (DNI, CBU, email) en texto plano dentro de `detalle`. Los callers registran identificadores opacos (UUID), no PII.

## Migration Plan

1. Aplicar `005_audit_log` (crea tabla, índices, función trigger, trigger). Idempotente respecto a tenants (no siembra filas de log).
2. Aplicar la extensión de `rbac_seed` (datos): los nuevos permisos se siembran para tenants existentes — evaluar si se hace en 005 (siguiendo el patrón de 004) o en un seed idempotente separado.
3. **Rollback**: `downgrade()` de 005 elimina trigger → función → tabla. La extensión del seed RBAC se revierte borrando las filas de permiso sembradas (o se deja, al ser aditiva e inerte sin asignaciones de usuario).

## Open Questions

- **OQ-1**: Durante la impersonación, ¿el RBAC debe resolver permisos como el usuario impersonado (reproducir su vista) o conservar los del actor? D-06 propone "como el impersonado". Confirmar con stakeholder de seguridad antes de implementar.
- **OQ-2**: ¿La sesión de impersonación necesita un TTL más corto que el access token normal, o un mecanismo de finalización forzada server-side? Por ahora hereda el TTL de 15 min.
- **OQ-3**: ¿El seed de los nuevos permisos va dentro de la migración 005 (como 004) o en un seed separado ejecutable on-demand? Decidir según convención de despliegue del equipo.
