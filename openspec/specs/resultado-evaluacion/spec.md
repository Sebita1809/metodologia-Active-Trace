## Requirements

### Requirement: Registro de nota final
El sistema SHALL permitir a usuarios con `coloquios:gestionar` registrar un `ResultadoEvaluacion` vía `POST /api/v1/coloquios/{id}/resultados` con `alumno_id` y `nota_final` (numérica o cualitativa, texto libre). El `tenant_id` SHALL derivarse del JWT. Sin el permiso SHALL responder 403 (fail-closed).

#### Scenario: Gestor registra nota
- **WHEN** un usuario con `coloquios:gestionar` registra una nota para un alumno de la evaluación
- **THEN** el sistema crea el `ResultadoEvaluacion` scoped al tenant con la `nota_final` provista

#### Scenario: Usuario sin permiso de gestión es rechazado
- **WHEN** un usuario sin `coloquios:gestionar` envía `POST /api/v1/coloquios/{id}/resultados`
- **THEN** el sistema responde 403 y no registra la nota

### Requirement: Unicidad de resultado por alumno
El sistema SHALL garantizar un único `ResultadoEvaluacion` por par `(evaluacion_id, alumno_id)`. Un intento de registrar un segundo resultado para el mismo alumno en la misma evaluación SHALL ser rechazado.

#### Scenario: Resultado duplicado es rechazado
- **WHEN** se intenta registrar una segunda nota para un alumno que ya tiene resultado en la evaluación
- **THEN** el sistema rechaza la operación y conserva el resultado existente

### Requirement: Consulta del registro académico
El sistema SHALL exponer `GET /api/v1/coloquios/{id}/resultados` para usuarios con `coloquios:ver`, devolviendo los resultados de la evaluación filtrados por `tenant_id`.

#### Scenario: Coordinador consulta el registro de notas
- **WHEN** un usuario con `coloquios:ver` solicita `GET /api/v1/coloquios/{id}/resultados`
- **THEN** el sistema devuelve los resultados de la evaluación filtrados por `tenant_id`

#### Scenario: Usuario sin permiso de vista es rechazado
- **WHEN** un usuario sin `coloquios:ver` solicita `GET /api/v1/coloquios/{id}/resultados`
- **THEN** el sistema responde 403
