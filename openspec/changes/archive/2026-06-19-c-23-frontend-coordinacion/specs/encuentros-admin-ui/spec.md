## ADDED Requirements

### Requirement: Vista transversal de encuentros del tenant

La feature SHALL presentar todos los encuentros del tenant (más allá del docente creador) consumiendo `GET /api/v1/encuentros` con scope global para COORDINADOR/ADMIN. Implementa F6.5 y FL-06 paso 6.

#### Scenario: Ver todos los encuentros del tenant
- **WHEN** el COORDINADOR accede a la vista de encuentros
- **THEN** la UI muestra los encuentros de todos los docentes con columnas: docente, materia, fecha, horario, estado, enlace grabación

#### Scenario: Filtrar por docente y período
- **WHEN** el COORDINADOR filtra por docente "García" y mes "julio 2025"
- **THEN** la UI muestra solo los encuentros de ese docente en ese período

#### Scenario: Sin encuentros en el tenant
- **WHEN** no hay encuentros registrados en el tenant
- **THEN** la UI muestra el estado vacío "sin encuentros registrados"

### Requirement: Registro de guardias de tutores

La feature SHALL permitir registrar guardias cubiertas por tutores con campos: quién cubrió, materia, carrera/cohorte, día, horario, estado y comentarios, enviando `POST /api/v1/guardias`. Implementa F6.6.

#### Scenario: Registrar guardia
- **WHEN** el COORDINADOR registra una guardia para el tutor "Rodríguez"
- **THEN** la guardia aparece en el registro con todos sus datos

#### Scenario: Validación de campos obligatorios
- **WHEN** el usuario intenta registrar una guardia sin indicar el horario
- **THEN** Zod bloquea el envío y muestra el error inline

### Requirement: Consulta y exportación de guardias

La feature SHALL permitir consultar el registro de guardias filtrado por tutor, materia, estado y rango de fechas, consumiendo `GET /api/v1/guardias`, y descargar el registro como CSV. Implementa F6.6.

#### Scenario: Filtrar guardias por tutor
- **WHEN** el COORDINADOR filtra por tutor "Rodríguez"
- **THEN** la UI muestra solo las guardias registradas por ese tutor

#### Scenario: Exportar guardias como CSV
- **WHEN** el COORDINADOR pulsa "Exportar"
- **THEN** el navegador descarga el CSV con el registro de guardias filtrado
