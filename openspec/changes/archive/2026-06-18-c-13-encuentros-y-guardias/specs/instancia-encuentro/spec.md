## ADDED Requirements

### Requirement: Creación de encuentro único
El sistema SHALL permitir crear un encuentro único vía `POST /api/v1/encuentros` (sin slot), generando exactamente una `InstanciaEncuentro` con `slot_id = NULL`, `fecha` igual a `fecha_unica` y `hora` indicada (RN-13.2). El `tenant_id` SHALL derivarse del JWT.

#### Scenario: Crear encuentro único genera una instancia sin slot
- **WHEN** un usuario con `encuentros:gestionar` envía `POST /api/v1/encuentros` con `fecha_unica` y `hora`
- **THEN** el sistema crea una única `InstanciaEncuentro` con `slot_id = NULL` en estado `Programado`

### Requirement: Edición de instancia con estado independiente (RN-14)
El sistema SHALL permitir editar una `InstanciaEncuentro` vía `PATCH /api/v1/encuentros/{id}` modificando `estado`, `meet_url`, `video_url` y `comentario`. La edición SHALL afectar SOLO a esa instancia, sin modificar el slot ni otras instancias del mismo slot.

#### Scenario: Marcar instancia como Realizado no afecta a las demás
- **WHEN** un slot recurrente generó 3 instancias y se hace `PATCH` sobre una de ellas marcándola `Realizado` y cargando `video_url`
- **THEN** esa instancia queda `Realizado` con su `video_url`, y las otras dos instancias y el slot permanecen sin cambios

#### Scenario: Transición de estado válida
- **WHEN** se hace `PATCH` sobre una instancia `Programado` con `estado="Cancelado"`
- **THEN** la instancia queda `Cancelado` y conserva su `fecha` y `hora`

### Requirement: Generación de HTML para aula virtual
El sistema SHALL exponer `GET /api/v1/encuentros/html?asignacion_id=X` que devuelve un fragmento HTML con el calendario de instancias y enlaces a `meet_url` y `video_url` de cada encuentro de esa asignación dentro del tenant.

#### Scenario: HTML incluye instancias con grabaciones
- **WHEN** se solicita `GET /api/v1/encuentros/html?asignacion_id=X` para una asignación con instancias realizadas con `video_url`
- **THEN** el fragmento HTML lista las instancias con su fecha y hora e incluye los enlaces a `video_url` y `meet_url`

### Requirement: Vista administrativa de encuentros
El sistema SHALL exponer `GET /api/v1/admin/encuentros` para COORDINADOR y ADMIN, devolviendo encuentros de todas las asignaciones del tenant (transversal dentro del tenant, nunca cross-tenant). Sin rol habilitado SHALL responder 403.

#### Scenario: Coordinador ve encuentros del tenant
- **WHEN** un COORDINADOR solicita `GET /api/v1/admin/encuentros`
- **THEN** el sistema devuelve las instancias de todas las asignaciones de su tenant, filtradas por `tenant_id`

#### Scenario: Profesor sin rol admin es rechazado
- **WHEN** un PROFESOR sin rol COORDINADOR/ADMIN solicita `GET /api/v1/admin/encuentros`
- **THEN** el sistema responde 403
