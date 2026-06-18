## ADDED Requirements

### Requirement: Modelo AuditLog
El sistema SHALL mantener un registro de auditoría en la tabla `audit_log`, con las siguientes columnas: `id` (UUID PK), `tenant_id`, `fecha_hora`, `actor_id` (UUID, referencia lógica al usuario que realizó la acción), `impersonado_id` (UUID nullable, referencia lógica al usuario impersonado), `materia_id` (UUID nullable, referencia lógica a una materia), `accion` (código estandarizado), `detalle` (JSONB nullable), `filas_afectadas` (integer nullable), `ip` (text nullable), `user_agent` (text nullable).

#### Scenario: Registrar acción con todos los campos
- **WHEN** se registra una acción con actor_id, tenant_id, accion, detalle JSON, filas_afectadas, ip y user_agent
- **THEN** el registro se persiste con todos los campos y un UUID único y timestamp de creación

#### Scenario: Registrar acción con solo campos obligatorios
- **WHEN** se registra una acción con solo actor_id, tenant_id y accion
- **THEN** el registro se persiste sin error y los campos opcionales son NULL

### Requirement: Append-only enforcement
El sistema SHALL impedir toda modificación o eliminación de registros en `audit_log`, tanto a nivel de aplicación como a nivel de base de datos.

#### Scenario: App rechaza update
- **WHEN** se intenta ejecutar un UPDATE sobre un registro de audit_log
- **THEN** la operación falla (el repositorio no expone método de update)

#### Scenario: App rechaza delete
- **WHEN** se intenta ejecutar un DELETE sobre un registro de audit_log
- **THEN** la operación falla (el repositorio no expone método de delete)

#### Scenario: DB trigger rechaza update directo
- **WHEN** se ejecuta un UPDATE directo sobre la tabla audit_log
- **THEN** el trigger de base de datos rechaza la operación con un error

#### Scenario: DB trigger rechaza delete directo
- **WHEN** se ejecuta un DELETE directo sobre la tabla audit_log
- **THEN** el trigger de base de datos rechaza la operación con un error

### Requirement: Helper audit_record
El sistema SHALL proveer una función `audit_record()` en el servicio de auditoría que permita registrar acciones con los parámetros: `db`, `actor_id`, `accion`, `tenant_id`, más parámetros opcionales (`impersonado_id`, `materia_id`, `detalle`, `filas_afectadas`, `ip`, `user_agent`).

#### Scenario: Registrar acción completa
- **WHEN** se llama a `audit_record()` con todos los parámetros
- **THEN** el registro se persiste en la tabla audit_log con todos los valores especificados

#### Scenario: Registrar acción mínima
- **WHEN** se llama a `audit_record()` solo con actor_id, accion y tenant_id
- **THEN** el registro se persiste sin error y los campos opcionales quedan como NULL

### Requirement: Catálogo de códigos de acción
El sistema SHALL definir un catálogo inicial de códigos de acción como un enum que incluya: `CALIFICACIONES_IMPORTAR`, `PADRON_CARGAR`, `COMUNICACION_ENVIAR`, `ASIGNACION_MODIFICAR`, `LIQUIDACION_CERRAR`, `IMPERSONACION_INICIAR`, `IMPERSONACION_FINALIZAR`.

#### Scenario: Códigos definidos como constantes
- **WHEN** se importa el catálogo de códigos
- **THEN** los 7 códigos están disponibles como valores del enum AuditAction

#### Scenario: Helper acepta enum AuditAction
- **WHEN** se llama a `audit_record()` con `accion=AuditAction.CALIFICACIONES_IMPORTAR`
- **THEN** la acción se registra correctamente con el código textual "CALIFICACIONES_IMPORTAR"

### Requirement: Filtros de consulta de audit-log
El sistema SHALL permitir consultar registros de auditoría con filtros por: rango de fechas, actor_id, materia_id, accion, y tenant_id (automático por el repositorio base).

#### Scenario: Consultar acciones por rango de fechas
- **WHEN** se consultan registros entre dos fechas para un tenant
- **THEN** se retornan solo los registros dentro del rango

#### Scenario: Consultar acciones de un actor específico
- **WHEN** se consultan registros filtrados por actor_id
- **THEN** se retornan solo los registros de ese actor

#### Scenario: Consultar acciones por código
- **WHEN** se consultan registros filtrados por accion
- **THEN** se retornan solo los registros con ese código de acción

### Requirement: Migración Alembic 004
El sistema SHALL incluir una migración Alembic (`004_audit_log`) que cree la tabla `audit_log` con sus columnas, índices y el trigger de append-only.

#### Scenario: Migración ejecutada
- **WHEN** se ejecuta `alembic upgrade head`
- **THEN** la tabla audit_log existe con todas sus columnas e índices

#### Scenario: Rollback de migración
- **WHEN** se ejecuta `alembic downgrade -1`
- **THEN** la tabla audit_log es eliminada junto con el trigger
