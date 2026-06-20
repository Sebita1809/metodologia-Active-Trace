## ADDED Requirements

### Requirement: Asignacion vincula Usuario, rol de negocio y contexto académico
El sistema SHALL permitir crear una `Asignacion` que vincule un `Usuario` (`usuario_id`) con un rol de negocio (`rol`) y un contexto académico opcional (`materia_id`, `carrera_id`, `cohorte_id`, `comisiones`). El `rol` SHALL ser uno de `PROFESOR | TUTOR | COORDINADOR | NEXO | ADMIN | FINANZAS`.

#### Scenario: Crear asignación con contexto académico completo
- **WHEN** un usuario con permiso `equipos:asignar` crea una Asignacion con `usuario_id`, `rol = "PROFESOR"`, `materia_id`, `carrera_id`, `cohorte_id` y `comisiones`
- **THEN** el sistema persiste la asignación y retorna HTTP 201 con el recurso creado

#### Scenario: Rol de negocio inválido es rechazado
- **WHEN** se crea una Asignacion con un `rol` que no pertenece al conjunto permitido
- **THEN** el sistema retorna HTTP 422 (validación)

#### Scenario: Contexto académico es opcional para roles tenant-globales
- **WHEN** se crea una Asignacion con `rol = "FINANZAS"` sin `materia_id`, `carrera_id` ni `cohorte_id`
- **THEN** el sistema crea la asignación exitosamente con esos campos nulos

#### Scenario: comisiones puede estar vacía
- **WHEN** se crea una Asignacion sin `comisiones`
- **THEN** el sistema crea la asignación con una lista de comisiones vacía

### Requirement: Asignacion es independiente del catálogo de roles RBAC
El sistema SHALL almacenar `Asignacion.rol` como el nombre del rol de negocio (texto/enum), NO como una FK al catálogo de Roles de RBAC. La `Asignacion` describe contexto académico de trabajo y NO otorga ni revoca permisos del sistema RBAC; los permisos viven en `UsuarioRol` (C-04).

#### Scenario: La asignación no modifica permisos RBAC del usuario
- **WHEN** se crea una Asignacion con `rol = "COORDINADOR"` para un Usuario
- **THEN** los permisos RBAC efectivos del usuario autenticado no cambian por la existencia de esa asignación (siguen determinados por `UsuarioRol`)

### Requirement: estado_vigencia es derivado, nunca persistido
El sistema SHALL calcular `estado_vigencia` (`Vigente | Vencida`) a partir de `desde`/`hasta` y la fecha actual, sin almacenarlo en la base de datos. Una asignación es `Vencida` cuando `hasta` no es nulo y la fecha actual es posterior a `hasta`; en caso contrario, dentro de su ventana, es `Vigente`. `hasta` nulo significa vigencia abierta.

#### Scenario: Asignación con hasta futuro es Vigente
- **WHEN** se consulta una Asignacion con `desde` pasado y `hasta` futuro
- **THEN** el sistema reporta `estado_vigencia = "Vigente"`

#### Scenario: Asignación con hasta pasado es Vencida
- **WHEN** se consulta una Asignacion con `hasta` anterior a la fecha actual
- **THEN** el sistema reporta `estado_vigencia = "Vencida"`

#### Scenario: Asignación con hasta nulo es Vigente (vigencia abierta)
- **WHEN** se consulta una Asignacion con `hasta = null` y `desde` ya iniciado
- **THEN** el sistema reporta `estado_vigencia = "Vigente"`

#### Scenario: estado_vigencia no existe como columna
- **WHEN** se inspecciona el esquema de la tabla `asignacion`
- **THEN** no existe ninguna columna `estado_vigencia` (es un valor calculado en serialización)

### Requirement: Asignación vencida se conserva para el histórico
El sistema SHALL conservar las asignaciones vencidas como registro histórico de auditoría. Una asignación vencida NO SHALL eliminarse automáticamente y NO SHALL otorgar permisos, pero SHALL permanecer consultable.

#### Scenario: Asignación vencida sigue siendo consultable
- **WHEN** un usuario con permiso de lectura consulta una Asignacion cuyo `hasta` ya pasó
- **THEN** el sistema retorna la asignación con `estado_vigencia = "Vencida"` (no se oculta ni se borra)

#### Scenario: Vencimiento no dispara borrado
- **WHEN** la fecha actual supera el `hasta` de una asignación
- **THEN** la asignación permanece persistida (no se elimina ni se marca con `deleted_at` por el solo hecho de vencer)

### Requirement: Asignacion modela jerarquía mediante responsable
El sistema SHALL permitir definir un `responsable_id` (FK opcional a `Usuario`) que indica el supervisor jerárquico de la persona asignada. Esto modela la jerarquía docente (a quién reporta el asignado).

#### Scenario: Crear asignación con responsable
- **WHEN** se crea una Asignacion con un `responsable_id` que apunta a otro Usuario del mismo tenant
- **THEN** el sistema persiste la relación de responsable y retorna HTTP 201

#### Scenario: responsable_id es opcional
- **WHEN** se crea una Asignacion sin `responsable_id`
- **THEN** el sistema crea la asignación con `responsable_id` nulo

### Requirement: Un Usuario puede tener múltiples asignaciones
El sistema SHALL permitir que un mismo `Usuario` tenga varias `Asignacion` con distintos roles, materias, carreras, cohortes o períodos de vigencia simultáneamente.

#### Scenario: Usuario con dos roles en distintas materias
- **WHEN** se crean dos Asignacion para el mismo `usuario_id`, una con `rol = "PROFESOR"` en una materia y otra con `rol = "TUTOR"` en otra materia
- **THEN** el sistema persiste ambas asignaciones sin conflicto

### Requirement: CRUD de Asignacion requiere permiso `equipos:asignar`
El sistema SHALL proteger los endpoints de escritura de `/api/asignaciones` con el guard `require_permission("equipos:asignar")`. Solo usuarios con ese permiso (ADMIN, COORDINADOR) pueden crear, modificar o eliminar asignaciones. Fail-closed: sin permiso explícito → 403.

#### Scenario: Usuario sin permiso no puede crear asignación
- **WHEN** un usuario sin permiso `equipos:asignar` hace POST a `/api/asignaciones`
- **THEN** el sistema retorna HTTP 403

#### Scenario: Petición sin token es rechazada
- **WHEN** se hace POST a `/api/asignaciones` sin token de autenticación
- **THEN** el sistema retorna HTTP 401

#### Scenario: COORDINADOR puede crear asignación
- **WHEN** un COORDINADOR con permiso `equipos:asignar` hace POST a `/api/asignaciones` con datos válidos
- **THEN** el sistema crea la asignación y retorna HTTP 201

### Requirement: Listado de Asignacion soporta filtros
El sistema SHALL permitir filtrar el listado de asignaciones del tenant por `materia_id`, `carrera_id`, `cohorte_id`, `usuario_id`, `rol` y `responsable_id`.

#### Scenario: Filtrar asignaciones por materia
- **WHEN** un usuario con permiso hace GET a `/api/asignaciones?materia_id={id}`
- **THEN** el sistema retorna únicamente las asignaciones de esa materia dentro del tenant

#### Scenario: Filtrar asignaciones por responsable
- **WHEN** un usuario con permiso hace GET a `/api/asignaciones?responsable_id={id}`
- **THEN** el sistema retorna únicamente las asignaciones cuyo `responsable_id` coincide

### Requirement: Asignacion está aislada por tenant
El sistema SHALL filtrar todas las consultas de `Asignacion` por el `tenant_id` derivado del JWT. Un usuario de un tenant no puede ver ni modificar asignaciones de otro tenant.

#### Scenario: Listado retorna solo asignaciones del tenant del solicitante
- **WHEN** un usuario con permiso hace GET a `/api/asignaciones`
- **THEN** el sistema retorna únicamente las asignaciones cuyo `tenant_id` coincide con el del JWT

#### Scenario: Acceso a asignación de otro tenant retorna 404
- **WHEN** un usuario intenta acceder a una Asignacion de un tenant diferente
- **THEN** el sistema retorna HTTP 404

### Requirement: Asignacion soporta soft delete
El sistema SHALL marcar las asignaciones eliminadas con `deleted_at` no nulo en lugar de borrarlas físicamente. Las asignaciones eliminadas no aparecen en los listados normales.

#### Scenario: Eliminar asignación la marca con deleted_at
- **WHEN** un usuario con permiso hace DELETE a una Asignacion existente
- **THEN** el sistema setea `deleted_at` con la fecha/hora actual y retorna HTTP 204
