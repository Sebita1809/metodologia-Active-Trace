## ADDED Requirements

### Requirement: Monitor de seguimiento de alumnos (vista tutor/profesor)

La feature SHALL presentar un monitor filtrable del estado de actividades de los alumnos de la comisión para los roles TUTOR y PROFESOR, reutilizando los datos de análisis/reportes de la comisión seleccionada.

#### Scenario: Mostrar estado de actividades
- **WHEN** el usuario abre el monitor de seguimiento de una comisión con datos
- **THEN** la UI muestra el estado de actividades de los alumnos de esa comisión

#### Scenario: Comisión sin datos
- **WHEN** la comisión no tiene datos de actividades
- **THEN** la UI muestra un estado informativo "sin datos de seguimiento"

### Requirement: Filtros del monitor de seguimiento

El monitor SHALL permitir acotar la vista por alumno, correo, comisión, actividad y mínimo de actividad cumplida, aplicando los filtros sobre los datos presentados.

#### Scenario: Aplicar filtro por alumno
- **WHEN** el usuario filtra por nombre o correo de alumno
- **THEN** la UI muestra únicamente las filas que coinciden con el criterio

#### Scenario: Filtro por mínimo de actividad cumplida
- **WHEN** el usuario fija un mínimo de actividad cumplida
- **THEN** la UI muestra únicamente los alumnos que alcanzan o superan ese mínimo
