## ADDED Requirements

### Requirement: Monitor global de actividad de alumnos del tenant

La feature SHALL presentar una vista transversal de todos los alumnos del tenant con su estado de actividades, consumiendo `GET /api/v1/calificaciones/monitor` (verificar path real en el router antes de implementar). Implementa F2.7.

#### Scenario: Ver todos los alumnos del tenant
- **WHEN** el COORDINADOR accede al monitor general sin filtros
- **THEN** la UI muestra el estado de actividades de todos los alumnos del tenant paginados

#### Scenario: Sin datos de actividades
- **WHEN** el tenant no tiene datos de calificaciones importados
- **THEN** la UI muestra el estado vacío "sin datos de actividades para el tenant"

### Requirement: Filtros del monitor general

El monitor SHALL permitir acotar la vista por materia, regional, comisión, búsqueda libre por alumno, estado de actividad y criterio de clasificación. Implementa F2.7 filtros.

#### Scenario: Filtrar por materia y regional
- **WHEN** el COORDINADOR filtra por materia "Estadística" y regional "Buenos Aires"
- **THEN** la UI muestra solo los alumnos de esa combinación

#### Scenario: Búsqueda libre por alumno
- **WHEN** el COORDINADOR escribe el apellido "García" en la búsqueda
- **THEN** la UI muestra solo los alumnos cuyo nombre o correo coincide con el criterio

#### Scenario: Limpiar filtros
- **WHEN** el COORDINADOR pulsa "Limpiar filtros"
- **THEN** la UI muestra nuevamente todos los alumnos del tenant

### Requirement: Exportar monitor general

La feature SHALL permitir descargar el listado filtrado actual como CSV.

#### Scenario: Exportar como CSV
- **WHEN** el COORDINADOR pulsa "Exportar"
- **THEN** el navegador descarga el CSV con los alumnos y su estado de actividades según los filtros activos
