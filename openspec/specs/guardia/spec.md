## Requirements

### Requirement: Registro de guardia por tutor
El sistema SHALL permitir a un TUTOR registrar una `Guardia` vía `POST /api/v1/guardias` con `asignacion_id`, `materia_id`, `carrera_id`, `cohorte_id`, `dia`, `horario`, `estado` y `comentarios`. El `tenant_id` y la identidad SHALL derivarse del JWT, y `creada_at` SHALL setearse en el servidor.

#### Scenario: Tutor registra guardia
- **WHEN** un TUTOR envía `POST /api/v1/guardias` con datos válidos
- **THEN** el sistema crea la guardia scoped al tenant, con `creada_at` del servidor y `estado` inicial provisto

#### Scenario: Usuario sin permiso de registro es rechazado
- **WHEN** un usuario sin permiso de registro de guardias envía `POST /api/v1/guardias`
- **THEN** el sistema responde 403 (fail-closed) y no crea la guardia

### Requirement: Consulta y exportación de guardias por coordinación
El sistema SHALL exponer `GET /api/v1/guardias` para COORDINADOR y ADMIN, devolviendo las guardias del tenant con soporte de exportación. Los resultados SHALL filtrarse siempre por `tenant_id`. Sin rol habilitado SHALL responder 403.

#### Scenario: Coordinador consulta guardias del tenant
- **WHEN** un COORDINADOR solicita `GET /api/v1/guardias`
- **THEN** el sistema devuelve las guardias de su tenant filtradas por `tenant_id`

#### Scenario: Tutor sin rol de consulta es rechazado
- **WHEN** un TUTOR sin rol COORDINADOR/ADMIN solicita `GET /api/v1/guardias`
- **THEN** el sistema responde 403

### Requirement: Soft delete de guardias
El sistema SHALL aplicar soft delete (`deleted_at`) a las guardias; nunca hard delete. Las guardias eliminadas SHALL excluirse de las consultas por defecto.

#### Scenario: Guardia eliminada no aparece en consultas
- **WHEN** una guardia tiene `deleted_at` seteado
- **THEN** `GET /api/v1/guardias` no la incluye en los resultados por defecto
