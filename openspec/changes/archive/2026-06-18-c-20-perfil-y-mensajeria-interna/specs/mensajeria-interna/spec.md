## ADDED Requirements

### Requirement: Mensajería interna entre usuarios registrados, separada de los emails a alumnos
El sistema SHALL modelar la mensajería interna mediante una entidad `Mensaje` distinta de la cola de comunicaciones a alumnos (`Comunicacion`). Cada `Mensaje` SHALL pertenecer a un `tenant_id`, un hilo (`thread_id`), un `remitente_id` (FK a usuarios, siempre desde el JWT) y un `destinatario_id` (FK a usuarios). El `remitente_id` NUNCA SHALL tomarse del body de la petición.

#### Scenario: Mensaje interno no se mezcla con la cola de emails a alumnos
- **WHEN** se crea un mensaje interno entre dos usuarios
- **THEN** el mensaje se persiste en la entidad `Mensaje` y no genera ningún registro en la cola `Comunicacion`

#### Scenario: El remitente se fija desde el JWT
- **WHEN** un usuario autenticado envía un mensaje interno
- **THEN** el `remitente_id` del mensaje persistido es el `user_id` del JWT, ignorando cualquier remitente provisto en el body

### Requirement: Usuario puede listar los hilos de mensajes recibidos
El sistema SHALL exponer `GET /api/inbox` para que el usuario autenticado liste los hilos en los que es destinatario, dentro de su tenant. El listado SHALL acotarse al `tenant_id` y al `user_id` del JWT.

#### Scenario: El inbox lista solo hilos donde el usuario es destinatario
- **WHEN** un usuario autenticado hace GET a `/api/inbox`
- **THEN** el sistema retorna únicamente los hilos en los que el usuario figura como destinatario, agrupados por `thread_id`

#### Scenario: El inbox no muestra hilos de otros usuarios
- **WHEN** existe un hilo entre dos usuarios distintos del solicitante
- **THEN** ese hilo no aparece en el inbox del solicitante

#### Scenario: Petición sin token es rechazada
- **WHEN** se hace GET a `/api/inbox` sin token de autenticación
- **THEN** el sistema retorna HTTP 401

### Requirement: Usuario puede leer un hilo en el que participa
El sistema SHALL exponer `GET /api/inbox/{thread_id}` para que el usuario autenticado lea todos los mensajes de un hilo en el que participa (como remitente o destinatario de algún mensaje del hilo), ordenados cronológicamente. Si el usuario no participa en el hilo, o el hilo es de otro tenant, el sistema SHALL retornar HTTP 404.

#### Scenario: Participante lee el hilo completo
- **WHEN** un usuario autenticado hace GET a `/api/inbox/{thread_id}` de un hilo en el que participa
- **THEN** el sistema retorna HTTP 200 con todos los mensajes del hilo ordenados por fecha de creación ascendente

#### Scenario: No participante recibe 404
- **WHEN** un usuario autenticado hace GET a `/api/inbox/{thread_id}` de un hilo en el que NO participa
- **THEN** el sistema retorna HTTP 404

#### Scenario: Hilo de otro tenant retorna 404
- **WHEN** un usuario autenticado intenta leer un hilo perteneciente a otro tenant
- **THEN** el sistema retorna HTTP 404

### Requirement: Abrir un mensaje lo marca como leído
El sistema SHALL marcar como leídos (`leido_at` no nulo) los mensajes de un hilo dirigidos al usuario actual cuando este lee el hilo. Los mensajes enviados por el propio usuario no cambian su estado de lectura.

#### Scenario: Mensajes recibidos se marcan leídos al abrir el hilo
- **WHEN** un usuario autenticado lee un hilo con mensajes recibidos no leídos
- **THEN** el sistema setea `leido_at` en los mensajes cuyo `destinatario_id` es el usuario actual

### Requirement: Usuario puede responder dentro de un hilo
El sistema SHALL exponer `POST /api/inbox/{thread_id}/responder` para que un participante agregue una respuesta al hilo. El nuevo mensaje SHALL reusar el `thread_id` del hilo, fijar `remitente_id` desde el JWT y `destinatario_id` = el otro participante del hilo. El `asunto` se hereda del hilo y no se acepta desde el cliente. Responder a un hilo inexistente o ajeno SHALL retornar HTTP 404.

#### Scenario: Participante responde y la respuesta se agrega al hilo
- **WHEN** un usuario autenticado hace POST a `/api/inbox/{thread_id}/responder` con un `cuerpo` válido
- **THEN** el sistema crea un nuevo `Mensaje` con el mismo `thread_id`, `remitente_id` = usuario actual y `destinatario_id` = el otro participante, y retorna HTTP 201

#### Scenario: Responder a un hilo ajeno es rechazado
- **WHEN** un usuario autenticado hace POST a `/api/inbox/{thread_id}/responder` sobre un hilo en el que NO participa
- **THEN** el sistema retorna HTTP 404 y no crea ningún mensaje

#### Scenario: La respuesta hereda el asunto del hilo
- **WHEN** un usuario responde dentro de un hilo
- **THEN** el asunto del hilo se conserva y no puede ser sobrescrito desde el body de la respuesta

### Requirement: La mensajería interna está aislada por tenant
El sistema SHALL filtrar todas las consultas de `Mensaje` por el `tenant_id` derivado del JWT. Ningún mensaje ni hilo de un tenant puede ser leído, listado ni respondido por un usuario de otro tenant.

#### Scenario: Listado de inbox acotado al tenant del solicitante
- **WHEN** un usuario autenticado lista su inbox
- **THEN** el sistema retorna únicamente mensajes cuyo `tenant_id` coincide con el del JWT

#### Scenario: No se puede responder a un mensaje de otro tenant
- **WHEN** un usuario intenta responder a un hilo de otro tenant
- **THEN** el sistema retorna HTTP 404
