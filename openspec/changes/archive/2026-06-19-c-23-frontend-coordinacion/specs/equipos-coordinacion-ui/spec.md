## ADDED Requirements

### Requirement: Vista de asignaciones del tenant

La feature SHALL presentar la lista de asignaciones activas del tenant con filtros por materia, carrera, cohorte, nombre de docente, rol y relación de reporte, consumiendo `GET /api/v1/asignaciones`.

#### Scenario: Listar asignaciones con filtros
- **WHEN** el COORDINADOR accede a la página de equipos y aplica un filtro por materia
- **THEN** la UI muestra únicamente las asignaciones que coinciden con la materia seleccionada

#### Scenario: Sin asignaciones activas
- **WHEN** no existen asignaciones para los filtros aplicados
- **THEN** la UI muestra un estado informativo "sin asignaciones para los criterios seleccionados"

### Requirement: Alta individual de asignación

La feature SHALL permitir crear una asignación individual mediante un formulario con campos materia, carrera, cohorte, rol, docente y fechas de vigencia (desde/hasta), enviando `POST /api/v1/asignaciones`.

#### Scenario: Crear asignación exitosa
- **WHEN** el COORDINADOR completa el formulario de nueva asignación y confirma
- **THEN** la UI envía la asignación al backend y actualiza la lista sin recargar la página

#### Scenario: Validación de fechas
- **WHEN** el usuario ingresa una fecha "hasta" anterior a la fecha "desde"
- **THEN** Zod bloquea el envío y muestra el error de validación inline

### Requirement: Alta masiva de asignaciones

La feature SHALL permitir seleccionar múltiples docentes y asignarlos en bloque a materia × carrera × cohorte × rol con una vigencia, enviando `POST /api/v1/asignaciones/masiva`.

#### Scenario: Asignar múltiples docentes
- **WHEN** el COORDINADOR selecciona 3 docentes y confirma la asignación masiva
- **THEN** la UI envía el lote y muestra el resultado con los éxitos y errores individuales

#### Scenario: Lote con errores parciales
- **WHEN** el backend devuelve éxitos parciales (algunos docentes ya asignados)
- **THEN** la UI lista las asignaciones creadas y las que fallaron con su motivo

### Requirement: Clonar equipo docente entre períodos

La feature SHALL permitir seleccionar un equipo origen (materia × carrera × cohorte) y un destino (misma materia × carrera × nueva cohorte), enviando `POST /api/v1/asignaciones/clonar`. Implementa FL-03 paso 2.

#### Scenario: Clonar equipo con éxito
- **WHEN** el COORDINADOR selecciona origen y destino y confirma el clonado
- **THEN** la UI crea todas las asignaciones del destino y confirma cuántas se generaron

#### Scenario: Destino con asignaciones existentes
- **WHEN** el destino ya tiene asignaciones para la misma combinación
- **THEN** la UI muestra una advertencia y permite confirmar o cancelar el clonado

### Requirement: Modificar vigencia general del equipo

La feature SHALL permitir actualizar las fechas desde/hasta de todas las asignaciones de un equipo en una operación, enviando `PUT /api/v1/asignaciones/{id}/vigencia` para cada asignación del equipo.

#### Scenario: Actualizar vigencia del equipo
- **WHEN** el COORDINADOR selecciona un equipo y establece nuevas fechas de vigencia
- **THEN** la UI actualiza todas las asignaciones del equipo y confirma el resultado

### Requirement: Exportar equipo docente

La feature SHALL permitir descargar las asignaciones filtradas como archivo CSV consumiendo `GET /api/v1/asignaciones/exportar`.

#### Scenario: Exportar como CSV
- **WHEN** el COORDINADOR pulsa "Exportar"
- **THEN** el navegador descarga un CSV con las columnas: docente, rol, materia, carrera, cohorte, vigencia_desde, vigencia_hasta, estado
