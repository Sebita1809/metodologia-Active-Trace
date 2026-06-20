## ADDED Requirements

### Requirement: Guard de autenticación
El sistema SHALL proteger las rutas privadas con un guard que verifica la existencia de una sesión válida. Si no hay sesión, SHALL redirigir al login conservando la ruta de destino para volver tras autenticarse.

#### Scenario: Acceso sin sesión redirige a login
- **WHEN** un usuario no autenticado navega a una ruta protegida
- **THEN** el guard redirige a la pantalla de login

#### Scenario: Acceso con sesión permite la ruta
- **WHEN** un usuario autenticado navega a una ruta protegida que no exige rol específico
- **THEN** el guard permite el render de la ruta

#### Scenario: Retorno a la ruta original tras login
- **WHEN** un usuario no autenticado intenta acceder a una ruta protegida y luego inicia sesión correctamente
- **THEN** el frontend lo redirige a la ruta originalmente solicitada

### Requirement: Guard por rol/permiso (fail-closed)
El sistema SHALL permitir declarar las rutas que exigen un rol (o conjunto de roles) presente en la sesión. Si la sesión no incluye el rol requerido, el guard SHALL denegar el acceso (fail-closed) mostrando un estado de acceso denegado, sin asumir permiso por defecto.

#### Scenario: Rol suficiente
- **WHEN** un usuario cuyo JWT incluye un rol requerido navega a una ruta que lo exige
- **THEN** el guard permite el acceso a la ruta

#### Scenario: Rol insuficiente (fail-closed)
- **WHEN** un usuario cuyo JWT NO incluye ninguno de los roles requeridos navega a una ruta que los exige
- **THEN** el guard deniega el acceso y muestra un estado de "acceso denegado" en lugar del contenido protegido

### Requirement: El backend es la autoridad de autorización
El sistema SHALL tratar el guard por rol/permiso como mecanismo de experiencia de usuario, no como control de seguridad. Cuando el backend responde `403` a una operación, el frontend SHALL respetar ese resultado como autoridad final aunque la UI hubiera permitido intentarla.

#### Scenario: 403 del backend prevalece
- **WHEN** el frontend permite intentar una acción según la sesión pero el backend responde `403`
- **THEN** el frontend muestra el estado de acceso denegado y no insiste, respetando al backend como autoridad de autorización
