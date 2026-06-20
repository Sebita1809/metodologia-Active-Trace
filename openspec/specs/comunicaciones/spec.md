## Requirements

### Requirement: Modelo Comunicacion con ciclo de vida de estados

El sistema SHALL persistir la entidad `Comunicacion` (E21) con los campos: `id` (UUID PK), `tenant_id` (UUID), `enviado_por` (UUID FK Usuario), `materia_id` (UUID FK Materia), `destinatario` (texto, email del alumno cifrado AES-256 en reposo), `asunto` (texto), `cuerpo` (texto enriquecido), `estado` (enum `Pendiente | Enviando | Enviado | Error | Cancelado`), `lote_id` (UUID), `enviado_at` (fecha-hora nullable), más los campos de `BaseMixin` (`created_at`, `updated_at`, `deleted_at` para soft delete). El `estado` inicial al crearse SHALL ser `Pendiente`. El ciclo de vida válido (RN-15) SHALL ser: `Pendiente → Enviando`, `Pendiente → Cancelado`, `Enviando → Enviado`, `Enviando → Error`. Toda otra transición SHALL ser rechazada con un error de dominio. Solo un mensaje en estado `Pendiente` SHALL poder cancelarse.

#### Scenario: comunicacion nace en estado Pendiente

- **WHEN** se crea una `Comunicacion`
- **THEN** su `estado` es `Pendiente` y su `enviado_at` es nulo

#### Scenario: transición válida Pendiente a Enviando

- **WHEN** se aplica la transición `Pendiente → Enviando` sobre una comunicación
- **THEN** la transición se acepta y el estado pasa a `Enviando`

#### Scenario: transición válida Enviando a Enviado

- **WHEN** se aplica la transición `Enviando → Enviado` sobre una comunicación
- **THEN** la transición se acepta, el estado pasa a `Enviado` y se registra `enviado_at`

#### Scenario: transición válida Enviando a Error

- **WHEN** el despacho falla y se aplica `Enviando → Error`
- **THEN** la transición se acepta y el estado pasa a `Error`

#### Scenario: cancelar solo es válido desde Pendiente

- **WHEN** se intenta cancelar una comunicación en estado `Pendiente`
- **THEN** la transición `Pendiente → Cancelado` se acepta

#### Scenario: cancelar desde Enviando es rechazado

- **WHEN** se intenta cancelar una comunicación en estado `Enviando`, `Enviado` o `Error`
- **THEN** el sistema rechaza la transición con un error de dominio y el estado no cambia

#### Scenario: transición inválida es rechazada

- **WHEN** se intenta una transición fuera del ciclo válido (p. ej. `Enviado → Pendiente`)
- **THEN** el sistema rechaza la transición con un error de dominio

### Requirement: Destinatario cifrado AES-256 en reposo

El sistema SHALL cifrar el campo `destinatario` (email del alumno, PII) con `CryptoService` (AES-256-GCM) antes de persistirlo. El valor en la base de datos SHALL ser ciphertext, nunca el email en claro. El descifrado SHALL ocurrir únicamente en la capa de presentación al construir la respuesta para un usuario autorizado.

#### Scenario: destinatario se persiste cifrado

- **WHEN** se encola una comunicación con `destinatario = "alumno@ejemplo.com"`
- **THEN** el valor almacenado en la columna `destinatario` es ciphertext, no el texto plano

#### Scenario: destinatario se descifra al leer

- **WHEN** un usuario autorizado lee una comunicación
- **THEN** el `destinatario` en la respuesta es el email en claro original

### Requirement: Preview obligatorio con sustitución de variables

El sistema SHALL exponer un endpoint de preview que renderice `asunto` y `cuerpo` sustituyendo variables de plantilla (p. ej. `{{nombre_alumno}}`, `{{materia}}`) por sus valores reales (F3.1, RN-16). El preview NO SHALL persistir ninguna `Comunicacion`. El encolado SHALL requerir que el cliente haya obtenido un preview; sin preview no hay despacho (RN-16). Requiere permiso `comunicacion:enviar`.

#### Scenario: preview renderiza variables

- **WHEN** un usuario con permiso `comunicacion:enviar` solicita preview de una plantilla con `{{nombre_alumno}}` para un alumno llamado "Ana"
- **THEN** el sistema retorna el texto con "Ana" sustituido y no crea ninguna `Comunicacion`

#### Scenario: preview no persiste

- **WHEN** se solicita un preview
- **THEN** no se crea ninguna fila en la tabla `comunicacion`

#### Scenario: variable ausente se deja literal

- **WHEN** la plantilla referencia una variable que no está en el contexto
- **THEN** el token se conserva sin sustituir y el render no falla

#### Scenario: preview sin permiso retorna 403

- **WHEN** un usuario sin permiso `comunicacion:enviar` solicita un preview
- **THEN** el sistema responde HTTP 403

### Requirement: Encolar lote de comunicaciones

El sistema SHALL exponer un endpoint que, dado un conjunto de destinatarios y una plantilla, cree una `Comunicacion` por destinatario en estado `Pendiente`, todas con un mismo `lote_id` (UUID generado), de forma atómica (F3.2, FL-02 pasos 7-8). La identidad del remitente (`enviado_por`) y el `tenant_id` SHALL derivarse del JWT, nunca de la petición. Al confirmar el encolado, el sistema SHALL emitir un único evento de auditoría `COMUNICACION_ENVIAR`. Requiere permiso `comunicacion:enviar`.

#### Scenario: encolar crea un mensaje por destinatario

- **WHEN** un usuario con permiso `comunicacion:enviar` encola un lote para 3 destinatarios
- **THEN** se crean 3 `Comunicacion` en estado `Pendiente`, todas con el mismo `lote_id`

#### Scenario: enviado_por proviene del JWT

- **WHEN** se encola un lote
- **THEN** `enviado_por` y `tenant_id` corresponden al usuario y tenant del JWT, ignorando cualquier valor en el body

#### Scenario: encolar emite auditoría

- **WHEN** se confirma un encolado
- **THEN** se registra un único `AuditLog` con acción `COMUNICACION_ENVIAR`

#### Scenario: encolar es atómico

- **WHEN** el encolado de un lote falla a mitad de la creación
- **THEN** no queda ninguna `Comunicacion` parcial del lote persistida

#### Scenario: encolar sin permiso retorna 403

- **WHEN** un usuario sin permiso `comunicacion:enviar` intenta encolar
- **THEN** el sistema responde HTTP 403

### Requirement: Aprobación administrativa de envíos masivos

El sistema SHALL permitir aprobar o cancelar comunicaciones en estado `Pendiente`, a nivel de lote completo o por destinatario individual (F3.3, RN-17, FL-04). La aprobación SHALL registrar `aprobado_at` y `aprobado_por` (derivado del JWT). Cuando el tenant exige aprobación, una comunicación `Pendiente` sin `aprobado_at` NO SHALL ser despachable. La aprobación y la cancelación requieren permiso `comunicacion:aprobar`.

#### Scenario: aprobar lote completo

- **WHEN** un usuario con permiso `comunicacion:aprobar` aprueba un `lote_id`
- **THEN** todas las comunicaciones `Pendiente` de ese lote quedan con `aprobado_at` y `aprobado_por` seteados

#### Scenario: aprobar destinatario individual

- **WHEN** un aprobador aprueba una comunicación individual por su `id`
- **THEN** solo esa comunicación queda aprobada; el resto del lote permanece sin aprobar

#### Scenario: cancelar lote desde Pendiente

- **WHEN** un aprobador cancela un `lote_id`
- **THEN** las comunicaciones `Pendiente` del lote pasan a `Cancelado` y las que no están `Pendiente` no se modifican

#### Scenario: aprobacion proviene del JWT

- **WHEN** se aprueba una comunicación
- **THEN** `aprobado_por` corresponde al usuario del JWT, no a un valor de la petición

#### Scenario: aprobar sin permiso retorna 403

- **WHEN** un usuario sin permiso `comunicacion:aprobar` intenta aprobar o cancelar
- **THEN** el sistema responde HTTP 403

### Requirement: Tracking de estado por mensaje y por lote

El sistema SHALL exponer endpoints de consulta de la cola que retornen el estado de cada comunicación, filtrables por `lote_id` y por `estado` (F3.2). Los resultados SHALL estar restringidos al tenant del JWT. Requiere permiso `comunicacion:enviar` o `comunicacion:aprobar` para leer la cola.

#### Scenario: listar cola por lote

- **WHEN** un usuario autorizado consulta la cola filtrando por un `lote_id`
- **THEN** el sistema retorna las comunicaciones de ese lote con su `estado` actual

#### Scenario: filtrar por estado

- **WHEN** se consulta la cola filtrando por `estado = Pendiente`
- **THEN** solo se retornan las comunicaciones en estado `Pendiente`

#### Scenario: aislamiento por tenant

- **WHEN** se consulta la cola
- **THEN** solo se incluyen comunicaciones cuyo `tenant_id` coincide con el JWT; un `lote_id` de otro tenant retorna lista vacía o HTTP 404

#### Scenario: listar cola sin permiso retorna 403

- **WHEN** un usuario sin `comunicacion:enviar` ni `comunicacion:aprobar` consulta la cola
- **THEN** el sistema responde HTTP 403
