## ADDED Requirements

### Requirement: Registro append-only de acciones significativas
El sistema SHALL persistir cada acción significativa en una tabla `audit_log` scoped por `tenant_id`. Cada registro SHALL contener `fecha_hora`, `actor_id`, `impersonado_id` (nullable), `materia_id` (nullable), `accion` (código estandarizado), `detalle` (JSON), `filas_afectadas` (entero), `ip` y `user_agent`. El registro SHALL ser append-only: una vez creado, ningún campo puede modificarse ni el registro puede eliminarse.

#### Scenario: Acción registrada con código y filas afectadas
- **WHEN** un service del dominio registra una acción con código `CALIFICACIONES_IMPORTAR` y `filas_afectadas = 42`
- **THEN** existe en `audit_log`, para el tenant actor, un registro con `accion = "CALIFICACIONES_IMPORTAR"`, `filas_afectadas = 42`, `fecha_hora` poblada y `actor_id` igual al usuario autenticado

#### Scenario: Contexto adicional persistido como JSON
- **WHEN** una acción se registra con `detalle = {"materia": "PROG_I", "version": 3}`
- **THEN** el registro conserva ese objeto JSON consultable sin pérdida de estructura

### Requirement: Inmutabilidad reforzada en aplicación y en base de datos
El sistema SHALL impedir cualquier `UPDATE` o `DELETE` sobre `audit_log`. La inmutabilidad SHALL estar reforzada tanto en la capa de aplicación (el repositorio no expone `update` ni `soft_delete`) como en la base de datos (un mecanismo a nivel de motor rechaza UPDATE y DELETE). El modelo `AuditLog` NO SHALL definir columnas `updated_at` ni `deleted_at`.

#### Scenario: UPDATE rechazado a nivel de base de datos
- **WHEN** se intenta ejecutar un `UPDATE` directo sobre una fila de `audit_log`
- **THEN** la base de datos rechaza la operación con error y la fila permanece inalterada

#### Scenario: DELETE rechazado a nivel de base de datos
- **WHEN** se intenta ejecutar un `DELETE` directo sobre una fila de `audit_log`
- **THEN** la base de datos rechaza la operación con error y la fila permanece presente

#### Scenario: El repositorio no expone mutación
- **WHEN** se inspecciona el repositorio de auditoría
- **THEN** ofrece únicamente creación y consultas; no expone métodos de actualización ni de borrado (físico o lógico)

### Requirement: Aislamiento por tenant del log de auditoría
El sistema SHALL filtrar toda consulta de `audit_log` por `tenant_id` por defecto. Un tenant SHALL ver únicamente sus propios registros de auditoría.

#### Scenario: Un tenant no ve auditoría de otro
- **WHEN** el tenant A registra una acción y un usuario del tenant B consulta su auditoría
- **THEN** el registro del tenant A no aparece en los resultados del tenant B

### Requirement: Consulta de auditoría protegida por permiso fino
El sistema SHALL exigir el permiso `auditoria:ver` para consultar `audit_log`. Sin el permiso, el sistema SHALL responder 403 (fail-closed). El alcance del permiso SHALL acotar el resultado: alcance `global` ve toda la auditoría del tenant; alcance `propio` ve solo los registros donde el actor es el propio usuario.

#### Scenario: Sin permiso, acceso denegado
- **WHEN** un usuario sin `auditoria:ver` consulta el log de auditoría
- **THEN** el sistema responde 403 y no devuelve registros

#### Scenario: Alcance propio acota a los registros del propio actor
- **WHEN** un usuario con `auditoria:ver` de alcance `propio` consulta la auditoría
- **THEN** el sistema devuelve únicamente registros cuyo `actor_id` es el del propio usuario

#### Scenario: Alcance global ve toda la auditoría del tenant
- **WHEN** un usuario con `auditoria:ver` de alcance `global` consulta la auditoría
- **THEN** el sistema devuelve todos los registros del tenant, independientemente del actor

### Requirement: Códigos de acción estandarizados
El sistema SHALL usar un catálogo de códigos de acción estandarizados para el campo `accion`. El catálogo SHALL incluir al menos `CALIFICACIONES_IMPORTAR`, `PADRON_CARGAR`, `COMUNICACION_ENVIAR`, `ASIGNACION_MODIFICAR`, `LIQUIDACION_CERRAR`, `IMPERSONACION_INICIAR` e `IMPERSONACION_FINALIZAR`. El helper de registro SHALL aceptar el código como un valor del catálogo, no como texto libre arbitrario.

#### Scenario: Código fuera del catálogo es inválido
- **WHEN** un service intenta registrar una acción con un código que no pertenece al catálogo
- **THEN** el helper de auditoría rechaza el registro
