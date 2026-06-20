## ADDED Requirements

### Requirement: Preview de actividades del archivo LMS

La feature SHALL permitir subir el archivo de calificaciones exportado del LMS y previsualizar las actividades detectadas sin persistir nada, consumiendo `POST /api/calificaciones/preview` con el `asignacion_id` como dato de negocio.

#### Scenario: Preview exitoso
- **WHEN** el usuario sube un archivo de calificaciones válido para la comisión seleccionada
- **THEN** la UI muestra la lista de actividades detectadas sin haber persistido datos en el backend

#### Scenario: Archivo inválido
- **WHEN** el backend responde `422` al previsualizar un archivo con formato inválido
- **THEN** la UI muestra el mensaje de error y permite reintentar con otro archivo

### Requirement: Selección de actividades y confirmación de importación

La feature SHALL permitir al usuario seleccionar qué actividades incluir en el análisis y confirmar la importación vía `POST /api/calificaciones/import`, enviando el archivo y el cuerpo de la solicitud según el contrato multipart del backend.

#### Scenario: Confirmar importación con actividades seleccionadas
- **WHEN** el usuario selecciona una o más actividades y confirma la importación
- **THEN** la UI envía el archivo junto con la solicitud que incluye las actividades seleccionadas y, al recibir `201`, refleja que las calificaciones quedaron importadas

#### Scenario: Sin actividades seleccionadas
- **WHEN** el usuario intenta confirmar sin haber seleccionado ninguna actividad
- **THEN** la UI bloquea la confirmación y solicita seleccionar al menos una actividad

### Requirement: Detección y exportación de entregas sin corregir

La feature SHALL permitir subir el reporte de finalización del LMS (`POST /api/calificaciones/finalizacion-preview`), mostrar la tabla de posibles entregas sin corregir y exportarla a un archivo descargable generado en el cliente.

#### Scenario: Mostrar entregas sin corregir
- **WHEN** el usuario sube el reporte de finalización de la comisión
- **THEN** la UI muestra la tabla de actividades detectadas como posiblemente sin corregir, identificadas por alumno y actividad

#### Scenario: Exportar listado
- **WHEN** el usuario solicita exportar el listado de entregas sin corregir
- **THEN** la UI genera y descarga un archivo con esas entregas a partir de los datos ya recibidos
