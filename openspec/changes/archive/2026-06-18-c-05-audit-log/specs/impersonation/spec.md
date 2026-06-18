## ADDED Requirements

### Requirement: Inicio de impersonación
El sistema SHALL permitir que un usuario con permiso `impersonacion:usar` inicie una sesión de impersonación sobre otro usuario del mismo tenant. La acción SHALL quedar registrada en el audit-log con código `IMPERSONACION_INICIAR`.

#### Scenario: Iniciar impersonación exitosamente
- **WHEN** un usuario con permiso `impersonacion:usar` solicita impersonar a otro usuario del mismo tenant
- **THEN** se crea un JWT de tipo "impersonation" con actor_id (quien impersona) e impersonado_id (quien es impersonado)
- **THEN** se registra un audit-log con acción IMPERSONACION_INICIAR, actor_id=quien impersona, impersonado_id=quien es impersonado

#### Scenario: Iniciar impersonación sin permiso
- **WHEN** un usuario SIN permiso `impersonacion:usar` intenta impersonar a otro usuario
- **THEN** recibe 403 Forbidden

#### Scenario: Iniciar impersonación de usuario inexistente
- **WHEN** se intenta impersonar a un usuario que no existe en el tenant
- **THEN** recibe 404 Not Found

### Requirement: Sesión distinguible durante impersonación
El sistema SHALL generar un JWT de tipo "impersonation" durante la sesión activa de impersonación, claramente distinguible de una sesión normal. El JWT incluye los claims estándar más `actor_id` (usuario real) e `impersonado_id` (usuario suplantado).

#### Scenario: JWT de impersonación tiene tipo distinto
- **WHEN** se inicia impersonación
- **THEN** el JWT devuelto tiene `type: "impersonation"`

#### Scenario: UserContext refleja impersonación activa
- **WHEN** un usuario autenticado con JWT de tipo impersonation accede a un endpoint
- **THEN** `UserContext.is_impersonating` es True
- **THEN** `UserContext.actor_id` es el UUID del usuario real
- **THEN** `UserContext.impersonated_user_id` es el UUID del usuario impersonado
- **THEN** `UserContext.user_id` y `UserContext.email` corresponden al usuario impersonado

### Requirement: Atribución de acciones bajo impersonación
El sistema SHALL registrar toda acción realizada durante una sesión de impersonación con el actor real (quien impersona) como `actor_id` y el usuario impersonado como `impersonado_id` en el audit-log.

#### Scenario: Acción bajo impersonación registra actor real
- **WHEN** un usuario impersonando a otro realiza una acción auditable
- **THEN** el audit-log tiene `actor_id` = quien impersona e `impersonado_id` = quien es impersonado

### Requirement: Fin de impersonación
El sistema SHALL permitir finalizar una sesión de impersonación activa. La acción SHALL quedar registrada en el audit-log con código `IMPERSONACION_FINALIZAR`. Al finalizar, se devuelve un JWT de sesión normal del usuario real.

#### Scenario: Finalizar impersonación exitosamente
- **WHEN** un usuario con impersonación activa solicita finalizar
- **THEN** se registra un audit-log con acción IMPERSONACION_FINALIZAR
- **THEN** se devuelve un nuevo JWT de tipo "access" para el usuario real

### Requirement: Consulta de sesiones de impersonación activas
El sistema SHALL permitir al usuario con permiso `auditoria:ver` consultar las sesiones de impersonación activas en su tenant.

#### Scenario: Listar impersonaciones activas
- **WHEN** un usuario con `auditoria:ver` consulta las impersonaciones activas
- **THEN** se retorna una lista de sesiones activas con actor_real e impersonado
