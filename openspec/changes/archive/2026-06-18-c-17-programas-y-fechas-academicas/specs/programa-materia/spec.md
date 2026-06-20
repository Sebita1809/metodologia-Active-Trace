## ADDED Requirements

### Requirement: Alta y asociación de programa por combinación

El sistema MUST (DEBE) permitir crear y asociar el programa oficial de una materia para una combinación específica de carrera × cohorte, persistiendo `materia_id`, `carrera_id`, `cohorte_id`, `titulo` descriptivo, `referencia_archivo` (cadena opaca a almacenamiento externo) y `tenant_id` derivado de la sesión. La combinación `(materia_id, carrera_id, cohorte_id)` MUST (DEBE) ser única entre los programas vivos del tenant.

#### Scenario: Crear programa para una combinación nueva
- WHEN un COORDINADOR autenticado asocia un programa con `materia_id`, `carrera_id`, `cohorte_id`, `titulo` y `referencia_archivo` para una combinación que aún no tiene programa vivo
- THEN el programa se persiste con `tenant_id` = tenant de la sesión y queda accesible para esa combinación

#### Scenario: referencia_archivo se almacena de forma opaca
- WHEN se crea un programa con `referencia_archivo` = "s3://bucket/programa.pdf"
- THEN el sistema persiste la cadena tal cual, sin subir, validar ni interpretar el contenido del archivo

#### Scenario: tenant_id nunca se toma del body
- WHEN una petición de alta incluye un campo `tenant_id` en el body
- THEN el schema lo rechaza (`extra='forbid'`) y el `tenant_id` se toma de la sesión

### Requirement: Reemplazo de programa preservando historial

El sistema MUST (DEBE) permitir reemplazar el programa de una combinación ya asociada: el programa anterior MUST (DEBE) quedar soft-deleted y crearse uno nuevo vivo, conservando el rastro histórico de forma append-only.

#### Scenario: Reasociar un programa a una combinación existente
- WHEN un COORDINADOR asocia un nuevo programa para una combinación `(materia, carrera, cohorte)` que ya tiene un programa vivo
- THEN el programa anterior queda soft-deleted (`deleted_at` no nulo) y el nuevo programa queda como el único vivo de esa combinación

#### Scenario: La unicidad solo aplica a programas vivos
- WHEN existe un programa soft-deleted para una combinación y se crea uno nuevo para la misma combinación
- THEN el alta es aceptada y no colisiona con la fila borrada

### Requirement: Consulta de programa por combinación

El sistema MUST (DEBE) permitir recuperar el programa vivo de una combinación materia × carrera × cohorte dentro del tenant de la sesión.

#### Scenario: Obtener el programa vigente de una combinación
- WHEN un usuario autorizado consulta el programa de `(materia, carrera, cohorte)` que tiene un programa vivo
- THEN el sistema devuelve ese programa con su `titulo` y `referencia_archivo`, excluyendo cualquier versión soft-deleted

#### Scenario: Combinación sin programa
- WHEN se consulta el programa de una combinación que no tiene programa vivo
- THEN el sistema responde 404

### Requirement: Listado de programas del tenant

El sistema MUST (DEBE) permitir listar los programas vivos del tenant de la sesión, con filtros opcionales por `materia_id`, `carrera_id` y `cohorte_id`, excluyendo los soft-deleted.

#### Scenario: Listar todos los programas del tenant
- WHEN un COORDINADOR lista programas sin filtros
- THEN el sistema devuelve todos los programas vivos del tenant, sin los eliminados

#### Scenario: Filtrar programas por materia
- WHEN un COORDINADOR lista programas filtrando por `materia_id`
- THEN el resultado contiene solo los programas vivos de esa materia dentro del tenant

### Requirement: Validación de referencias dentro del tenant

El sistema MUST (DEBE) rechazar la asociación de un programa cuya `materia_id`, `carrera_id` o `cohorte_id` no pertenezca al tenant de la sesión.

#### Scenario: Materia de otro tenant es rechazada
- WHEN un COORDINADOR del tenant A intenta crear un programa con `materia_id` perteneciente al tenant B
- THEN el sistema responde 404/422 y no persiste el programa

### Requirement: Aislamiento por tenant en programas

El sistema MUST (DEBE) garantizar que ninguna operación sobre programas exponga datos de otro tenant.

#### Scenario: Programa de otro tenant no es visible
- WHEN un usuario del tenant A consulta un programa cuyo `tenant_id` es el tenant B
- THEN el sistema responde 404 y no expone datos del tenant B

#### Scenario: Listado acotado al tenant de la sesión
- WHEN un COORDINADOR del tenant A lista programas
- THEN el resultado contiene exclusivamente programas con `tenant_id` = A

### Requirement: Control de acceso fail-closed en programas

Todos los endpoints de programas MUST (DEBEN) exigir el permiso `estructura:gestionar`; sin permiso explícito el acceso se deniega.

#### Scenario: Acceso sin permiso es denegado
- WHEN un usuario sin el permiso `estructura:gestionar` invoca cualquier endpoint de `/api/v1/programas/*`
- THEN el sistema responde 403
