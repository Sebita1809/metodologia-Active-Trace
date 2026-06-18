## ADDED Requirements

### Requirement: Usuario — Crear con PII cifrada

El sistema SHALL permitir crear un usuario dentro de un tenant con datos personales, donde email, dni, cuil, cbu y alias_cbu SHALL ser cifrados con AES-256-GCM antes de persistir.

#### Scenario: Crear usuario con datos válidos
- **WHEN** un usuario ADMIN envía una solicitud POST a `/api/admin/usuarios` con `nombre`, `apellidos`, `email`, `dni`, `cuil`, `cbu`, `alias_cbu`, `banco`, `regional`, `facturador` y `legajo` válidos
- **THEN** el sistema SHALL crear el usuario, cifrar los campos PII, y retornar 201 con los datos del usuario (excluyendo campos cifrados en texto plano)

#### Scenario: Crear usuario con email duplicado en el mismo tenant
- **WHEN** un usuario ADMIN envía una solicitud POST a `/api/admin/usuarios` con un `email` que ya existe en el mismo tenant
- **THEN** el sistema SHALL retornar 409 Conflict indicando violación de unicidad

#### Scenario: Crear usuario con email duplicado en tenant distinto
- **WHEN** un usuario ADMIN de otro tenant envía una solicitud POST con el mismo `email` que existe en otro tenant
- **THEN** el sistema SHALL crear el usuario sin conflictos y retornar 201

#### Scenario: Crear usuario sin campos PII opcionales
- **WHEN** un usuario ADMIN envía una solicitud POST con `nombre`, `apellidos` y `email` solamente (sin dni, cuil, cbu, alias_cbu)
- **THEN** el sistema SHALL crear el usuario y retornar 201 con los campos omitidos como null

---

### Requirement: Usuario — Leer

El sistema SHALL permitir consultar usuarios por ID y listar usuarios del tenant.

#### Scenario: Obtener usuario por ID
- **WHEN** un usuario ADMIN envía una solicitud GET a `/api/admin/usuarios/{id}` con un UUID válido
- **THEN** el sistema SHALL retornar 200 con los datos del usuario, con los campos PII descifrados para la respuesta (nunca el ciphertext)

#### Scenario: Listar usuarios del tenant
- **WHEN** un usuario ADMIN envía una solicitud GET a `/api/admin/usuarios`
- **THEN** el sistema SHALL retornar 200 con la lista de usuarios del tenant (excluyendo soft-deleted)

#### Scenario: Obtener usuario de otro tenant
- **WHEN** un usuario ADMIN envía una solicitud GET a `/api/admin/usuarios/{id}` con un UUID que pertenece a otro tenant
- **THEN** el sistema SHALL retornar 404 Not Found

---

### Requirement: Usuario — Actualizar

El sistema SHALL permitir actualizar datos de un usuario existente.

#### Scenario: Actualizar email válido
- **WHEN** un usuario ADMIN envía una solicitud PATCH a `/api/admin/usuarios/{id}` con un nuevo `email`
- **THEN** el sistema SHALL actualizar el email (cifrado + recálculo de hash), actualizar `updated_at`, y retornar 200

#### Scenario: Actualizar a email duplicado
- **WHEN** un usuario ADMIN envía una solicitud PATCH a `/api/admin/usuarios/{id}` con un `email` que ya pertenece a otro usuario del mismo tenant
- **THEN** el sistema SHALL retornar 409 Conflict

#### Scenario: Actualizar nombre sin modificar PII
- **WHEN** un usuario ADMIN envía una solicitud PATCH a `/api/admin/usuarios/{id}` solo con un nuevo `nombre`
- **THEN** el sistema SHALL actualizar solo el nombre, mantener los campos PII existentes, y retornar 200

---

### Requirement: Usuario — Desactivar (soft delete)

El sistema SHALL permitir desactivar un usuario cambiando su estado a Inactivo.

#### Scenario: Desactivar usuario activo
- **WHEN** un usuario ADMIN envía una solicitud DELETE a `/api/admin/usuarios/{id}` sobre un usuario activo
- **THEN** el sistema SHALL cambiar `estado` a `Inactivo` y retornar 204 No Content

#### Scenario: Desactivar usuario ya inactivo
- **WHEN** un usuario ADMIN envía una solicitud DELETE a `/api/admin/usuarios/{id}` sobre un usuario inactivo
- **THEN** el sistema SHALL retornar 409 Conflict indicando que el usuario ya está inactivo

#### Scenario: Usuario inactivo no puede autenticarse
- **WHEN** un usuario con `estado: Inactivo` intenta iniciar sesión
- **THEN** el sistema SHALL denegar el acceso (independientemente de credenciales válidas)

---

### Requirement: PII — No exposición en logs ni respuestas

El sistema SHALL garantizar que los campos PII cifrados nunca aparezcan en texto plano en logs, excepciones ni respuestas de error.

#### Scenario: Log de creación no contiene PII en texto plano
- **WHEN** se crea un usuario
- **THEN** el log estructurado NO SHALL contener los valores planos de email, dni, cuil, cbu ni alias_cbu (puede contener el valor cifrado o un marcador)

#### Scenario: Error de validación no expone PII
- **WHEN** una solicitud de creación de usuario falla por validación
- **THEN** la respuesta de error NO SHALL incluir los valores de campos PII en texto plano en el mensaje de error

---

### Requirement: Búsqueda por email

El sistema SHALL permitir buscar usuarios por email de forma eficiente sin comprometer el cifrado.

#### Scenario: Búsqueda por email exacto
- **WHEN** un usuario ADMIN envía una solicitud GET a `/api/admin/usuarios?email=usuario@example.com`
- **THEN** el sistema SHALL retornar 200 con el usuario que coincide (usando `email_hash` para la búsqueda)

#### Scenario: Búsqueda por email inexistente
- **WHEN** un usuario ADMIN envía una solicitud GET a `/api/admin/usuarios?email=noexiste@example.com`
- **THEN** el sistema SHALL retornar 200 con una lista vacía

---

### Requirement: RBAC — Protección de endpoints de usuarios

Todos los endpoints de `/api/admin/usuarios` SHALL requerir el permiso `usuarios:gestionar`.

#### Scenario: Usuario sin permiso recibe 403
- **WHEN** un usuario autenticado sin el permiso `usuarios:gestionar` envía cualquier solicitud a `/api/admin/usuarios`
- **THEN** el sistema SHALL retornar 403 Forbidden

#### Scenario: Usuario no autenticado recibe 401
- **WHEN** un cliente no autenticado envía una solicitud a `/api/admin/usuarios`
- **THEN** el sistema SHALL retornar 401 Unauthorized
