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
