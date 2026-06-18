## Why

Sin un audit-log centralizado no hay trazabilidad de acciones significativas en el sistema. C-04 (RBAC) ya define quién puede hacer qué, pero no registra qué se hizo, cuándo, ni sobre qué datos. C-05 resuelve esto implementando un registro de auditoría append-only con inmutabilidad a nivel app y DB, necesario antes de que cualquier módulo de dominio (C-06 en adelante) empiece a generar acciones auditables. También incorpora el sistema de impersonación (suplantación legítima), que depende del audit-log para su trazabilidad.

## What Changes

- **Modelo `AuditLog` append-only**: tabla con `actor_id`, `impersonado_id`, `materia_id`, `accion`, `detalle` (JSONB), `filas_afectadas`, `ip`, `user_agent`, `fecha_hora`. Sin update ni delete — ni a nivel app ni a nivel DB.
- **Helper de auditoría**: función `audit_record()` o decorador que cualquier service/router puede llamar para registrar una acción con código estandarizado.
- **Catálogo inicial de códigos de acción**: `CALIFICACIONES_IMPORTAR`, `PADRON_CARGAR`, `COMUNICACION_ENVIAR`, `ASIGNACION_MODIFICAR`, `LIQUIDACION_CERRAR`, `IMPERSONACION_INICIAR`, `IMPERSONACION_FINALIZAR` como constantes/enum.
- **Sistema de impersonación**:
  - Endpoints `POST /impersonacion/iniciar` y `POST /impersonacion/finalizar`
  - Sesión distinguible (tipo `impersonation` en JWT) con `actor_id` real + `impersonado_id`
  - Toda acción bajo impersonación registra ambos IDs en AuditLog
  - Requiere permiso `impersonacion:usar` (ya seedeado en C-04)
- **Enforcement de append-only en DB**: trigger o política que rechaza UPDATE/DELETE sobre `audit_log`.
- **Migración 004**: creación de `audit_log`.
- **Tests**: append-only (update/delete rechazados), atribución bajo impersonación, registro con código + filas afectadas.

## Capabilities

### New Capabilities
- `audit-log`: Registro centralizado append-only de acciones de usuarios. Modelo AuditLog con inmutabilidad, helper de registro, catálogo de códigos de acción. Consultas con filtros por rango de fechas, actor, materia, acción.
- `impersonation`: Suplantación legítima de usuarios. Sesión distinguible, endpoints de iniciar/finalizar, registro obligatorio en audit-log con actor real e impersonado.

### Modified Capabilities
- *(Ninguna — C-04 no cambia; el RBAC ya incluye `impersonacion:usar` y `auditoria:ver` como permisos)*

## Impact

- **Nuevo modelo**: `AuditLog` en `app/models/audit_log.py`
- **Nuevo servicio**: `app/services/audit/audit_service.py` (helper de registro)
- **Nuevos endpoints de impersonación**: `app/api/v1/routers/impersonacion.py`
- **Nuevo helper**: `app/core/audit.py` o integrado en service con función `audit_record()`
- **Migración**: `004_audit_log.py` en Alembic + trigger/constraint append-only
- **Catálogo de códigos**: `app/core/audit_codes.py` (enum o constantes)
- **Tests**: `tests/test_audit_log.py` (append-only, impersonación, helper)
- **Modificación en auth**: JWT/extender `create_session` para soportar tipo `impersonation` con `actor_id` y `impersonado_id`
