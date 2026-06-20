## ADDED Requirements

### Requirement: Resolución de permisos efectivos server-side por request
El sistema SHALL resolver los permisos efectivos de un usuario en cada request protegido como la **unión** de los permisos de todos sus roles **vigentes**, acotada por su `tenant_id`. La identidad (`user_id`, `tenant_id`) SHALL provenir exclusivamente del JWT verificado. Los permisos NUNCA SHALL leerse del JWT ni almacenarse en él; se calculan contra la base de datos en cada petición.

#### Scenario: Unión de permisos de múltiples roles
- **WHEN** un usuario tiene roles vigentes PROFESOR (con `encuentros:gestionar`) y COORDINADOR (con `avisos:publicar`)
- **THEN** sus permisos efectivos incluyen tanto `encuentros:gestionar` como `avisos:publicar`

#### Scenario: Solo roles vigentes aportan permisos
- **WHEN** un usuario tiene un rol vencido que otorgaba `liquidaciones:cerrar` y ningún rol vigente con ese permiso
- **THEN** `liquidaciones:cerrar` no figura entre sus permisos efectivos

#### Scenario: Permisos acotados por tenant
- **WHEN** se resuelven los permisos efectivos de un usuario del tenant A
- **THEN** solo se consideran roles, asignaciones y permisos del tenant A; ningún dato de otro tenant influye en el resultado

#### Scenario: Permisos no provienen del token
- **WHEN** un JWT manipulado declara un rol o permiso que el usuario no tiene asignado en la BD
- **THEN** la resolución ignora el contenido del token para autorización y se basa exclusivamente en las asignaciones persistidas

### Requirement: Guard `require_permission` fail-closed
El sistema SHALL proveer una dependency `require_permission("modulo:accion")` que cada endpoint protegido declara para exigir un permiso explícito. Si el usuario autenticado no posee el permiso requerido con alcance suficiente, el guard SHALL responder `HTTPException(403)` antes de ejecutar el handler. La ausencia de `require_permission` en un endpoint NUNCA SHALL otorgar acceso implícito a recursos protegidos (fail-closed).

#### Scenario: Usuario con el permiso accede
- **WHEN** un endpoint declara `require_permission("comunicacion:enviar")` y el usuario tiene ese permiso efectivo
- **THEN** el guard permite la ejecución del handler

#### Scenario: Usuario sin el permiso recibe 403
- **WHEN** un endpoint declara `require_permission("comunicacion:enviar")` y el usuario NO tiene ese permiso efectivo
- **THEN** el guard responde `HTTPException(403)` y el handler no se ejecuta

#### Scenario: 403 distinto de 401
- **WHEN** un usuario autenticado válido carece del permiso exigido
- **THEN** la respuesta es `403` (autenticado pero no autorizado), nunca `401` (que indica falta de autenticación)

### Requirement: Semántica de alcance `(propio)` vs global
El sistema SHALL distinguir entre alcance `global` y `propio` al evaluar un permiso. Un endpoint declarado con `scope="propio"` SHALL aceptar un permiso concedido con alcance `propio` o `global`; un endpoint declarado con `scope="global"` SHALL exigir alcance `global`. Cuando el alcance concedido es `propio`, el guard SHALL exponer ese alcance al handler para que la capa de Service/Repository filtre los datos al dueño. El alcance `global` SHALL prevalecer sobre `propio` cuando ambos provienen de roles distintos del mismo usuario.

#### Scenario: Alcance propio satisface endpoint de alcance propio
- **WHEN** un endpoint declara `require_permission("atrasados:ver", scope="propio")` y el usuario tiene `atrasados:ver` con alcance `propio`
- **THEN** el guard permite la ejecución y expone al handler el alcance `propio` para que filtre por dueño

#### Scenario: Alcance propio no satisface endpoint de alcance global
- **WHEN** un endpoint declara `require_permission("atrasados:ver", scope="global")` y el usuario solo tiene `atrasados:ver` con alcance `propio`
- **THEN** el guard responde `HTTPException(403)`

#### Scenario: Global prevalece sobre propio
- **WHEN** un usuario tiene `atrasados:ver` con alcance `propio` por un rol y `global` por otro rol vigente
- **THEN** el alcance efectivo resultante es `global`
