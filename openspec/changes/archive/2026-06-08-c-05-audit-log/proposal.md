## Why

El nombre del producto es *trace*: toda acción significativa debe quedar registrada y atribuida de forma inmutable. Hoy el sistema tiene identidad (C-03) y RBAC fino (C-04), pero ninguna acción deja rastro auditable. Sin un log de auditoría append-only no hay trazabilidad legal ni operativa, y la impersonación legítima (soporte/ADMIN operando "en nombre de" otro) no puede habilitarse de forma segura porque rompería la atribución de responsabilidad. C-05 cierra ese hueco fundacional antes de que los módulos de dominio (calificaciones, padrón, comunicaciones, liquidaciones) empiecen a producir acciones que deben auditarse.

## What Changes

- **Modelo `AuditLog` (E-AUD) append-only**: registro inmutable con `actor_id`, `impersonado_id`, `materia_id`, `accion` (código estandarizado), `detalle` (JSONB), `filas_afectadas`, `ip`, `user_agent`, `fecha_hora`. Sin `updated_at` ni `deleted_at`: no inicia de `BaseTenantModel` (que es mutable y soft-deletable). **BREAKING respecto del patrón base de modelos**: es el primer modelo que define su propio mixin inmutable.
- **Inmutabilidad reforzada en DB**: trigger PostgreSQL que rechaza `UPDATE` y `DELETE` sobre `audit_log`, no solo una convención de aplicación. La inmutabilidad es contractual, no confiada a la capa de app.
- **Servicio de auditoría (`AuditService`) + helper de registro**: API estable `registrar(...)` para que cualquier service del dominio emita un registro con código estandarizado y `filas_afectadas`. Repositorio append-only (solo `create` y consultas; sin `update`/`soft_delete`).
- **Catálogo de códigos de acción**: enum/constantes Python con los códigos estandarizados (`CALIFICACIONES_IMPORTAR`, `PADRON_CARGAR`, `COMUNICACION_ENVIAR`, `ASIGNACION_MODIFICAR`, `LIQUIDACION_CERRAR`, `IMPERSONACION_INICIAR`, `IMPERSONACION_FINALIZAR`).
- **Impersonación (suplantación legítima)**: permiso `impersonacion:usar` (sembrado en el catálogo RBAC); endpoints para iniciar/finalizar impersonación; sesión distinguible (claim `impersonando` en el JWT). **Toda acción bajo impersonación se atribuye al actor real** (`actor_id` = quien impersona) y registra al impersonado (`impersonado_id`). Inicio y fin se auditan (`IMPERSONACION_INICIAR` / `IMPERSONACION_FINALIZAR`).
- **`CurrentUser` extendido**: nuevo campo opcional `impersonando_user_id` derivado exclusivamente del JWT verificado, nunca de un parámetro de la petición.
- **`Migración 005: audit_log`**: tabla, índices por tenant + actor + fecha, trigger de inmutabilidad. (La cabecera de migración actual es `004`; el número siguiente es `005`.)
- **Auditoría de la lectura de auditoría**: el endpoint de consulta exige `auditoria:ver`; COORDINADOR la ve con alcance `propio`, ADMIN/FINANZAS con alcance `global`.

## Capabilities

### New Capabilities
- `audit-log`: registro inmutable append-only de acciones significativas con código estandarizado, atribución de actor/impersonado, `filas_afectadas`, contexto JSON, IP y user-agent; inmutabilidad reforzada en aplicación y en DB; consulta scoped por tenant y permiso `auditoria:ver`.
- `impersonation`: suplantación legítima permisada (`impersonacion:usar`), sesión distinguible, atribución de toda acción al actor real, y registro auditado de inicio/fin de impersonación.

### Modified Capabilities
<!-- No cambian requisitos de specs existentes. La nueva clave de permiso `impersonacion:usar` y `auditoria:ver` se siembran como datos del catálogo (rbac-catalog ya admite catálogo administrable); no altera los requisitos del spec rbac-catalog ni auth-dependency. -->

## Impact

- **Modelos**: nuevo `backend/app/models/audit_log.py` (mixin inmutable propio, no `BaseTenantModel`); registro en `models/__init__.py`.
- **Migraciones**: nueva `backend/alembic/versions/005_audit_log.py` (revisa `004`), con trigger de inmutabilidad.
- **Repositorio**: nuevo `backend/app/repositories/audit_log.py` append-only (sin update/delete).
- **Servicios**: nuevo `backend/app/services/audit_service.py` (helper `registrar`) y `backend/app/services/impersonation_service.py`.
- **Core**: `backend/app/core/auth_context.py` (campo `impersonando_user_id`), `backend/app/core/security.py` (claim `impersonando` en el access token), `backend/app/core/dependencies.py` (poblar el nuevo campo desde el JWT).
- **API**: nuevos endpoints de impersonación (iniciar/finalizar) y de consulta de auditoría bajo `app/api/v1/routers/`.
- **Catálogo RBAC (datos)**: seed de `auditoria:ver` e `impersonacion:usar` y su asignación en la matriz base (`rbac_seed`).
- **Tests**: append-only (UPDATE/DELETE rechazados a nivel DB y app), atribución bajo impersonación, registro de acción con código + `filas_afectadas`, aislamiento por tenant en la consulta.
- **Governance**: dominio **CRÍTICO** (auth/audit). Requiere aprobación humana explícita antes de implementar.
