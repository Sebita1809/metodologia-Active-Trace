## ADDED Requirements

### Requirement: Alta de fecha académica

El sistema MUST (DEBE) permitir crear una fecha académica registrando `materia_id`, `cohorte_id`, `tipo` (Parcial | TP | Coloquio | Recuperatorio), `numero` (entero ≥ 1), `fecha` (DATE), `titulo` y opcionalmente `periodo`, con `tenant_id` derivado de la sesión. La combinación `(materia_id, cohorte_id, tipo, numero)` MUST (DEBE) ser única entre las fechas vivas del tenant.

#### Scenario: Crear el primer parcial de una materia y cohorte
- WHEN un COORDINADOR crea una fecha con `tipo` = `Parcial`, `numero` = 1, `fecha`, `titulo`, `materia_id` y `cohorte_id`
- THEN la fecha se persiste con `tenant_id` = tenant de la sesión y queda visible en el listado de esa materia × cohorte

#### Scenario: tipo fuera del enum es rechazado
- WHEN se intenta crear una fecha con `tipo` no perteneciente a {Parcial, TP, Coloquio, Recuperatorio}
- THEN el sistema responde 422 y no persiste la fecha

#### Scenario: numero inválido es rechazado
- WHEN se intenta crear una fecha con `numero` = 0
- THEN el sistema responde 422 y no persiste la fecha

#### Scenario: Combinación tipo+numero duplicada es rechazada
- WHEN ya existe un `Parcial` número 1 vivo para una materia × cohorte y se intenta crear otro `Parcial` número 1 para la misma materia × cohorte
- THEN el sistema responde 409/422 y no crea la fecha duplicada

### Requirement: Listado tabular por materia y cohorte

El sistema MUST (DEBE) listar las fechas académicas vivas de una combinación materia × cohorte, ordenadas por `fecha` ascendente, excluyendo las soft-deleted.

#### Scenario: Listar las fechas de una materia y cohorte
- WHEN un usuario autorizado solicita las fechas de una materia × cohorte que tiene varias instancias
- THEN el sistema devuelve todas las fechas vivas de esa combinación ordenadas por `fecha`, sin las eliminadas

#### Scenario: Materia y cohorte sin fechas
- WHEN se solicitan las fechas de una combinación que no tiene ninguna fecha viva
- THEN el sistema devuelve una lista vacía

### Requirement: Edición de fecha académica

El sistema MUST (DEBE) permitir actualizar `fecha`, `titulo` y `periodo` de una fecha académica existente dentro del tenant de la sesión, refrescando `updated_at`.

#### Scenario: Reprogramar una instancia evaluativa
- WHEN un COORDINADOR actualiza la `fecha` de un parcial existente
- THEN la fecha se actualiza y `updated_at` se refresca, conservando `tipo`, `numero`, `materia_id` y `cohorte_id`

#### Scenario: Editar fecha de otro tenant es rechazado
- WHEN un usuario del tenant A intenta editar una fecha cuyo `tenant_id` es el tenant B
- THEN el sistema responde 404 y no modifica la fecha

### Requirement: Baja lógica de fecha académica

El sistema MUST (DEBE) eliminar las fechas académicas mediante soft-delete (`deleted_at`), nunca hard delete. Una combinación borrada MUST (DEBE) poder volver a crearse.

#### Scenario: Eliminar una fecha
- WHEN un COORDINADOR elimina una fecha académica
- THEN la fecha queda soft-deleted (`deleted_at` no nulo) y deja de aparecer en los listados

#### Scenario: Recrear una combinación previamente borrada
- WHEN existe una fecha soft-deleted con `tipo` = `TP`, `numero` = 2 para una materia × cohorte y se crea una nueva con la misma combinación
- THEN el alta es aceptada y no colisiona con la fila borrada

### Requirement: Generación de fragmento LMS

El sistema MUST (DEBE) generar un fragmento de contenido formateado (texto/HTML estructurado) listo para publicar en el aula virtual del LMS, a partir de las fechas vivas de una materia × cohorte ordenadas por `fecha`. El sistema NO realiza ninguna llamada al LMS en esta operación; solo construye y devuelve el contenido.

#### Scenario: Obtener el fragmento de una materia y cohorte con fechas
- WHEN un usuario autorizado solicita el fragmento LMS de una materia × cohorte que tiene fechas vivas
- THEN el sistema devuelve un contenido formateado con una entrada por instancia (`tipo`, `numero`, `titulo`, `fecha`), ordenadas por `fecha`, sin invocar al LMS

#### Scenario: Fragmento de una combinación sin fechas
- WHEN se solicita el fragmento LMS de una materia × cohorte sin fechas vivas
- THEN el sistema devuelve un contenido vacío o sin entradas, sin error

### Requirement: Validación de referencias dentro del tenant

El sistema MUST (DEBE) rechazar el alta de una fecha cuya `materia_id` o `cohorte_id` no pertenezca al tenant de la sesión.

#### Scenario: Cohorte de otro tenant es rechazada
- WHEN un COORDINADOR del tenant A intenta crear una fecha con `cohorte_id` perteneciente al tenant B
- THEN el sistema responde 404/422 y no persiste la fecha

### Requirement: Aislamiento por tenant en fechas académicas

El sistema MUST (DEBE) garantizar que ninguna operación sobre fechas académicas exponga datos de otro tenant.

#### Scenario: Fecha de otro tenant no es visible
- WHEN un usuario del tenant A solicita una fecha cuyo `tenant_id` es el tenant B
- THEN el sistema responde 404 y no expone datos del tenant B

#### Scenario: Listado y fragmento acotados al tenant de la sesión
- WHEN un COORDINADOR del tenant A lista o genera el fragmento LMS de fechas
- THEN el resultado contiene exclusivamente fechas con `tenant_id` = A

### Requirement: Control de acceso fail-closed en fechas académicas

Todos los endpoints de fechas académicas MUST (DEBEN) exigir el permiso `estructura:gestionar`; sin permiso explícito el acceso se deniega.

#### Scenario: Acceso sin permiso es denegado
- WHEN un usuario sin el permiso `estructura:gestionar` invoca cualquier endpoint de `/api/v1/fechas-academicas/*`
- THEN el sistema responde 403
