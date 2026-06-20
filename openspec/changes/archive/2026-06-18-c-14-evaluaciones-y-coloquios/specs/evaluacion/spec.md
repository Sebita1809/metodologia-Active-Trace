## ADDED Requirements

### Requirement: Creación de convocatoria
El sistema SHALL permitir a COORDINADOR y ADMIN crear una `Evaluacion` vía `POST /api/v1/coloquios/` con `materia_id`, `cohorte_id`, `tipo` (Parcial|TP|Coloquio|Recuperatorio), `instancia`, `dias_disponibles` y `cupo_por_dia`. El `tenant_id` SHALL derivarse del JWT y el `estado` inicial SHALL ser `Activa`. Sin el permiso `coloquios:gestionar` SHALL responder 403 (fail-closed).

#### Scenario: Coordinador crea convocatoria
- **WHEN** un usuario con `coloquios:gestionar` envía `POST /api/v1/coloquios/` con datos válidos
- **THEN** el sistema crea la evaluación scoped al tenant, con `estado='Activa'` y `cupo_por_dia` provisto

#### Scenario: Usuario sin permiso de gestión es rechazado
- **WHEN** un usuario sin `coloquios:gestionar` envía `POST /api/v1/coloquios/`
- **THEN** el sistema responde 403 y no crea la evaluación

#### Scenario: Tipo inválido es rechazado
- **WHEN** se envía `tipo` fuera de {Parcial, TP, Coloquio, Recuperatorio}
- **THEN** el sistema rechaza la solicitud por validación

### Requirement: Importación de padrón de candidatos
El sistema SHALL permitir, vía `POST /api/v1/coloquios/{id}/alumnos`, importar en bulk una lista de `alumno_id`s habilitados para la evaluación. Cada `alumno_id` SHALL existir y pertenecer al mismo `tenant_id`; un lote con identificadores inválidos SHALL ser rechazado. Requiere `coloquios:gestionar`.

#### Scenario: Importación de padrón válido
- **WHEN** un gestor envía una lista de `alumno_id`s válidos del tenant para la evaluación
- **THEN** el sistema registra a los candidatos y refleja el total en las métricas

#### Scenario: Padrón con alumno de otro tenant es rechazado
- **WHEN** la lista incluye un `alumno_id` inexistente o de otro tenant
- **THEN** el sistema rechaza el lote y no importa candidatos

### Requirement: Listado de convocatorias con métricas
El sistema SHALL exponer `GET /api/v1/coloquios/` para usuarios con `coloquios:ver`, devolviendo las evaluaciones del tenant con, por evaluación, los convocados, las reservas activas y los cupos libres. Los resultados SHALL filtrarse siempre por `tenant_id`.

#### Scenario: Listado expone cupos libres por evaluación
- **WHEN** un usuario con `coloquios:ver` solicita `GET /api/v1/coloquios/`
- **THEN** el sistema devuelve cada evaluación con `convocados`, `reservas_activas` y `cupos_libres` derivados de `cupo_por_dia` menos las reservas activas

#### Scenario: Usuario sin permiso de vista es rechazado
- **WHEN** un usuario sin `coloquios:ver` solicita `GET /api/v1/coloquios/`
- **THEN** el sistema responde 403

### Requirement: Panel de métricas
El sistema SHALL exponer `GET /api/v1/coloquios/metricas` para usuarios con `coloquios:ver`, devolviendo `total_alumnos_cargados`, `instancias_activas`, `reservas_activas` y `notas_registradas` agregadas y filtradas por `tenant_id`.

#### Scenario: Métricas agregadas del tenant
- **WHEN** un usuario con `coloquios:ver` solicita `GET /api/v1/coloquios/metricas`
- **THEN** el sistema devuelve los cuatro contadores calculados sobre las evaluaciones del tenant

### Requirement: Soft delete de evaluaciones
El sistema SHALL aplicar soft delete (`deleted_at`) a las evaluaciones; nunca hard delete. Las evaluaciones eliminadas SHALL excluirse de las consultas por defecto.

#### Scenario: Evaluación eliminada no aparece en consultas
- **WHEN** una evaluación tiene `deleted_at` seteado
- **THEN** `GET /api/v1/coloquios/` no la incluye en los resultados por defecto
