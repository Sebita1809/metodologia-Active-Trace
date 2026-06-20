## ADDED Requirements

### Requirement: Docente puede consultar sus propios equipos (mis-equipos)
El sistema SHALL exponer `GET /api/equipos/mis-equipos` que retorna todas las `Asignacion` del usuario autenticado (derivado del JWT) dentro del tenant. El campo `estado_vigencia` SHALL ser calculado en el service sin persistirse. El endpoint SHALL soportar filtros opcionales por `estado_vigencia` (Vigente/Vencida), `materia_id`, `rol`, `carrera_id` y `cohorte_id`. La identidad del docente MUST provenir exclusivamente del JWT — no existe ningún parámetro de URL o body que permita consultar equipos de otro usuario.

#### Scenario: Docente ve sus asignaciones vigentes
- **WHEN** un docente autenticado hace GET a `/api/equipos/mis-equipos`
- **THEN** el sistema retorna únicamente las asignaciones cuyo `usuario_id` coincide con el del JWT y cuyo `tenant_id` coincide con el del JWT, con `estado_vigencia` calculado para cada una

#### Scenario: Filtrar mis-equipos por materia
- **WHEN** un docente hace GET a `/api/equipos/mis-equipos?materia_id={id}`
- **THEN** el sistema retorna solo las asignaciones del docente para esa materia

#### Scenario: Identidad no puede ser suplantada por parámetro
- **WHEN** un usuario autenticado hace GET a `/api/equipos/mis-equipos` con un `usuario_id` en querystring diferente al propio
- **THEN** el sistema ignora ese parámetro y retorna únicamente las asignaciones del usuario del JWT

#### Scenario: Sin token retorna 401
- **WHEN** se hace GET a `/api/equipos/mis-equipos` sin token de autenticación
- **THEN** el sistema retorna HTTP 401

---

### Requirement: Búsqueda de usuarios con autocompletado asistido por servidor
El sistema SHALL exponer `GET /api/equipos/usuarios/buscar?q=<texto>` que retorna una lista paginada de usuarios del tenant cuyo `nombre` o `apellidos` contengan el texto de búsqueda (case-insensitive). La respuesta SHALL incluir `id`, `nombre`, `apellidos` y `rol` contextual, pero NO SHALL exponer datos PII cifrados (email, DNI, CBU) en este endpoint. El endpoint SHALL requerir al menos 2 caracteres en `q`.

#### Scenario: Búsqueda retorna coincidencias por nombre
- **WHEN** un usuario con permiso `equipos:asignar` hace GET a `/api/equipos/usuarios/buscar?q=mar`
- **THEN** el sistema retorna usuarios del tenant cuyo nombre o apellidos contienen "mar" (case-insensitive)

#### Scenario: Búsqueda con menos de 2 caracteres retorna 422
- **WHEN** se hace GET a `/api/equipos/usuarios/buscar?q=m`
- **THEN** el sistema retorna HTTP 422 con mensaje de validación

#### Scenario: La respuesta no expone PII cifrada
- **WHEN** se obtiene el resultado de la búsqueda de usuarios
- **THEN** los campos `email`, `dni`, `cuil`, `cbu` y `alias_cbu` NO aparecen en la respuesta

---

### Requirement: Asignación masiva de docentes en bloque
El sistema SHALL exponer `POST /api/equipos/asignaciones/masiva` protegido con `require_permission("equipos:asignar")`. El body SHALL aceptar: `usuario_ids: list[UUID]` (1 o más), `rol: str`, `materia_id: UUID`, `carrera_id: UUID | None`, `cohorte_id: UUID | None`, `comisiones: list[str]`, `desde: date`, `hasta: date | None`. El sistema SHALL crear una `Asignacion` por cada `usuario_id` recibido dentro de una única transacción y retornar HTTP 201 con la lista de asignaciones creadas. SHALL registrar un evento de auditoría `ASIGNACION_MODIFICAR` con `filas_afectadas = len(usuario_ids)`.

#### Scenario: Asignación masiva crea una asignación por cada usuario
- **WHEN** un COORDINADOR hace POST a `/api/equipos/asignaciones/masiva` con 3 `usuario_ids` y datos de contexto válidos
- **THEN** el sistema crea 3 asignaciones, retorna HTTP 201 con las 3, y registra `ASIGNACION_MODIFICAR` con `filas_afectadas = 3`

#### Scenario: Lista de usuarios vacía es rechazada
- **WHEN** se hace POST a `/api/equipos/asignaciones/masiva` con `usuario_ids: []`
- **THEN** el sistema retorna HTTP 422

#### Scenario: Usuario sin permiso recibe 403
- **WHEN** un usuario sin permiso `equipos:asignar` hace POST a `/api/equipos/asignaciones/masiva`
- **THEN** el sistema retorna HTTP 403

#### Scenario: Fallo en un usuario hace rollback completo
- **WHEN** uno de los `usuario_ids` no pertenece al tenant
- **THEN** el sistema no persiste ninguna asignación y retorna HTTP 422 o 404 según el caso

---

### Requirement: Clonar equipo docente entre períodos (RN-12)
El sistema SHALL exponer `POST /api/equipos/asignaciones/clonar` protegido con `require_permission("equipos:asignar")`. El body SHALL aceptar: `origen: { materia_id, carrera_id, cohorte_id }`, `destino: { materia_id, carrera_id, cohorte_id }`, `desde: date`, `hasta: date | None`. El sistema SHALL leer todas las `Asignacion` vigentes del origen (filtradas por tenant), duplicarlas cambiando el contexto al destino y aplicando las nuevas fechas de vigencia, y persistirlas en una única transacción. La respuesta SHALL indicar cuántas asignaciones fueron clonadas. SHALL registrar `ASIGNACION_MODIFICAR` con el número de asignaciones creadas.

#### Scenario: Clonar equipo crea asignaciones equivalentes en el destino
- **WHEN** un COORDINADOR hace POST a `/api/equipos/asignaciones/clonar` con origen válido (3 asignaciones vigentes) y destino válido con nuevas fechas
- **THEN** el sistema crea 3 nuevas asignaciones en el destino con las mismas propiedades de rol/usuario/comisiones pero con `cohorte_id` del destino y las fechas indicadas, y retorna HTTP 201 con `clonadas: 3`

#### Scenario: Origen sin asignaciones vigentes retorna 0 clonadas
- **WHEN** se hace POST a `/api/equipos/asignaciones/clonar` con un origen que no tiene asignaciones vigentes
- **THEN** el sistema retorna HTTP 200 con `clonadas: 0` sin crear registros

#### Scenario: Origen de otro tenant es inaccesible
- **WHEN** se hace POST a `/api/equipos/asignaciones/clonar` con `origen.cohorte_id` de otro tenant
- **THEN** el sistema retorna `clonadas: 0` (las asignaciones del origen no son visibles para el tenant actual)

#### Scenario: Fallo en bulk insert hace rollback completo
- **WHEN** la inserción de cualquiera de las asignaciones clonadas falla (e.g., FK inválida en destino)
- **THEN** el sistema no persiste ninguna asignación del clonar y retorna error HTTP 4XX/5XX

---

### Requirement: Modificar vigencia general del equipo en bloque
El sistema SHALL exponer `PATCH /api/equipos/asignaciones/vigencia` protegido con `require_permission("equipos:asignar")`. El body SHALL aceptar: `filtro: { materia_id, carrera_id?, cohorte_id? }`, `desde: date`, `hasta: date | None`. El sistema SHALL actualizar `desde` y `hasta` de todas las `Asignacion` del tenant que coincidan con el filtro, y retornar el número de registros modificados. SHALL registrar `ASIGNACION_MODIFICAR` con `filas_afectadas`.

#### Scenario: Modificación de vigencia actualiza las asignaciones del equipo
- **WHEN** un COORDINADOR hace PATCH a `/api/equipos/asignaciones/vigencia` con `materia_id`, `cohorte_id` y nuevas fechas
- **THEN** el sistema actualiza `desde`/`hasta` de todas las asignaciones de esa materia×cohorte y retorna `{ modificadas: N }`

#### Scenario: Filtro sin coincidencias retorna 0 modificadas
- **WHEN** se hace PATCH con un `materia_id` que no tiene asignaciones en el tenant
- **THEN** el sistema retorna `{ modificadas: 0 }` sin error

#### Scenario: `hasta: null` deja la vigencia abierta
- **WHEN** se hace PATCH con `hasta: null`
- **THEN** el sistema setea `hasta = null` (vigencia abierta) en todas las asignaciones del filtro

---

### Requirement: Exportar equipo docente como archivo CSV
El sistema SHALL exponer `GET /api/equipos/asignaciones/exportar` protegido con `require_permission("equipos:asignar")`. El endpoint SHALL aceptar los mismos parámetros de filtro opcionales que el listado (`materia_id`, `carrera_id`, `cohorte_id`, `rol`, `estado_vigencia`). La respuesta SHALL ser un `StreamingResponse` con `Content-Type: text/csv` y `Content-Disposition: attachment; filename="equipo.csv"`. El CSV SHALL incluir columnas: `usuario_id`, `nombre`, `apellidos`, `rol`, `materia`, `carrera`, `cohorte`, `comisiones`, `desde`, `hasta`, `estado_vigencia`.

#### Scenario: Exportación genera CSV con todas las asignaciones del equipo
- **WHEN** un COORDINADOR hace GET a `/api/equipos/asignaciones/exportar`
- **THEN** el sistema retorna HTTP 200 con `Content-Type: text/csv` y el cuerpo contiene las filas de asignaciones del tenant

#### Scenario: Exportación con filtro retorna subconjunto
- **WHEN** se hace GET a `/api/equipos/asignaciones/exportar?materia_id={id}`
- **THEN** el CSV contiene únicamente las asignaciones de esa materia

#### Scenario: Usuario sin permiso recibe 403
- **WHEN** un usuario sin permiso `equipos:asignar` hace GET a `/api/equipos/asignaciones/exportar`
- **THEN** el sistema retorna HTTP 403

---

### Requirement: Todas las operaciones de escritura generan auditoría `ASIGNACION_MODIFICAR`
El sistema SHALL registrar un evento de auditoría con código `ASIGNACION_MODIFICAR` después de cada operación de escritura exitosa en los endpoints de equipos (masiva, clonar, vigencia). El campo `filas_afectadas` SHALL reflejar el número de asignaciones creadas o modificadas. El `actor_id` SHALL derivarse del JWT.

#### Scenario: Masiva registra auditoría con filas_afectadas correcto
- **WHEN** la asignación masiva de 5 docentes se completa exitosamente
- **THEN** existe un registro en `AuditLog` con `accion = "ASIGNACION_MODIFICAR"` y `filas_afectadas = 5`

#### Scenario: Clonar registra auditoría con filas_afectadas correcto
- **WHEN** el clonar equipo crea 8 asignaciones nuevas
- **THEN** existe un registro en `AuditLog` con `accion = "ASIGNACION_MODIFICAR"` y `filas_afectadas = 8`

#### Scenario: Modificar vigencia registra auditoría
- **WHEN** la modificación de vigencia actualiza 12 asignaciones
- **THEN** existe un registro en `AuditLog` con `accion = "ASIGNACION_MODIFICAR"` y `filas_afectadas = 12`
