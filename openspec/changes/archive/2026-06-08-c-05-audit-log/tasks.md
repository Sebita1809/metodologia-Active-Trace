## 1. Aprobación previa (dominio CRÍTICO)

- [x] 1.1 Surfacear a revisión humana las decisiones D-06 (RBAC "como impersonado" vs "como actor") y OQ-1/OQ-2/OQ-3; esperar aprobación explícita antes de escribir código
- [x] 1.2 Confirmar el número de migración siguiente (`005`, revisa `004`) y la convención de seed (dentro de la migración vs. seed separado, OQ-3)

## 2. Catálogo de códigos de acción

- [x] 2.1 Test: `AccionAuditoria` (StrEnum) contiene los 7 códigos del spec (CALIFICACIONES_IMPORTAR, PADRON_CARGAR, COMUNICACION_ENVIAR, ASIGNACION_MODIFICAR, LIQUIDACION_CERRAR, IMPERSONACION_INICIAR, IMPERSONACION_FINALIZAR)
- [x] 2.2 Implementar `app/services/audit_codes.py` con el StrEnum `AccionAuditoria` (mínimo para pasar el test)
- [x] 2.3 Test: el helper de registro rechaza un código fuera del catálogo

## 3. Modelo AuditLog (inmutable, sin BaseTenantModel)

- [x] 3.1 Test: `AuditLog` expone `id`, `tenant_id`, `fecha_hora`, `actor_id`, `impersonado_id` (nullable), `materia_id` (nullable), `accion`, `detalle` (JSON), `filas_afectadas`, `ip`, `user_agent`
- [x] 3.2 Test: `AuditLog` NO define `updated_at` ni `deleted_at`
- [x] 3.3 Implementar `app/models/audit_log.py` con mixin/columnas inmutables propias (no hereda `BaseTenantModel`); `detalle` como JSONB
- [x] 3.4 Registrar `AuditLog` en `app/models/__init__.py`

## 4. Migración 005 (tabla + trigger de inmutabilidad)

- [x] 4.1 Crear `alembic/versions/005_audit_log.py` (`down_revision = "004"`): tabla `audit_log` + índices (`tenant_id`; `tenant_id, fecha_hora`; `tenant_id, actor_id`)
- [x] 4.2 Añadir función trigger PostgreSQL `BEFORE UPDATE OR DELETE` que hace `RAISE EXCEPTION`, y crear el trigger sobre `audit_log`
- [x] 4.3 Implementar `downgrade()`: drop trigger → drop función → drop tabla
- [x] 4.4 Test de integración: aplicar la migración sobre DB efímera; verificar que la tabla e índices existen
- [x] 4.5 Test: `UPDATE` directo sobre `audit_log` es rechazado por la DB (la fila permanece inalterada)
- [x] 4.6 Test: `DELETE` directo sobre `audit_log` es rechazado por la DB (la fila permanece presente)

## 5. Repositorio append-only

- [x] 5.1 Test: `AuditLogRepository` expone solo `crear` y consultas; no expone `update` ni `soft_delete`
- [x] 5.2 Test: `crear(...)` persiste un registro scoped al tenant del repositorio
- [x] 5.3 Implementar `app/repositories/audit_log.py` (no hereda `BaseRepository`; scope de tenant en las consultas)
- [x] 5.4 Test: una consulta del tenant A no devuelve registros del tenant B (aislamiento)

## 6. Servicio/helper de auditoría

- [x] 6.1 Test: `AuditService.registrar(...)` toma `actor_id` de `CurrentUser.user_id` (no de un parámetro) y persiste `accion` + `filas_afectadas`
- [x] 6.2 Test: `detalle` se persiste y recupera como JSON sin pérdida de estructura
- [x] 6.3 Test: sin impersonación, `impersonado_id` queda nulo; el registro lleva `actor_id` correcto
- [x] 6.4 Implementar `app/services/audit_service.py` con `registrar(current_user, accion, *, materia_id=None, detalle=None, filas_afectadas=0, ip, user_agent)`

## 7. Impersonación — sesión y contexto

- [x] 7.1 Test: `CurrentUser` acepta `impersonando_user_id` opcional (default None)
- [x] 7.2 Extender `app/core/auth_context.py` con `impersonando_user_id: uuid.UUID | None`
- [x] 7.3 Test: `security.py` emite un access token de impersonación con claim `impersonando` (actor real en `sub`, impersonado en el claim)
- [x] 7.4 Implementar el claim `impersonando` en la creación del token y su lectura en `verify_token`/`get_current_user` (SOLO desde el JWT)
- [x] 7.5 Test: `get_current_user` puebla `impersonando_user_id` desde el claim; una sesión normal lo deja en None
- [x] 7.6 Test: un parámetro/header de la petición que pretenda fijar el impersonado fuera del flujo es ignorado

## 8. Impersonación — servicio y endpoints

- [x] 8.1 Test: iniciar impersonación sin `impersonacion:usar` responde 403 (fail-closed)
- [x] 8.2 Test: iniciar impersonación con permiso emite token distinguible y registra `IMPERSONACION_INICIAR` (actor_id=A, impersonado_id=B)
- [x] 8.3 Test: finalizar impersonación registra `IMPERSONACION_FINALIZAR` (actor_id=A, impersonado_id=B)
- [x] 8.4 Implementar `app/services/impersonation_service.py` (iniciar/finalizar, integrando `AuditService`)
- [x] 8.5 Implementar el router de impersonación (iniciar/finalizar) con `require_permission("impersonacion:usar")` y schemas Pydantic `extra='forbid'`
- [x] 8.6 Test: una acción auditable ejecutada bajo sesión de impersonación queda atribuida al actor real (actor_id=A, impersonado_id=B)

## 9. Consulta de auditoría (endpoint protegido)

- [x] 9.1 Test: consultar auditoría sin `auditoria:ver` responde 403
- [x] 9.2 Test: alcance `propio` devuelve solo registros con `actor_id` del propio usuario
- [x] 9.3 Test: alcance `global` devuelve todos los registros del tenant
- [x] 9.4 Implementar el router de consulta con `require_permission("auditoria:ver", scope="propio")` y filtrado por `PermisoConcedido.alcance`; schemas de respuesta `extra='forbid'`
- [x] 9.5 Registrar los nuevos routers en la app FastAPI (`app/main.py` / agregador de routers v1)

## 10. Seed RBAC de los nuevos permisos (datos)

- [x] 10.1 Test: el seed incluye `auditoria:ver` (COORDINADOR/propio, ADMIN/global, FINANZAS/global) e `impersonacion:usar` (ADMIN/global)
- [x] 10.2 Extender `app/services/rbac_seed.py` con los nuevos permisos y asignaciones de la matriz base
- [x] 10.3 Test: el seed es idempotente (re-ejecutar no duplica permisos ni asignaciones)

## 11. Cierre

- [x] 11.1 Ejecutar toda la suite: 127 tests previos + los nuevos en verde; cobertura ≥80% líneas / ≥90% reglas de negocio
- [x] 11.2 Verificar ≤500 LOC por archivo backend nuevo/modificado
- [x] 11.3 Marcar `[x]` C-05 en `CHANGES.md` y dejar listo para `/opsx:archive`
