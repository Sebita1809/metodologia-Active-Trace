## ADDED Requirements

### Requirement: Catálogo administrable de roles
El sistema SHALL mantener un catálogo de roles en la tabla `rol`, administrable como datos (no hardcodeado). Cada rol tiene nombre único por tenant, descripción opcional y es referenciable por UUID.

#### Scenario: Crear rol con datos válidos
- **WHEN** se inserta un rol con nombre, tenant_id y descripción
- **THEN** el rol se persiste con un UUID único y timestamps

#### Scenario: Dos roles con el mismo nombre en distinto tenant no colisionan
- **WHEN** se crean dos roles con el mismo nombre en tenants distintos
- **THEN** ambos roles existen sin error de unicidad

#### Scenario: Nombre de rol duplicado dentro del mismo tenant es rechazado
- **WHEN** se intenta crear un segundo rol con el mismo nombre en el mismo tenant
- **THEN** la operación falla con error de unicidad

### Requirement: Catálogo administrable de permisos
El sistema SHALL mantener un catálogo de permisos en la tabla `permiso`. Cada permiso tiene un código único del formato `modulo:accion` (ej: `calificaciones:importar`), con columnas separadas `modulo` y `accion`.

#### Scenario: Crear permiso con código válido
- **WHEN** se inserta un permiso con modulo="calificaciones" y accion="importar"
- **THEN** el permiso se persiste con codigo="calificaciones:importar"

#### Scenario: Permiso duplicado es rechazado
- **WHEN** se intenta crear un permiso con un codigo que ya existe
- **THEN** la operación falla con error de unicidad

### Requirement: Matriz Rol → Permiso (RolPermiso)
El sistema SHALL mantener una tabla `rol_permiso` que asocia roles con permisos. Un rol puede tener múltiples permisos y un permiso puede pertenecer a múltiples roles.

#### Scenario: Asignar permiso a rol
- **WHEN** se asocia un permiso existente a un rol existente
- **THEN** la relación se persiste en rol_permiso

#### Scenario: Permiso no existente no puede asociarse
- **WHEN** se intenta asociar un permiso inexistente a un rol
- **THEN** la operación falla por violación de clave foránea

#### Scenario: Rol no existente no puede recibir permisos
- **WHEN** se intenta asociar un permiso a un rol inexistente
- **THEN** la operación falla por violación de clave foránea

### Requirement: Seed de roles del dominio
El sistema SHALL incluir en la migración inicial los 7 roles del dominio: ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS. Estos roles se crean sin asociación a ningún tenant específico (son catálogo global).

#### Scenario: Roles base existen después de migrar
- **WHEN** se ejecuta la migración 003
- **THEN** existen registros para ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS

### Requirement: Seed de matriz de permisos por rol
El sistema SHALL incluir en la migración inicial la matriz de permisos definida en `knowledge-base/03_actores_y_roles.md §3.3`, asociando cada rol con sus permisos correspondientes.

#### Scenario: ADMIN tiene permiso estructura:gestionar
- **WHEN** se consultan los permisos del rol ADMIN
- **THEN** incluye `estructura:gestionar`

#### Scenario: PROFESOR tiene permiso atrasados:ver pero NO estructura:gestionar
- **WHEN** se consultan los permisos del rol PROFESOR
- **THEN** incluye `atrasados:ver` y NO incluye `estructura:gestionar`

#### Scenario: ALUMNO no tiene permiso calificaciones:importar
- **WHEN** se consultan los permisos del rol ALUMNO
- **THEN** NO incluye `calificaciones:importar`

### Requirement: Guard require_permission
El sistema SHALL proveer una FastAPI dependency `require_permission("modulo:accion")` que:
- Recibe el usuario autenticado de `get_current_user`
- Resuelve server-side los permisos del usuario consultando `rol_permiso` mediante sus roles
- Si el usuario NO tiene el permiso → HTTP 403 Forbidden
- Si el usuario SÍ tiene el permiso → permite continuar

#### Scenario: Usuario con permiso accede al endpoint
- **WHEN** un usuario autenticado con el permiso requerido accede a un endpoint protegido
- **THEN** recibe 200 OK (o el código esperado del endpoint)

#### Scenario: Usuario sin permiso recibe 403
- **WHEN** un usuario autenticado SIN el permiso requerido accede a un endpoint protegido
- **THEN** recibe 403 Forbidden

#### Scenario: Usuario no autenticado recibe 401, no 403
- **WHEN** un usuario NO autenticado accede a un endpoint protegido con require_permission
- **THEN** recibe 401 Unauthorized (el guard de auth se ejecuta antes)

### Requirement: Resolución multi-rol
El sistema SHALL calcular los permisos efectivos como la UNIÓN de los permisos de todos los roles del usuario. Si un usuario tiene los roles PROFESOR y COORDINADOR, tiene los permisos de ambos.

#### Scenario: Usuario multi-rol hereda permisos de ambos roles
- **WHEN** un usuario con roles [PROFESOR, COORDINADOR] consulta un endpoint que requiere `avisos:publicar`
- **THEN** se le concede acceso (porque COORDINADOR tiene ese permiso aunque PROFESOR no)

### Requirement: Aislamiento por tenant en resolución de permisos
El sistema SHALL acotar la resolución de permisos al tenant del usuario autenticado. Un rol definido en un tenant no otorga permisos en otro tenant.

#### Scenario: Mismo rol en distinto tenant no otorga permisos cruzados
- **WHEN** un usuario del Tenant A tiene rol ADMIN, y un usuario del Tenant B también tiene rol ADMIN
- **THEN** cada usuario solo tiene permisos dentro de su propio tenant

### Requirement: Migración Alembic 003
El sistema SHALL incluir una migración Alembic (`003_rol_permiso`) que cree las tablas `rol`, `permiso` y `rol_permiso` con sus claves foráneas, constraints de unicidad y los seed datos de roles y permisos.

#### Scenario: Migración ejecutada correctamente
- **WHEN** se ejecuta `alembic upgrade head`
- **THEN** las tablas rol, permiso y rol_permiso existen en el schema

#### Scenario: Rollback de migración funciona
- **WHEN** se ejecuta `alembic downgrade -1`
- **THEN** las tablas rol, permiso y rol_permiso son eliminadas
