## ADDED Requirements

### Requirement: Panel de métricas de coloquios

La feature SHALL presentar los KPIs globales de coloquios: total de alumnos cargados, instancias activas, reservas activas y notas registradas. Implementa F7.1.

#### Scenario: Ver métricas del panel
- **WHEN** el COORDINADOR accede al módulo de coloquios
- **THEN** la UI muestra los 4 KPIs en tarjetas de cabecera con los valores actuales del tenant

### Requirement: Listado de convocatorias de coloquio

La feature SHALL presentar todas las convocatorias activas con sus métricas operativas (materia, instancia, días disponibles, convocados, reservas activas, cupos libres) consumiendo `GET /api/v1/evaluaciones`. Implementa F7.4.

#### Scenario: Ver convocatorias activas
- **WHEN** el COORDINADOR accede a la sección de convocatorias
- **THEN** la UI muestra la tabla de convocatorias con métricas operativas por fila

#### Scenario: Sin convocatorias activas
- **WHEN** no hay convocatorias activas en el tenant
- **THEN** la UI muestra el estado vacío con acción para crear la primera convocatoria

### Requirement: Crear convocatoria de coloquio

La feature SHALL permitir crear una convocatoria con: materia, instancia, días disponibles y cupos por día, enviando `POST /api/v1/evaluaciones`. Implementa F7.3.

#### Scenario: Crear convocatoria con múltiples días
- **WHEN** el COORDINADOR define una convocatoria con 3 días disponibles y 10 cupos cada uno
- **THEN** la convocatoria aparece en el listado con 30 cupos totales

#### Scenario: Validar cupos positivos
- **WHEN** el usuario ingresa 0 cupos para un día
- **THEN** Zod bloquea el envío indicando que los cupos deben ser mayores a 0

### Requirement: Importar padrón de alumnos habilitados a convocatoria

La feature SHALL permitir importar el padrón de alumnos habilitados para una convocatoria específica enviando `POST /api/v1/evaluaciones/{id}/alumnos`. Implementa F7.2.

#### Scenario: Importar padrón con éxito
- **WHEN** el COORDINADOR sube el archivo de padrón y confirma la importación
- **THEN** la UI muestra cuántos alumnos fueron cargados exitosamente y actualiza el KPI "convocados"

#### Scenario: Archivo inválido
- **WHEN** el usuario sube un archivo con formato no reconocido
- **THEN** la UI muestra el error devuelto por el backend sin importar ningún registro

### Requirement: Agenda de reservas activas por convocatoria

La feature SHALL mostrar las reservas de turnos por convocatoria (alumno, día reservado, cupo) consumiendo `GET /api/v1/reservas?evaluacion_id=<id>`. Implementa F7.5 supervisor view.

#### Scenario: Ver agenda de una convocatoria
- **WHEN** el COORDINADOR abre la agenda de una convocatoria
- **THEN** la UI muestra las reservas agrupadas por día con el alumno y su turno

#### Scenario: Convocatoria sin reservas
- **WHEN** ningún alumno ha reservado turno
- **THEN** la UI muestra "sin reservas activas para esta convocatoria"

### Requirement: Registro académico consolidado de resultados

La feature SHALL presentar los resultados finales de coloquio registrados por convocatoria (alumno, nota, instancia) consumiendo `GET /api/v1/resultados`. Implementa F7.5 registro académico.

#### Scenario: Ver resultados de una convocatoria
- **WHEN** el COORDINADOR accede al registro académico de una convocatoria
- **THEN** la UI muestra la tabla con alumno, instancia y nota final registrada
