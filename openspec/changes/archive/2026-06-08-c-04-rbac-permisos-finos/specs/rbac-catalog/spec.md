## ADDED Requirements

### Requirement: Catálogo de roles administrable por tenant
El sistema SHALL persistir los roles como datos en una tabla `roles` scoped por `tenant_id`, no como una lista fija en código. El catálogo SHALL incluir, sembrados por defecto, los roles del dominio: ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN y FINANZAS. Un tenant SHALL poder tener roles propios adicionales sin afectar a otros tenants.

#### Scenario: Roles del dominio sembrados al crear el tenant
- **WHEN** se aplica la migración del catálogo RBAC sobre un tenant
- **THEN** existen en `roles`, para ese tenant, los 7 roles del dominio (ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS)

#### Scenario: Roles aislados por tenant
- **WHEN** el tenant A tiene un rol y se consulta el catálogo del tenant B
- **THEN** el rol del tenant A no aparece en el catálogo del tenant B

#### Scenario: Seed idempotente
- **WHEN** el seed del catálogo se ejecuta una segunda vez sobre el mismo tenant
- **THEN** no se duplican roles ni permisos; el conteo permanece igual

### Requirement: Catálogo de permisos `modulo:accion`
El sistema SHALL persistir los permisos como capacidades atómicas con clave canónica `modulo:accion` (única por tenant) en una tabla `permisos`. Cada endpoint protegido referencia un permiso por su clave; la clave es el contrato entre el endpoint y el catálogo.

#### Scenario: Permiso identificado por clave canónica
- **WHEN** se consulta un permiso por la clave `comunicacion:enviar`
- **THEN** el catálogo retorna el permiso correspondiente del tenant actual

#### Scenario: Clave de permiso única dentro del tenant
- **WHEN** se intenta crear un segundo permiso con la clave `comunicacion:enviar` en el mismo tenant
- **THEN** el sistema rechaza la operación por violación de unicidad

### Requirement: Matriz rol × permiso como datos con alcance
El sistema SHALL modelar la asociación rol → permiso en una tabla `rol_permiso` (N:N), nunca hardcodeada. Cada fila SHALL llevar un `alcance` con valor `global` o `propio`, reflejando el modificador `(propio)` de la matriz de capacidades. La matriz base de `03_actores_y_roles.md` §3.3 SHALL sembrarse por defecto.

#### Scenario: Matriz base sembrada
- **WHEN** se aplica el seed del catálogo RBAC sobre un tenant
- **THEN** el rol ADMIN tiene asignado, entre otros, `calificaciones:importar` con alcance `global`, y el rol PROFESOR tiene `calificaciones:importar` con alcance `propio`

#### Scenario: Rol sin permisos no otorga acceso
- **WHEN** el rol NEXO se siembra sin filas en `rol_permiso`
- **THEN** un usuario cuyo único rol es NEXO no obtiene ningún permiso efectivo

#### Scenario: Administración de la matriz por permiso del propio módulo
- **WHEN** un usuario sin el permiso `rbac:administrar` intenta modificar la matriz rol × permiso
- **THEN** el sistema responde 403 y la matriz no cambia

### Requirement: Asignación de roles a usuarios con vigencia temporal
El sistema SHALL asociar roles a usuarios mediante una tabla `usuario_rol` scoped por `tenant_id`, con `vigente_desde` y `vigente_hasta` (esta última puede ser abierta/NULL). Una asignación SHALL considerarse vigente solo si la fecha actual cae dentro de su rango. Las asignaciones vencidas SHALL conservarse en el histórico (no se borran físicamente).

#### Scenario: Asignación vigente otorga el rol
- **WHEN** un usuario tiene una asignación a PROFESOR con `vigente_desde` en el pasado y `vigente_hasta` nulo
- **THEN** la asignación se considera vigente y aporta los permisos de PROFESOR

#### Scenario: Asignación vencida no otorga el rol
- **WHEN** un usuario tiene una asignación a COORDINADOR cuyo `vigente_hasta` ya pasó
- **THEN** la asignación no se considera vigente y no aporta permisos, pero permanece registrada en el histórico

#### Scenario: Múltiples roles simultáneos
- **WHEN** un usuario tiene asignaciones vigentes a PROFESOR y a COORDINADOR al mismo tiempo
- **THEN** ambas asignaciones se consideran activas (no hay exclusión mutua entre roles)
