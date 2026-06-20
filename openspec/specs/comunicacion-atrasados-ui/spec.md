## ADDED Requirements

### Requirement: Selección de destinatarios atrasados

La feature SHALL permitir seleccionar uno o más alumnos atrasados desde la tabla de atrasados como destinatarios de una comunicación.

#### Scenario: Seleccionar destinatarios
- **WHEN** el usuario marca uno o más alumnos en la tabla de atrasados
- **THEN** esos alumnos quedan como destinatarios candidatos de la comunicación

#### Scenario: Sin destinatarios seleccionados
- **WHEN** el usuario intenta continuar sin seleccionar destinatarios
- **THEN** la UI bloquea el avance y solicita seleccionar al menos un destinatario

### Requirement: Previsualización de la comunicación

La feature SHALL presentar una previsualización del mensaje (asunto y cuerpo) personalizado por alumno antes del envío, consumiendo `POST /preview` de comunicaciones, conforme a RN-16.

#### Scenario: Mostrar preview por destinatario
- **WHEN** el usuario solicita previsualizar la comunicación para los destinatarios seleccionados
- **THEN** la UI muestra el asunto y cuerpo renderizados tal como los recibirá cada alumno, sin haber encolado nada

### Requirement: Envío a la cola de comunicaciones

La feature SHALL permitir confirmar el envío encolando el lote vía `POST /` de comunicaciones, recibiendo el `lote_id` del lote creado. La identidad del emisor sale exclusivamente del JWT.

#### Scenario: Encolar lote
- **WHEN** el usuario confirma el envío tras la previsualización
- **THEN** la UI envía el lote al backend y recibe un `lote_id`, dejando los mensajes en estado Pendiente

### Requirement: Tracking de estados en tiempo real

La feature SHALL hacer seguimiento del estado de cada mensaje del lote consumiendo `GET /` de comunicaciones por `lote_id`, refrescando mientras existan mensajes en estados no terminales (Pendiente/Enviando) y deteniendo el refresco cuando todos alcanzan un estado terminal (OK/Fallido/Cancelado).

#### Scenario: Transición de estados visible
- **WHEN** un mensaje del lote pasa de Pendiente a Enviando y luego a OK o Fallido
- **THEN** la UI refleja las transiciones de estado por destinatario sin recargar la página

#### Scenario: Detener polling al finalizar
- **WHEN** todos los mensajes del lote alcanzan un estado terminal (OK/Fallido/Cancelado)
- **THEN** la UI detiene el refresco periódico y muestra el resultado final por destinatario
## ADDED Requirements

### Requirement: Cola de aprobación de comunicaciones masivas

La feature SHALL presentar al COORDINADOR (o cualquier rol con permiso `comunicacion:aprobar`) la lista de lotes de comunicaciones en estado Pendiente que requieren aprobación, consumiendo `GET /api/v1/comunicaciones?estado=PENDIENTE`. Implementa F3.3 y FL-04 parte B.

#### Scenario: Ver lotes pendientes de aprobación
- **WHEN** el COORDINADOR accede al panel de aprobación de comunicaciones
- **THEN** la UI muestra los lotes pendientes con: docente emisor, materia, cantidad de destinatarios, fecha de creación

#### Scenario: Sin lotes pendientes
- **WHEN** no hay lotes en estado Pendiente
- **THEN** la UI muestra el estado vacío "sin comunicaciones pendientes de aprobación"

### Requirement: Aprobar lote de comunicaciones

La feature SHALL permitir al COORDINADOR aprobar un lote completo enviando `PUT /api/v1/comunicaciones/lotes/{id}/aprobar`, haciendo que los mensajes pasen a estado Enviando.

#### Scenario: Aprobar lote completo
- **WHEN** el COORDINADOR aprueba un lote de 40 mensajes
- **THEN** la UI actualiza el estado del lote a "Enviando" y lo mueve fuera de la cola de aprobación

### Requirement: Cancelar lote de comunicaciones

La feature SHALL permitir al COORDINADOR cancelar un lote completo enviando `PUT /api/v1/comunicaciones/lotes/{id}/cancelar`, marcando todos los mensajes como Cancelado.

#### Scenario: Cancelar lote
- **WHEN** el COORDINADOR cancela un lote
- **THEN** la UI muestra confirmación previa ("¿Confirmar cancelación de N mensajes?") y tras confirmar actualiza el estado a "Cancelado"

#### Scenario: No cancelar sin confirmación
- **WHEN** el COORDINADOR pulsa "Cancelar" pero descarta el diálogo
- **THEN** el lote permanece en estado Pendiente sin cambios
