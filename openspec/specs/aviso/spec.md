## Requirements

### Requirement: Creación y gestión de avisos institucionales

El sistema SHALL permitir a usuarios con permiso `avisos:publicar` (COORDINADOR, ADMIN) crear, actualizar y dar de baja (soft delete) avisos institucionales vía `POST/PATCH/DELETE /api/avisos/`. Cada aviso SHALL tener: `alcance` (`Global|PorMateria|PorCohorte|PorRol`), `materia_id`/`cohorte_id`/`rol_destino` nullable según alcance, `severidad` (`Info|Advertencia|Critico`), `titulo`, `cuerpo` (texto enriquecido), ventana de visibilidad (`inicio_en`/`fin_en`), `orden` (entero, para prioridad), `activo` (booleano), `requiere_ack` (booleano), `deleted_at` y timestamps. El `tenant_id` SHALL derivarse del JWT; nunca de la petición. Sin permiso `avisos:publicar` SHALL responder 403.

#### Scenario: Coordinador crea aviso global

- **WHEN** un usuario con `avisos:publicar` envía `POST /api/avisos/` con `alcance='Global'` y datos válidos
- **THEN** el sistema crea el aviso con `tenant_id` del JWT y retorna 201

#### Scenario: Aviso con alcance PorMateria requiere materia_id

- **WHEN** se crea un aviso con `alcance='PorMateria'` sin `materia_id`
- **THEN** el sistema rechaza la solicitud con error de validación

#### Scenario: Usuario sin permiso de publicación es rechazado

- **WHEN** un usuario sin `avisos:publicar` intenta crear un aviso
- **THEN** el sistema responde 403

#### Scenario: Baja de aviso es soft delete

- **WHEN** un publicador elimina un aviso vía `DELETE /api/avisos/{id}`
- **THEN** el aviso queda con `deleted_at` seteado y no aparece en consultas por defecto

### Requirement: Ventana de vigencia controla la visibilidad (RN-18)

El sistema SHALL mostrar a los usuarios únicamente los avisos cuyo rango `inicio_en ≤ ahora ≤ fin_en` se cumpla. Un aviso fuera de su ventana SHALL ser excluido del listado `mis-avisos`, aunque el registro exista en la base de datos. El filtro de vigencia SHALL aplicarse en el repository.

#### Scenario: Aviso dentro de ventana es visible

- **WHEN** la fecha/hora actual está entre `inicio_en` y `fin_en` del aviso
- **THEN** el aviso aparece en `GET /api/avisos/mis-avisos` para los destinatarios

#### Scenario: Aviso fuera de ventana no es visible

- **WHEN** la fecha/hora actual es posterior a `fin_en`
- **THEN** el aviso no aparece en `GET /api/avisos/mis-avisos`

### Requirement: Segmentación por audiencia (RN-20)

El sistema SHALL filtrar los avisos por audiencia del usuario autenticado: un aviso con `alcance='Global'` SHALL mostrarse a todos; `PorRol` solo al rol destinatario; `PorMateria` solo a usuarios con asignación activa en esa materia; `PorCohorte` solo a usuarios de esa cohorte. El listado `GET /api/avisos/mis-avisos` SHALL aplicar estos filtros automáticamente según el rol y contexto del JWT. Un usuario que no pertenece a la audiencia del aviso NO SHALL verlo.

#### Scenario: Aviso global es visible para todos los roles

- **WHEN** existe un aviso con `alcance='Global'` activo y vigente
- **THEN** cualquier usuario autenticado lo ve en `mis-avisos`

#### Scenario: Aviso PorRol solo llega al rol destinatario

- **WHEN** un aviso tiene `alcance='PorRol'` y `rol_destino='ALUMNO'`
- **THEN** solo los usuarios con rol ALUMNO lo ven; un PROFESOR no lo ve

#### Scenario: Aviso PorCohorte solo llega a esa cohorte

- **WHEN** un aviso tiene `alcance='PorCohorte'` y `cohorte_id=X`
- **THEN** solo los usuarios pertenecientes a la cohorte X lo ven

### Requirement: Listado de avisos tenant-scoped con ordenamiento por prioridad

El sistema SHALL exponer `GET /api/avisos/mis-avisos` que retorne los avisos vigentes, activos y dirigidos al usuario autenticado, ordenados ascendentemente por `orden` (menor número = mayor prioridad). Los avisos con `requiere_ack=true` que ya fueron acusados SHALL excluirse del listado activo (ya leídos). Requiere cualquier rol autenticado.

#### Scenario: Orden de prioridad respetado

- **WHEN** existen dos avisos vigentes con `orden=1` y `orden=3`
- **THEN** el listado retorna primero el de `orden=1`

#### Scenario: Aviso acusado se excluye del listado activo

- **WHEN** un usuario emitió ack para un aviso con `requiere_ack=true`
- **THEN** ese aviso no aparece en `GET /api/avisos/mis-avisos` para ese usuario
