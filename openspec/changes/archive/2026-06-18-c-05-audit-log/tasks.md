## 1. Modelos y Migración

- [x] 1.1 Crear modelo `AuditLog` (SQLAlchemy): `id` (UUID PK), `tenant_id` (UUID, NOT NULL), `fecha_hora` (DateTime con timezone, server_default now()), `actor_id` (UUID, NOT NULL — referencia lógica), `impersonado_id` (UUID, nullable), `materia_id` (UUID, nullable), `accion` (String(50), NOT NULL), `detalle` (JSONB, nullable), `filas_afectadas` (Integer, nullable), `ip` (String(45), nullable), `user_agent` (String(500), nullable). Sin `deleted_at` (append-only). Sin FK a usuario ni materia (referencias lógicas).
- [x] 1.2 Crear enum `AuditAction` (StrEnum) en `app/core/audit_codes.py` con los 7 códigos: CALIFICACIONES_IMPORTAR, PADRON_CARGAR, COMUNICACION_ENVIAR, ASIGNACION_MODIFICAR, LIQUIDACION_CERRAR, IMPERSONACION_INICIAR, IMPERSONACION_FINALIZAR
- [x] 1.3 Agregar `AuditLog` al `__init__.py` de modelos
- [x] 1.4 Generar migración Alembic 004 con `alembic revision --autogenerate -m "004_audit_log"`
- [x] 1.5 Revisar la migración autogenerada: verificar tipos (JSONB), agregar índices `(tenant_id, fecha_hora)`, `actor_id`, `accion`, y agregar el trigger de append-only (función `reject_audit_modify()` + `CREATE TRIGGER` BEFORE UPDATE OR DELETE)

## 2. Servicio de Auditoría (Helper)

- [x] 2.1 Implementar función `audit_record(db, actor_id, accion, *, tenant_id, impersonado_id, materia_id, detalle, filas_afectadas, ip, user_agent)` en `app/services/audit/audit_service.py` que crea y persiste un AuditLog
- [x] 2.2 Implementar dependencia `get_request_metadata(request: Request)` en `app/core/dependencies.py` que extrae IP y User-Agent del request HTTP
- [x] 2.3 Escribir test: `audit_record` registra correctamente con todos los campos
- [x] 2.4 Escribir test: `audit_record` registra correctamente solo con campos obligatorios

## 3. Sistema de Impersonación

- [x] 3.1 Extender `UserContext` en `app/core/dependencies.py` con `is_impersonating: bool = False`, `actor_id: uuid.UUID | None = None`, `impersonated_user_id: uuid.UUID | None = None`
- [x] 3.2 Extender `create_access_token()` en `app/core/security.py` con parámetro opcional `impersonated_user_id` y tipo `"impersonation"` en lugar de `"access"`. Los claims adicionales: `actor_id` (quien impersona), `impersonated_user_id` (quien es impersonado).
- [x] 3.3 Extender `get_current_user()` en `app/core/dependencies.py` para detectar JWT tipo `"impersonation"` y llenar los campos extras del UserContext
- [x] 3.4 Implementar endpoint `POST /api/v1/impersonacion/iniciar` que: (a) requiere `impersonacion:usar`, (b) recibe `usuario_id` a impersonar, (c) verifica que el usuario existe en el mismo tenant, (d) registra `IMPERSONACION_INICIAR` en audit-log, (e) devuelve JWT tipo impersonation
- [x] 3.5 Implementar endpoint `POST /api/v1/impersonacion/finalizar` que: (a) requiere estar en sesión de impersonación, (b) registra `IMPERSONACION_FINALIZAR` en audit-log, (c) devuelve JWT tipo access normal para el usuario real
- [x] 3.6 Escribir test: iniciar impersonación exitosamente → 200 + JWT tipo impersonation
- [x] 3.7 Escribir test: iniciar impersonación sin permiso → 403
- [x] 3.8 Escribir test: finalizar impersonación → 200 + JWT tipo access normal
- [x] 3.9 Escribir test: acción bajo impersonación registra actor_id real e impersonado_id en audit-log

## 4. Append-only Enforcement

- [x] 4.1 Implementar repositorio `AuditLogRepository` (o usar helper directo) que solo exponga `add()` y `list()` — sin `update()` ni `delete()`
- [x] 4.2 Escribir test: app rechaza UPDATE sobre audit_log (404 o error de repositorio)
- [x] 4.3 Escribir test: app rechaza DELETE sobre audit_log (404 o error de repositorio)
- [x] 4.4 Escribir test: trigger de DB rechaza UPDATE directo sobre la tabla
- [x] 4.5 Escribir test: trigger de DB rechaza DELETE directo sobre la tabla

## 5. Consultas y Filtros

- [x] 5.1 Implementar función `list_audit_logs(db, tenant_id, *, fecha_desde, fecha_hasta, actor_id, accion, limit, offset)` que retorna registros paginados con filtros opcionales
- [x] 5.2 Escribir test: filtrar por rango de fechas retorna solo registros en el rango
- [x] 5.3 Escribir test: filtrar por actor_id retorna solo registros de ese actor
- [x] 5.4 Escribir test: filtrar por accion retorna solo registros con ese código
- [x] 5.5 Escribir test: paginación (limit + offset) funciona correctamente
