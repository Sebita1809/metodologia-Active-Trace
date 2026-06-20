## ADDED Requirements

### Requirement: Consulta analítica de calificaciones por lista de entradas

El sistema SHALL permitir consultar todas las `Calificacion` activas (no soft-deleted) para una lista de `entrada_padron_id`s, filtrando siempre por `tenant_id` derivado del contexto del repositorio. Esta operación es la base para los cálculos de análisis de C-11.

#### Scenario: consulta retorna solo calificaciones del tenant

- **WHEN** se invoca `list_by_entradas` con una lista de `entrada_padron_id`s
- **THEN** solo se retornan filas cuyo `tenant_id` coincide con el del repositorio y cuyo `deleted_at` es NULL

#### Scenario: lista vacía de entrada retorna lista vacía

- **WHEN** se invoca `list_by_entradas` con una lista vacía
- **THEN** el sistema retorna una lista vacía sin consultar la base de datos
