## ADDED Requirements

### Requirement: Usuario almacena PII cifrada en reposo (AES-256)
El sistema SHALL almacenar los campos de PII de `Usuario` (`email`, `dni`, `cuil`, `cbu`, `alias_cbu`) cifrados con AES-256 mediante el `CryptoService`. Estos campos NUNCA SHALL persistirse en texto plano en la base de datos. El cifrado ocurre en la capa Service antes de persistir, y el descifrado ocurre solo al construir respuestas que deban exponerlos.

#### Scenario: Email se persiste cifrado, no en texto plano
- **WHEN** un ADMIN crea un Usuario con `email = "docente@uni.edu"`
- **THEN** el valor almacenado en la columna `email` de la tabla `usuario` es un token cifrado (no contiene la cadena `docente@uni.edu` en claro)

#### Scenario: DNI, CUIL, CBU y alias_cbu se persisten cifrados
- **WHEN** un ADMIN crea un Usuario con `dni`, `cuil`, `cbu` y `alias_cbu`
- **THEN** cada uno de esos valores se almacena como token cifrado y ninguno aparece en texto plano en la fila persistida

#### Scenario: Respuesta de la API descifra los campos solicitados
- **WHEN** un ADMIN hace GET a `/api/admin/usuarios/{id}` de un usuario existente
- **THEN** el sistema retorna los campos de PII descifrados en claro en la respuesta (p. ej. el `email` original)

### Requirement: PII nunca aparece en logs ni en representaciones de depuración
El sistema SHALL garantizar que ningún campo de PII (`email`, `dni`, `cuil`, `cbu`, `alias_cbu`) aparezca en logs estructurados, mensajes de error, ni en `__repr__`/`__str__` del modelo `Usuario`. Las referencias a un usuario en logs SHALL usar su `id` (UUID).

#### Scenario: __repr__ del Usuario no expone PII
- **WHEN** se evalúa `repr(usuario)` de una instancia de `Usuario`
- **THEN** la cadena resultante contiene el `id` y `tenant_id` pero NO contiene el email, dni, cuil, cbu ni alias_cbu en claro ni cifrados

#### Scenario: Los logs no contienen PII al crear un usuario
- **WHEN** un ADMIN crea un Usuario y se inspeccionan los logs de la operación
- **THEN** los logs no contienen el email, dni, cuil, cbu ni alias_cbu del usuario en texto plano

### Requirement: Email es único por tenant
El sistema SHALL garantizar que el par `(tenant_id, email)` sea único. Dado que el email se almacena cifrado de forma no determinística, la unicidad se aplica mediante una columna derivada `email_hash` (HMAC determinístico del email normalizado) con índice único `(tenant_id, email_hash)`, validada además en la capa Service.

#### Scenario: Email duplicado dentro del mismo tenant es rechazado
- **WHEN** un ADMIN intenta crear un Usuario con un `email` que ya existe (mismo tenant)
- **THEN** el sistema retorna HTTP 409 indicando el conflicto de unicidad de email

#### Scenario: Mismo email en otro tenant es permitido
- **WHEN** un ADMIN crea un Usuario con un `email` que ya existe en un tenant diferente
- **THEN** el sistema crea el Usuario exitosamente (HTTP 201)

#### Scenario: email_hash no se expone en las respuestas
- **WHEN** un ADMIN hace GET a un Usuario
- **THEN** la respuesta no incluye el campo `email_hash`

### Requirement: Identidad del Usuario es por UUID interno, no por legajo
El sistema SHALL identificar a cada Usuario por su `id` (UUID interno). Los campos `legajo` y `legajo_profesional` son atributos de negocio opcionales y NUNCA SHALL usarse como credencial ni como selector de identidad en endpoints o sesión.

#### Scenario: El legajo es opcional al crear un usuario
- **WHEN** un ADMIN crea un Usuario sin `legajo`
- **THEN** el sistema crea el Usuario exitosamente con `legajo` nulo

#### Scenario: El endpoint de detalle usa el UUID, no el legajo
- **WHEN** se accede al detalle de un Usuario
- **THEN** la ruta lo selecciona por su `id` (UUID), no por su `legajo`

### Requirement: Usuario soporta estado Activo/Inactivo
El sistema SHALL permitir cambiar el `estado` de un Usuario entre `Activo` e `Inactivo`. Un usuario creado sin especificar estado SHALL quedar `Activo`. Los usuarios inactivos se conservan en el histórico.

#### Scenario: Usuario creado como Activo por defecto
- **WHEN** un ADMIN crea un Usuario sin especificar estado
- **THEN** el Usuario queda con `estado = Activo`

#### Scenario: Usuario se puede inactivar
- **WHEN** un ADMIN hace PATCH a un Usuario con `estado = Inactivo`
- **THEN** el sistema actualiza el estado y retorna HTTP 200

### Requirement: ABM de Usuario requiere permiso `usuarios:gestionar`
El sistema SHALL proteger todos los endpoints de escritura de `/api/admin/usuarios` (POST, PATCH, DELETE) con el guard `require_permission("usuarios:gestionar")`. Solo usuarios con ese permiso (ADMIN) pueden crear, modificar o eliminar usuarios. Fail-closed: sin permiso explícito → 403.

#### Scenario: Usuario sin permiso no puede crear ficha de usuario
- **WHEN** un usuario sin permiso `usuarios:gestionar` hace POST a `/api/admin/usuarios`
- **THEN** el sistema retorna HTTP 403

#### Scenario: Petición sin token es rechazada
- **WHEN** se hace POST a `/api/admin/usuarios` sin token de autenticación
- **THEN** el sistema retorna HTTP 401

#### Scenario: ADMIN puede crear usuario
- **WHEN** un ADMIN con permiso `usuarios:gestionar` hace POST a `/api/admin/usuarios` con datos válidos
- **THEN** el sistema crea el Usuario y retorna HTTP 201 con el recurso creado

### Requirement: Usuario está aislado por tenant
El sistema SHALL filtrar todas las consultas de `Usuario` por el `tenant_id` derivado del JWT del usuario autenticado. Un usuario de un tenant no puede ver ni modificar fichas de otro tenant.

#### Scenario: Listado retorna solo usuarios del tenant del solicitante
- **WHEN** un ADMIN hace GET a `/api/admin/usuarios`
- **THEN** el sistema retorna únicamente los usuarios cuyo `tenant_id` coincide con el tenant del JWT

#### Scenario: Acceso a usuario de otro tenant retorna 404
- **WHEN** un ADMIN intenta acceder a un Usuario de un tenant diferente
- **THEN** el sistema retorna HTTP 404

### Requirement: Usuario soporta soft delete
El sistema SHALL marcar los Usuarios como eliminados (`deleted_at` no nulo) en lugar de borrarlos físicamente. Los usuarios eliminados no aparecen en los listados normales.

#### Scenario: Eliminar usuario lo marca con deleted_at
- **WHEN** un ADMIN hace DELETE a un Usuario existente
- **THEN** el sistema setea `deleted_at` con la fecha/hora actual y retorna HTTP 204

#### Scenario: Usuario eliminado no aparece en el listado
- **WHEN** un ADMIN hace GET a `/api/admin/usuarios` después de eliminar un usuario
- **THEN** el usuario eliminado no aparece en los resultados
