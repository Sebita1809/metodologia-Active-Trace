## ADDED Requirements

### Requirement: BaseRepository aplica scope de tenant en toda operación
El sistema SHALL proveer `BaseRepository[T]` genérico que recibe `tenant_id: UUID` y `session: AsyncSession` en su constructor. Todo método público (get, list, create, update, soft_delete) aplica el filtro `tenant_id == self._tenant_id` sin excepción. Es imposible instanciar `BaseRepository` sin `tenant_id`.

#### Scenario: get por id filtra por tenant
- **WHEN** se llama `repo.get(id=uuid_A)` desde un repositorio construido con `tenant_id=T1`
- **THEN** solo retorna el registro si existe Y pertenece a `T1`; retorna `None` si el registro existe en otro tenant

#### Scenario: list solo devuelve registros del tenant
- **WHEN** existen registros de T1 y T2 en la misma tabla, y se llama `repo.list()` con `tenant_id=T1`
- **THEN** el resultado contiene solo los registros de T1

### Requirement: BaseRepository excluye registros soft-deleted por defecto
El sistema SHALL filtrar registros con `deleted_at IS NOT NULL` en todos los métodos de consulta pública. Los métodos de auditoría que necesiten ver registros eliminados DEBEN usar variantes explícitas.

#### Scenario: list excluye registros eliminados
- **WHEN** existen registros activos y eliminados (soft delete) del mismo tenant
- **THEN** `repo.list()` retorna solo los activos

#### Scenario: soft_delete marca deleted_at sin borrar
- **WHEN** se llama `repo.soft_delete(id=uuid)` sobre un registro existente del tenant
- **THEN** el campo `deleted_at` queda con el timestamp actual y el registro persiste en la tabla

### Requirement: BaseRepository rechaza operaciones entre tenants
El sistema SHALL garantizar que un repositorio construido con `tenant_id=T1` NO pueda operar sobre registros de `T2`, incluso si se provee explícitamente el `id` de un registro de T2.

#### Scenario: soft_delete de registro ajeno no tiene efecto
- **WHEN** se llama `repo.soft_delete(id=id_de_T2)` con un repo del T1
- **THEN** la operación no elimina ni modifica el registro de T2 (retorna 0 rows affected o lanza NotFound)
