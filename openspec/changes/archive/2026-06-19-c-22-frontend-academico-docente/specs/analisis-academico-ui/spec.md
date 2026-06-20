## ADDED Requirements

### Requirement: Tabla de alumnos atrasados

La feature SHALL presentar la tabla de alumnos atrasados de la comisión consumiendo `GET /api/v1/analisis/atrasados` por `asignacion_id`, sin replicar en el cliente la lógica de negocio que define "atrasado".

#### Scenario: Listar atrasados
- **WHEN** la comisión tiene datos importados y el usuario abre la vista de atrasados
- **THEN** la UI muestra la tabla de alumnos atrasados devuelta por el backend

#### Scenario: Sin atrasados
- **WHEN** el backend devuelve una lista vacía de atrasados
- **THEN** la UI muestra un estado informativo de "sin alumnos atrasados"

### Requirement: Ranking de actividades aprobadas

La feature SHALL presentar el ranking de actividades aprobadas por alumno consumiendo `GET /api/v1/analisis/ranking`.

#### Scenario: Mostrar ranking
- **WHEN** el usuario abre la vista de ranking de una comisión con datos
- **THEN** la UI muestra la tabla ordenada por cantidad de actividades aprobadas por alumno

### Requirement: Notas finales agrupadas

La feature SHALL presentar las notas finales agrupadas por alumno consumiendo `GET /api/v1/analisis/notas-finales`.

#### Scenario: Mostrar notas finales
- **WHEN** el usuario abre la vista de notas finales de una comisión con datos
- **THEN** la UI muestra la nota final calculada por alumno

### Requirement: Reportes rápidos por comisión

La feature SHALL presentar las métricas rápidas de la comisión consumiendo `GET /api/v1/analisis/reporte`, mostrando un estado informativo cuando aún no hay datos o no se seleccionaron actividades.

#### Scenario: Mostrar reporte
- **WHEN** el usuario abre los reportes rápidos de una comisión con datos
- **THEN** la UI muestra las métricas clave (actividades, aprobaciones, tendencias)

#### Scenario: Reporte sin datos
- **WHEN** la comisión no tiene datos o no se seleccionaron actividades
- **THEN** la UI muestra un estado informativo en lugar de métricas vacías
