## ADDED Requirements

### Requirement: Mis equipos — Vista del docente autenticado

El sistema SHALL exponer un endpoint para que cualquier usuario autenticado (PROFESOR, TUTOR, NEXO, COORDINADOR) consulte sus propias asignaciones activas.

#### Scenario: Docente consulta sus asignaciones vigentes
- **WHEN** un usuario autenticado con rol PROFESOR envía GET a `/api/equipos/mis-equipos`
- **THEN** el sistema SHALL retornar 200 con la lista de asignaciones vigentes de ese usuario en el tenant, incluyendo materia, carrera, cohorte, comisiones, rol, vigencia y estado

#### Scenario: Docente sin asignaciones vigentes
- **WHEN** un usuario autenticado sin asignaciones vigentes consulta `/api/equipos/mis-equipos`
- **THEN** el sistema SHALL retornar 200 con una lista vacía

#### Scenario: Usuario no autenticado
- **WHEN** un cliente no autenticado envía GET a `/api/equipos/mis-equipos`
- **THEN** el sistema SHALL retornar 401 Unauthorized

---

### Requirement: Equipo por materia — Consulta de equipo completo

El sistema SHALL exponer un endpoint para que COORDINADOR y ADMIN consulten todas las asignaciones de una materia.

#### Scenario: COORDINADOR consulta equipo de materia existente
- **WHEN** un usuario con permiso `equipos:asignar` envía GET a `/api/equipos/materias/{materia_id}` con un UUID de materia válida
- **THEN** el sistema SHALL retornar 200 con todas las asignaciones de esa materia en el tenant, agrupadas por cohorte

#### Scenario: COORDINADOR consulta equipo de materia inexistente
- **WHEN** un usuario envía GET a `/api/equipos/materias/{materia_id}` con un UUID inexistente
- **THEN** el sistema SHALL retornar 404 Not Found

#### Scenario: Consulta filtrada por cohorte
- **WHEN** un usuario envía GET a `/api/equipos/materias/{materia_id}?cohorte_id={uuid}`
- **THEN** el sistema SHALL retornar solo las asignaciones de esa materia Y esa cohorte

#### Scenario: COORDINADOR de tenant A no ve equipo de tenant B
- **WHEN** un usuario del tenant A consulta un equipo de materia del tenant B
- **THEN** el sistema SHALL retornar 404 (la materia no existe en su tenant)

---

### Requirement: Asignación masiva — Asignar N docentes en bloque

El sistema SHALL exponer un endpoint para que COORDINADOR y ADMIN asignen múltiples docentes a una misma materia × carrera × cohorte × rol con vigencia común en una sola operación transaccional.

#### Scenario: Asignación masiva exitosa
- **WHEN** un usuario con permiso `equipos:asignar` envía POST a `/api/equipos/asignacion-masiva` con una lista de `usuario_id`s, `materia_id`, `carrera_id`, `cohorte_id`, `rol`, `comisiones`, `desde` y `hasta` válidos
- **THEN** el sistema SHALL crear todas las asignaciones en una transacción y retornar 201 con la lista de asignaciones creadas

#### Scenario: Asignación masiva con docente inactivo
- **WHEN** el array de `usuario_id`s incluye un usuario con estado inactivo
- **THEN** el sistema SHALL retornar 422 indicando qué usuario no está activo, sin crear ninguna asignación

#### Scenario: Asignación masiva con rol inválido
- **WHEN** el `rol` proporcionado no está en la lista de roles del dominio (ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS)
- **THEN** el sistema SHALL retornar 422 indicando que el rol no es válido

#### Scenario: Asignación masiva con fechas inválidas
- **WHEN** `desde` es posterior a `hasta`
- **THEN** el sistema SHALL retornar 422 sin crear asignaciones

#### Scenario: Asignación masiva parcial falla — rollback
- **WHEN** uno de los `usuario_id`s no existe en el tenant
- **THEN** el sistema SHALL retornar 422 y NO crear ninguna asignación (rollback completo)

---

### Requirement: Clonar equipo entre períodos

El sistema SHALL exponer un endpoint para que COORDINADOR y ADMIN dupliquen todas las asignaciones vigentes de un equipo origen (materia × carrera × cohorte) hacia un destino (misma materia, misma carrera, cohorte distinta), ajustando las fechas de vigencia al nuevo período. Aplica RN-12.

#### Scenario: Clonación exitosa entre cohortes
- **WHEN** un usuario con permiso `equipos:asignar` envía POST a `/api/equipos/clonar` con `materia_id`, `carrera_id`, `cohorte_origen_id`, `cohorte_destino_id`, `desde` y `hasta` válidos
- **THEN** el sistema SHALL duplicar todas las asignaciones vigentes del origen hacia el destino, asignando las nuevas fechas, y retornar 201 con la lista de asignaciones creadas y el conteo

#### Scenario: Clonación con cohorte origen sin asignaciones
- **WHEN** la cohorte origen no tiene asignaciones vigentes para esa materia
- **THEN** el sistema SHALL retornar 200 con lista vacía (clonación exitosa sin datos)

#### Scenario: Clonación con cohorte destino idéntica a origen
- **WHEN** `cohorte_origen_id` es igual a `cohorte_destino_id`
- **THEN** el sistema SHALL retornar 422 indicando que las cohortes deben ser distintas

#### Scenario: Clonación con cohorte destino inexistente
- **WHEN** `cohorte_destino_id` no existe en el tenant
- **THEN** el sistema SHALL retornar 404 Not Found

#### Scenario: Clonación preserva responsable_id
- **WHEN** se clonan asignaciones que tienen `responsable_id` definido
- **THEN** el sistema SHALL preservar la relación jerárquica en las asignaciones clonadas

#### Scenario: Clonación entre tenants distintos
- **WHEN** `materia_id` pertenece a tenant A y `cohorte_destino_id` pertenece a tenant B
- **THEN** el sistema SHALL retornar 404 (los recursos no existen en el mismo tenant)

---

### Requirement: Modificar vigencia en bloque

El sistema SHALL exponer un endpoint para que COORDINADOR y ADMIN actualicen las fechas `desde` y `hasta` de todas las asignaciones vigentes de un equipo (materia × carrera × cohorte) en una sola operación.

#### Scenario: Modificación de vigencia en bloque exitosa
- **WHEN** un usuario con permiso `equipos:asignar` envía PATCH a `/api/equipos/vigencia` con `materia_id` y nuevos `desde`/`hasta`
- **THEN** el sistema SHALL actualizar las fechas de todas las asignaciones vigentes de esa materia y retornar 200 con el conteo de asignaciones afectadas

#### Scenario: Modificación filtrada por cohorte
- **WHEN** se envía PATCH a `/api/equipos/vigencia` con `materia_id`, `cohorte_id` y nuevos `desde`/`hasta`
- **THEN** el sistema SHALL actualizar solo las asignaciones de esa materia Y esa cohorte

#### Scenario: Modificación con rango inválido
- **WHEN** `desde` es posterior a `hasta`
- **THEN** el sistema SHALL retornar 422 sin modificar ninguna asignación

#### Scenario: Modificación sin asignaciones afectadas
- **WHEN** no existen asignaciones vigentes para la materia/cohorte indicada
- **THEN** el sistema SHALL retornar 200 con conteo 0 (operación exitosa sin efectos)

---

### Requirement: Exportar equipo docente

El sistema SHALL exponer un endpoint para que COORDINADOR y ADMIN descarguen la composición completa de un equipo docente en formato de archivo.

#### Scenario: Exportación exitosa de equipo
- **WHEN** un usuario con permiso `equipos:asignar` envía GET a `/api/equipos/{materia_id}/exportar`
- **THEN** el sistema SHALL retornar un archivo descargable con todas las asignaciones de esa materia incluyendo: docente, rol, carrera, cohorte, comisiones, vigencia y estado

#### Scenario: Exportación de materia sin asignaciones
- **WHEN** un usuario envía GET a `/api/equipos/{materia_id}/exportar` para una materia sin equipo asignado
- **THEN** el sistema SHALL retornar un archivo con solo los encabezados (sin datos)

#### Scenario: Exportación filtrada por cohorte
- **WHEN** se envía GET a `/api/equipos/{materia_id}/exportar?cohorte_id={uuid}`
- **THEN** el sistema SHALL exportar solo las asignaciones de esa materia Y esa cohorte

---

### Requirement: Validación de desactivación de entidad académica con asignaciones activas

El sistema SHALL impedir el soft-delete de una materia, carrera o cohorte que tenga asignaciones activas (vigentes), para mantener la integridad referencial lógica.

#### Scenario: Rechazar desactivación de materia con asignaciones activas
- **WHEN** un ADMIN intenta desactivar una materia que tiene asignaciones vigentes
- **THEN** el sistema SHALL retornar 409 Conflict indicando que la materia tiene asignaciones activas y no puede desactivarse

#### Scenario: Rechazar desactivación de carrera con asignaciones activas
- **WHEN** un ADMIN intenta desactivar una carrera que tiene asignaciones activas
- **THEN** el sistema SHALL retornar 409 Conflict

#### Scenario: Rechazar desactivación de cohorte con asignaciones activas
- **WHEN** un ADMIN intenta desactivar una cohorte que tiene asignaciones activas
- **THEN** el sistema SHALL retornar 409 Conflict

#### Scenario: Permitir desactivación de materia sin asignaciones activas
- **WHEN** un ADMIN intenta desactivar una materia que no tiene asignaciones activas
- **THEN** el sistema SHALL permitir la desactivación y retornar 200

---

### Requirement: Auditoría — Registro de operaciones sobre equipos docentes

Toda operación de escritura sobre equipos docentes SHALL generar un evento de auditoría con acción `ASIGNACION_MODIFICAR`.

#### Scenario: Asignación masiva genera evento de auditoría
- **WHEN** se completa una asignación masiva exitosa
- **THEN** el sistema SHALL registrar un evento `ASIGNACION_MODIFICAR` con detalle de las asignaciones creadas

#### Scenario: Clonación genera evento de auditoría
- **WHEN** se completa una clonación de equipo exitosa
- **THEN** el sistema SHALL registrar un evento `ASIGNACION_MODIFICAR` con origen, destino y conteo

#### Scenario: Modificación de vigencia genera evento de auditoría
- **WHEN** se completa una modificación de vigencia en bloque exitosa
- **THEN** el sistema SHALL registrar un evento `ASIGNACION_MODIFICAR` con el detalle del cambio

---

### Requirement: Enlace — Asignación a UmbralMateria

Cuando un docente recibe una asignación a una materia, el sistema SHALL crear automáticamente un registro `UmbralMateria` con el umbral por defecto (60%) para ese docente en esa materia.

#### Scenario: Creación automática de UmbralMateria en asignación individual
- **WHEN** se crea una asignación con rol PROFESOR o TUTOR y `materia_id` definido
- **THEN** el sistema SHALL crear un `UmbralMateria` con `umbral_pct = 60` vinculado a esa asignación y materia

#### Scenario: Creación automática de UmbralMateria en asignación masiva
- **WHEN** se completa una asignación masiva que incluye roles PROFESOR o TUTOR
- **THEN** el sistema SHALL crear un `UmbralMateria` para cada asignación de tipo docente

#### Scenario: No crear UmbralMateria para roles no docentes
- **WHEN** se crea una asignación con rol COORDINADOR, ADMIN o FINANZAS
- **THEN** el sistema NO SHALL crear un `UmbralMateria`
