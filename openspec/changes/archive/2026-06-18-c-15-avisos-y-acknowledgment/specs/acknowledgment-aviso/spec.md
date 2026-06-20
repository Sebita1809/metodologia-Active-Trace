## ADDED Requirements

### Requirement: Acuse de recibo de avisos (RN-19)

El sistema SHALL permitir a cualquier usuario destinatario acusar recibo de un aviso con `requiere_ack=true` vía `POST /api/avisos/{id}/ack`, registrando `confirmado_at` con el timestamp del servidor. El par `(aviso_id, usuario_id)` SHALL ser único (UNIQUE constraint): el sistema SHALL aceptar solo el primer acuse y rechazar duplicados con 409. El `usuario_id` SHALL derivarse siempre del JWT, nunca del body. Un aviso con `requiere_ack=false` puede ser acusado sin efecto en la visibilidad (idempotente).

#### Scenario: Acuse de lectura registrado correctamente

- **WHEN** un usuario destinatario envía `POST /api/avisos/{id}/ack` sobre un aviso con `requiere_ack=true`
- **THEN** el sistema crea un `AcknowledgmentAviso` con `confirmado_at=now()` y responde 201

#### Scenario: Segundo acuse es rechazado con 409

- **WHEN** el mismo usuario intenta acusar el mismo aviso por segunda vez
- **THEN** el sistema responde 409 (UNIQUE constraint)

#### Scenario: usuario_id proviene del JWT

- **WHEN** se emite un acuse
- **THEN** `usuario_id` en `AcknowledgmentAviso` corresponde al usuario del JWT, ignorando cualquier valor en el body

### Requirement: Contadores de ack derivados (sin denormalización)

El sistema SHALL exponer contadores de `total_destinatarios_estimados` y `total_acks` en la vista de administración del aviso, derivados mediante queries agregadas sobre `AcknowledgmentAviso`. NO SHALL denormalizar estos conteos en la tabla `aviso`. Los contadores SHALL reflejar el estado real en tiempo de consulta.

#### Scenario: Contador de acks refleja los acuses reales

- **WHEN** 3 usuarios acusaron recibo de un aviso
- **THEN** la vista de administración del aviso retorna `total_acks=3`

#### Scenario: Sin acuses el contador es cero

- **WHEN** nadie acusó recibo de un aviso
- **THEN** la vista de administración retorna `total_acks=0`

### Requirement: Solo el destinatario puede acusar su propio aviso

El sistema SHALL validar que el usuario que emite el acuse sea parte de la audiencia del aviso (alcance + rol). Si el aviso no está dirigido al rol/cohorte/materia del usuario, SHALL responder 403. Un aviso inactivo o fuera de ventana SHALL responder 404 o 403 (el usuario no ve el aviso, por lo tanto no puede acusarlo).

#### Scenario: Acuse de aviso no dirigido al rol del usuario es rechazado

- **WHEN** un usuario con rol PROFESOR intenta acusar un aviso con `alcance='PorRol'` y `rol_destino='ALUMNO'`
- **THEN** el sistema responde 403
