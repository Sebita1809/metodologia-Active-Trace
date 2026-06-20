### Requirement: Impersonación protegida por permiso explícito
El sistema SHALL requerir el permiso `impersonacion:usar` para iniciar una sesión de impersonación. Sin el permiso, el sistema SHALL responder 403 (fail-closed). La impersonación NUNCA SHALL activarse alterando un dato de la petición (parámetro, body o header): siempre SHALL ser una acción explícita, permisada y auditada.

#### Scenario: Sin permiso, no se puede impersonar
- **WHEN** un usuario sin `impersonacion:usar` intenta iniciar una impersonación
- **THEN** el sistema responde 403 y no se crea ninguna sesión de impersonación

#### Scenario: La identidad efectiva no se altera desde la petición
- **WHEN** una petición incluye un parámetro o header que pretende cambiar el usuario impersonado fuera del flujo explícito de impersonación
- **THEN** el sistema lo ignora; el usuario impersonado se deriva exclusivamente de la sesión (JWT) emitida por el flujo de inicio

### Requirement: Sesión de impersonación distinguible
El sistema SHALL emitir, al iniciar una impersonación, una sesión claramente distinguible de una sesión normal. La distinción SHALL derivarse exclusivamente del JWT verificado (un claim de impersonación), nunca de un parámetro de la petición.

#### Scenario: Sesión de impersonación marcada en el token
- **WHEN** un usuario autorizado inicia una impersonación de otro usuario
- **THEN** el sistema emite un token que identifica tanto al actor real como al usuario impersonado, distinguible de un token de sesión normal

#### Scenario: Sesión normal no es de impersonación
- **WHEN** un usuario inicia sesión por el flujo normal
- **THEN** el token no marca impersonación y la identidad efectiva es la del propio usuario

### Requirement: Atribución de acciones al actor real
El sistema SHALL atribuir toda acción realizada bajo impersonación al **actor real** (quien impersona) y SHALL registrar adicionalmente al usuario impersonado. En el log de auditoría, `actor_id` SHALL ser el actor real e `impersonado_id` SHALL ser el usuario impersonado. La trazabilidad de responsabilidad NUNCA SHALL recaer en el usuario impersonado.

#### Scenario: Acción bajo impersonación atribuida al actor real
- **WHEN** un usuario A impersona a un usuario B y, bajo esa sesión, ejecuta una acción auditable
- **THEN** el registro de auditoría tiene `actor_id = A` e `impersonado_id = B`

#### Scenario: Acción fuera de impersonación no registra impersonado
- **WHEN** un usuario A ejecuta una acción auditable en una sesión normal
- **THEN** el registro de auditoría tiene `actor_id = A` e `impersonado_id` nulo

### Requirement: Auditoría del ciclo de vida de la impersonación
El sistema SHALL registrar en el log de auditoría el inicio y el fin de cada sesión de impersonación con los códigos `IMPERSONACION_INICIAR` e `IMPERSONACION_FINALIZAR`, indicando quién impersona y a quién.

#### Scenario: Inicio de impersonación auditado
- **WHEN** un usuario A inicia una impersonación de un usuario B
- **THEN** se registra una entrada de auditoría con `accion = "IMPERSONACION_INICIAR"`, `actor_id = A` e `impersonado_id = B`

#### Scenario: Fin de impersonación auditado
- **WHEN** la sesión de impersonación de A sobre B finaliza
- **THEN** se registra una entrada de auditoría con `accion = "IMPERSONACION_FINALIZAR"`, `actor_id = A` e `impersonado_id = B`
