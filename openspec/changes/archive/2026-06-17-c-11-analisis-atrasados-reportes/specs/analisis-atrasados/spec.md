## ADDED Requirements

### Requirement: Detección de alumnos atrasados por asignación

El sistema SHALL exponer un endpoint `GET /api/v1/analisis/atrasados` que, dado un `asignacion_id`, retorne la lista de alumnos atrasados de esa asignación. Un alumno es **atrasado** si tiene actividades sin calificación registrada, o si tiene calificaciones con `aprobado = False` (RN-06). El resultado SHALL incluir el detalle de qué actividades lo clasifican como atrasado. Requiere permiso `analisis:ver`. La identidad del tenant se deriva del JWT; el `asignacion_id` SHALL pertenecer al mismo tenant o el sistema responde HTTP 404.

#### Scenario: alumno con actividades sin calificar es atrasado

- **WHEN** un usuario con permiso `analisis:ver` consulta atrasados para una asignación, y existe un alumno en el padrón activo que no tiene `Calificacion` para una o más actividades importadas
- **THEN** ese alumno aparece en la lista de atrasados con las actividades faltantes listadas

#### Scenario: alumno con nota reprobada es atrasado

- **WHEN** un usuario con permiso `analisis:ver` consulta atrasados y un alumno tiene al menos una `Calificacion` con `aprobado = False`
- **THEN** ese alumno aparece en la lista de atrasados con las actividades reprobadas listadas

#### Scenario: alumno con todas las actividades aprobadas no es atrasado

- **WHEN** un alumno tiene `Calificacion` con `aprobado = True` para todas las actividades importadas
- **THEN** ese alumno no aparece en la lista de atrasados

#### Scenario: sin padrón activo retorna lista vacía

- **WHEN** la asignación consultada no tiene padrón activo (C-09 no corrió)
- **THEN** el sistema retorna lista vacía con indicador `sin_padron: true` y HTTP 200

#### Scenario: aislamiento por tenant

- **WHEN** se consultan atrasados para una `asignacion_id`
- **THEN** solo se incluyen datos cuyo `tenant_id` coincide con el JWT; una `asignacion_id` de otro tenant retorna HTTP 404

#### Scenario: sin permiso retorna 403

- **WHEN** un usuario sin permiso `analisis:ver` consulta el endpoint de atrasados
- **THEN** el sistema responde HTTP 403

### Requirement: Ranking de actividades aprobadas por asignación

El sistema SHALL exponer un endpoint `GET /api/v1/analisis/ranking` que retorne la lista de alumnos ordenada de mayor a menor por cantidad de actividades aprobadas. Solo SHALL incluir alumnos con al menos una actividad aprobada (RN-09). Requiere permiso `analisis:ver`.

#### Scenario: ranking excluye alumnos sin aprobadas

- **WHEN** un usuario con permiso `analisis:ver` consulta el ranking de una asignación
- **THEN** solo aparecen alumnos con `count(aprobado = True) >= 1`, ordenados de mayor a menor

#### Scenario: ranking vacío sin calificaciones

- **WHEN** la asignación no tiene calificaciones importadas
- **THEN** el endpoint retorna lista vacía con HTTP 200

#### Scenario: sin permiso retorna 403

- **WHEN** un usuario sin permiso `analisis:ver` consulta el ranking
- **THEN** el sistema responde HTTP 403

### Requirement: Notas finales agrupadas por asignación

El sistema SHALL exponer un endpoint `GET /api/v1/analisis/notas-finales` que retorne, por alumno, la cantidad de actividades aprobadas sobre el total de actividades importadas para esa asignación (F2.5). Requiere permiso `analisis:ver`.

#### Scenario: nota final es razón aprobadas / total

- **WHEN** un usuario con permiso `analisis:ver` consulta notas finales
- **THEN** cada fila incluye `alumno`, `aprobadas` (count), `total_actividades` (count) y `porcentaje_aprobacion` (float 0–100)

#### Scenario: alumnos sin calificaciones aparecen con cero

- **WHEN** un alumno del padrón activo no tiene ninguna `Calificacion` importada
- **THEN** aparece con `aprobadas = 0`, `total_actividades = 0`, `porcentaje_aprobacion = 0.0`

#### Scenario: sin permiso retorna 403

- **WHEN** un usuario sin permiso `analisis:ver` consulta notas finales
- **THEN** el sistema responde HTTP 403

### Requirement: Reporte rápido de métricas por asignación

El sistema SHALL exponer un endpoint `GET /api/v1/analisis/reporte` que retorne métricas agregadas de la asignación: total de alumnos, total de atrasados, porcentaje de aprobación general, cantidad de actividades importadas (F2.4). Requiere permiso `analisis:ver`.

#### Scenario: reporte incluye métricas clave

- **WHEN** un usuario con permiso `analisis:ver` consulta el reporte de una asignación con datos importados
- **THEN** el sistema retorna `total_alumnos`, `total_atrasados`, `pct_aprobacion_general` (float), `total_actividades` y `tiene_datos` (bool)

#### Scenario: reporte sin datos

- **WHEN** la asignación no tiene calificaciones importadas ni padrón activo
- **THEN** el sistema retorna todos los contadores en cero y `tiene_datos: false`

#### Scenario: sin permiso retorna 403

- **WHEN** un usuario sin permiso `analisis:ver` consulta el reporte
- **THEN** el sistema responde HTTP 403
