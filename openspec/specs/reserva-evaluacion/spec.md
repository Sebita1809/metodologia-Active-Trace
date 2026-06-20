## Requirements

### Requirement: Reserva de turno con control de cupo
El sistema SHALL permitir a un ALUMNO con permiso `coloquios:reservar` crear una `ReservaEvaluacion` vía `POST /api/v1/coloquios/{id}/reservas` con `fecha_hora`. El `alumno_id` y el `tenant_id` SHALL derivarse del JWT, nunca del body o la URL. Antes de crear, el sistema SHALL validar que la cantidad de reservas `Activa` para esa fecha sea menor que `cupo_por_dia`; si el cupo está lleno SHALL responder 409 y no crear la reserva. La reserva creada SHALL tener `estado='Activa'`.

#### Scenario: Reserva con cupo disponible
- **WHEN** un ALUMNO reserva un turno en una fecha con cupo disponible
- **THEN** el sistema crea la `ReservaEvaluacion` con `estado='Activa'` scoped al tenant y al alumno del JWT

#### Scenario: Cupo lleno rechaza la reserva
- **WHEN** un ALUMNO reserva un turno en una fecha donde las reservas activas ya igualan `cupo_por_dia`
- **THEN** el sistema responde 409 y no crea la reserva

#### Scenario: Usuario sin permiso de reserva es rechazado
- **WHEN** un usuario sin `coloquios:reservar` envía `POST /api/v1/coloquios/{id}/reservas`
- **THEN** el sistema responde 403

### Requirement: Unicidad de reserva activa por alumno
El sistema SHALL garantizar que un alumno no tenga dos `ReservaEvaluacion` con `estado='Activa'` para la misma `evaluacion_id`. Un intento de segunda reserva activa SHALL responder 409.

#### Scenario: Segunda reserva activa es rechazada
- **WHEN** un ALUMNO con una reserva `Activa` para la evaluación intenta crear otra reserva en la misma evaluación
- **THEN** el sistema responde 409 y no crea la segunda reserva

### Requirement: Cancelación de la propia reserva
El sistema SHALL permitir a un ALUMNO cancelar su propia reserva vía `DELETE /api/v1/coloquios/{id}/reservas/{rid}`, cambiando `estado` de `Activa` a `Cancelada`, siempre que la evaluación siga `Activa`. La cancelación SHALL liberar el cupo (las reservas `Cancelada` no cuentan para el cupo). Un alumno SHALL poder cancelar solo reservas propias; en caso contrario SHALL responder 403.

#### Scenario: Alumno cancela su reserva y libera cupo
- **WHEN** un ALUMNO cancela su reserva `Activa` mientras la evaluación está `Activa`
- **THEN** la reserva pasa a `Cancelada` y el cupo de esa fecha queda disponible para otra reserva

#### Scenario: Cancelar reserva ajena es rechazado
- **WHEN** un ALUMNO intenta cancelar una reserva que no le pertenece
- **THEN** el sistema responde 403 y no modifica la reserva

#### Scenario: Cancelar sobre evaluación cerrada es rechazado
- **WHEN** un ALUMNO intenta cancelar su reserva cuando la evaluación está `Cerrada`
- **THEN** el sistema rechaza la operación y la reserva permanece `Activa`

### Requirement: Agenda consolidada de reservas
El sistema SHALL exponer `GET /api/v1/coloquios/{id}/reservas` para usuarios con `coloquios:ver`, devolviendo las reservas de la evaluación filtradas por `tenant_id` para consulta y agenda.

#### Scenario: Coordinador consulta la agenda de reservas
- **WHEN** un usuario con `coloquios:ver` solicita `GET /api/v1/coloquios/{id}/reservas`
- **THEN** el sistema devuelve las reservas de la evaluación filtradas por `tenant_id`

#### Scenario: Usuario sin permiso de vista es rechazado
- **WHEN** un usuario sin `coloquios:ver` solicita la agenda
- **THEN** el sistema responde 403
