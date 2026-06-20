## ADDED Requirements

### Requirement: Creación de slot de encuentro recurrente
El sistema SHALL permitir crear un `SlotEncuentro` recurrente vía `POST /api/v1/slots` cuando `cant_semanas > 0`, generando automáticamente N `InstanciaEncuentro` a partir de `dia_semana`, `hora` y `fecha_inicio` (RN-13.1). La identidad y el `tenant_id` SHALL derivarse del JWT y el registro SHALL persistirse scoped al tenant.

#### Scenario: Crear slot recurrente genera N instancias
- **WHEN** un PROFESOR con `encuentros:gestionar` envía `POST /api/v1/slots` con `cant_semanas=4`, `dia_semana="Martes"`, `hora="18:00"` y `fecha_inicio` un martes
- **THEN** el sistema crea el slot y genera 4 `InstanciaEncuentro` con fechas separadas 7 días, todas en martes, en estado `Programado`

#### Scenario: fecha_inicio que no cae en dia_semana se alinea
- **WHEN** se crea un slot con `dia_semana="Miércoles"` y `fecha_inicio` que cae un lunes
- **THEN** la primera instancia generada cae en el primer miércoles igual o posterior a `fecha_inicio`

### Requirement: Modos de creación excluyentes (RN-13)
El sistema SHALL rechazar la creación de un slot que combine ambos modos (`cant_semanas > 0` y `fecha_unica` seteada simultáneamente) o que no especifique ninguno. Recurrente y único SHALL ser mutuamente excluyentes.

#### Scenario: Ambos modos presentes es rechazado
- **WHEN** se envía `POST /api/v1/slots` con `cant_semanas=4` y `fecha_unica` no nula
- **THEN** el sistema responde con error de validación de dominio y no crea slot ni instancias

#### Scenario: Ningún modo presente es rechazado
- **WHEN** se envía `POST /api/v1/slots` con `cant_semanas=0` y `fecha_unica` nula
- **THEN** el sistema responde con error de validación de dominio

### Requirement: Acceso scoped del profesor a su asignación
El sistema SHALL permitir a un PROFESOR crear slots solo para asignaciones propias; COORDINADOR y ADMIN SHALL poder hacerlo para cualquier asignación del tenant. Sin el permiso `encuentros:gestionar`, el sistema SHALL responder 403 (fail-closed).

#### Scenario: Profesor sobre asignación ajena es rechazado
- **WHEN** un PROFESOR envía `POST /api/v1/slots` con un `asignacion_id` que no le pertenece
- **THEN** el sistema responde 403 y no crea el slot

#### Scenario: Sin permiso es rechazado
- **WHEN** un usuario sin `encuentros:gestionar` envía `POST /api/v1/slots`
- **THEN** el sistema responde 403
