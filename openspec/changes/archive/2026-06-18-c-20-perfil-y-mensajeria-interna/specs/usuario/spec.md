## ADDED Requirements

### Requirement: Usuario almacena sexo y modalidad de cobro
El sistema SHALL incorporar a la entidad `Usuario` dos atributos opcionales para cubrir la autogestión de perfil (F11.1): `sexo` (texto corto, nullable) y `modalidad_cobro` (enum `Factura` | `Liquidacion`, nullable). Ambos campos son aditivos y nullable; los usuarios existentes los conservan en nulo hasta que se completen. Estos campos son editables tanto desde el ABM administrativo como desde la autogestión de perfil propio.

#### Scenario: Usuario creado sin sexo ni modalidad de cobro queda con ambos nulos
- **WHEN** un ADMIN crea un Usuario sin especificar `sexo` ni `modalidad_cobro`
- **THEN** el sistema crea el Usuario con ambos campos en nulo

#### Scenario: modalidad_cobro acepta solo valores válidos
- **WHEN** se actualiza un Usuario con `modalidad_cobro` distinto de `Factura` o `Liquidacion`
- **THEN** el sistema rechaza la petición con HTTP 422

#### Scenario: La migración no rompe filas existentes
- **WHEN** se aplica la migración que agrega `sexo` y `modalidad_cobro`
- **THEN** las filas de `usuarios` preexistentes quedan con ambos campos en nulo sin error

## MODIFIED Requirements

### Requirement: Identidad del Usuario es por UUID interno, no por legajo
El sistema SHALL identificar a cada Usuario por su `id` (UUID interno). Los campos `legajo` y `legajo_profesional` son atributos de negocio opcionales y NUNCA SHALL usarse como credencial ni como selector de identidad en endpoints o sesión. Adicionalmente, el campo `cuil` (identificador tributario principal) SHALL ser inmutable desde la autogestión de perfil propio (`PATCH /api/perfil`): solo el ABM administrativo con permiso `usuarios:gestionar` puede modificarlo.

#### Scenario: El legajo es opcional al crear un usuario
- **WHEN** un ADMIN crea un Usuario sin `legajo`
- **THEN** el sistema crea el Usuario exitosamente con `legajo` nulo

#### Scenario: El endpoint de detalle usa el UUID, no el legajo
- **WHEN** se accede al detalle de un Usuario
- **THEN** la ruta lo selecciona por su `id` (UUID), no por su `legajo`

#### Scenario: El CUIL no es editable desde la autogestión de perfil
- **WHEN** un usuario intenta modificar su `cuil` vía `PATCH /api/perfil`
- **THEN** el sistema rechaza el campo (HTTP 422) y el CUIL permanece sin cambios

#### Scenario: El ABM administrativo sí puede editar el CUIL
- **WHEN** un ADMIN con permiso `usuarios:gestionar` hace PATCH a `/api/admin/usuarios/{id}` con un nuevo `cuil`
- **THEN** el sistema actualiza el CUIL cifrado y retorna HTTP 200
