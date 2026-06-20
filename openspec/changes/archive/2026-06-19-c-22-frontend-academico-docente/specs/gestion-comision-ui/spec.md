## ADDED Requirements

### Requirement: Selección de comisión

La feature SHALL permitir al PROFESOR/TUTOR seleccionar la comisión (asignación = materia × cohorte) sobre la que va a operar, fijando un `asignacion_id` que alimenta todas las sub-vistas académicas. El `asignacion_id` es dato de negocio enviado al backend como query/form; la identidad, roles y tenant del usuario salen exclusivamente del JWT.

#### Scenario: Selección fija el contexto de la comisión
- **WHEN** el usuario selecciona una comisión disponible en el selector
- **THEN** el `asignacion_id` seleccionado queda como contexto activo de la feature y las sub-vistas (importación, umbral, atrasados, ranking, notas finales, reportes, comunicación, seguimiento) usan ese identificador en sus peticiones

#### Scenario: Sin comisión seleccionada
- **WHEN** todavía no hay ninguna comisión seleccionada
- **THEN** la pantalla muestra un estado informativo que invita a seleccionar una comisión y no dispara peticiones de datos académicos

### Requirement: Orquestación de sub-vistas y estados informativos

La pantalla de gestión de comisión SHALL orquestar las sub-vistas académicas y MUST mostrar un estado informativo cuando aún no hay datos importados o no se seleccionaron actividades, sin presentar tablas vacías ni errores.

#### Scenario: Comisión sin datos importados
- **WHEN** la comisión seleccionada no tiene calificaciones importadas
- **THEN** las vistas de análisis (atrasados, ranking, notas finales, reportes) muestran un estado informativo "sin datos" en lugar de una tabla vacía

#### Scenario: Datos importados disponibles
- **WHEN** la comisión tiene calificaciones importadas y actividades seleccionadas
- **THEN** las sub-vistas de análisis presentan sus tablas y métricas correspondientes

### Requirement: Autorización delegada al backend

La feature SHALL tratar los guards de UI como UX y MUST tratar el `403` del backend como autoridad final de autorización (fail-closed). El frontend nunca deriva identidad ni permisos de datos de la petición.

#### Scenario: Backend rechaza por falta de permiso
- **WHEN** el backend responde `403` a una operación sobre la comisión
- **THEN** la UI presenta el estado de acceso denegado y no asume permiso pese a que la ruta sea visible
