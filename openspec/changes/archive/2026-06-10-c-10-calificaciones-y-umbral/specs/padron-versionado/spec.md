## ADDED Requirements

### Requirement: EntradaPadron como origen de Calificacion

El sistema SHALL permitir que una `EntradaPadron` sea referenciada por cero o más `Calificacion` (relación 1→N). La FK `calificacion.entrada_padron_id` apunta a `EntradaPadron`. El soft-delete de una `EntradaPadron` no afecta las `Calificacion` asociadas (se conservan con su `entrada_padron_id` intacto).

#### Scenario: calificaciones asociadas a una entrada de padrón

- **WHEN** se importan calificaciones para una materia
- **THEN** cada `Calificacion` creada tiene `entrada_padron_id` apuntando a la `EntradaPadron` correspondiente del padrón activo de esa materia

#### Scenario: soft-delete de EntradaPadron no borra calificaciones

- **WHEN** una `EntradaPadron` queda soft-deleted (por vaciado de padrón)
- **THEN** las `Calificacion` con esa `entrada_padron_id` permanecen en la base de datos con su `deleted_at` propio intacto
