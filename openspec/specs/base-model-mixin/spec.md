## ADDED Requirements

### Requirement: Toda entidad del dominio hereda BaseTenantModel
El sistema SHALL proveer `BaseTenantModel` como clase base para todos los modelos de dominio. El mixin aporta automáticamente: `id` (UUID, PK generado en base de datos), `tenant_id` (UUID, FK → Tenant, NOT NULL), `created_at` (datetime UTC, generado al insertar), `updated_at` (datetime UTC, actualizado en cada UPDATE), `deleted_at` (datetime UTC, nullable — soft delete).

#### Scenario: Instanciar un modelo que hereda BaseTenantModel
- **WHEN** se instancia un modelo concreto que hereda `BaseTenantModel` con `tenant_id` válido
- **THEN** el objeto tiene los campos `id`, `tenant_id`, `created_at`, `updated_at`, `deleted_at` disponibles con los tipos correctos

#### Scenario: UUID se genera automáticamente
- **WHEN** se persiste un nuevo registro en base de datos sin proveer `id`
- **THEN** el campo `id` tiene un UUID v4 válido generado por la base de datos (server_default)

### Requirement: Timestamps se gestionan automáticamente
El sistema SHALL gestionar `created_at` y `updated_at` sin intervención del código de aplicación. `created_at` se fija al momento del INSERT; `updated_at` se actualiza en cada UPDATE via `onupdate`.

#### Scenario: created_at no cambia en actualizaciones
- **WHEN** se actualiza un campo de un registro existente
- **THEN** `created_at` conserva el valor original y `updated_at` refleja el nuevo timestamp

### Requirement: Soft delete via deleted_at
El sistema SHALL implementar soft delete almacenando el timestamp de eliminación en `deleted_at`. Un registro con `deleted_at IS NOT NULL` está eliminado lógicamente. NUNCA se ejecuta un DELETE físico sobre entidades del dominio.

#### Scenario: Soft delete marca deleted_at sin borrar el registro
- **WHEN** se ejecuta la operación de soft delete sobre un registro
- **THEN** `deleted_at` queda con un timestamp y el registro sigue existiendo en la tabla

#### Scenario: Registro eliminado no aparece en queries normales
- **WHEN** se consultan registros de una entidad filtrando por tenant
- **THEN** los registros con `deleted_at IS NOT NULL` no aparecen en el resultado
