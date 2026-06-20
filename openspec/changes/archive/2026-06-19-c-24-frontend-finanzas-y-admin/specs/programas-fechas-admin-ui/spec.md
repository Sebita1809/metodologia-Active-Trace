## ADDED Requirements

### Requirement: Gestión de programas de materia

La feature SHALL permitir subir y asociar el programa oficial de cada materia para una combinación carrera × cohorte con un título descriptivo, enviando `POST /api/v1/programas` como multipart/form-data. Verificar el formato exacto del multipart en el router antes de implementar. Implementa F5.3.

#### Scenario: Subir programa de materia
- **WHEN** el ADMIN sube el PDF del programa de "Álgebra Lineal" para carrera "ING-SIS" y cohorte "MAR-2026"
- **THEN** el programa aparece en el listado con título, carrera, cohorte y enlace al documento

#### Scenario: Validar campos requeridos
- **WHEN** el usuario intenta subir un programa sin seleccionar carrera o cohorte
- **THEN** Zod bloquea el envío con error inline

#### Scenario: Listar programas existentes
- **WHEN** el ADMIN accede al módulo de programas
- **THEN** la UI muestra todos los programas del tenant con filtros por carrera y cohorte

### Requirement: Gestión de fechas de evaluaciones

La feature SHALL permitir registrar y editar fechas de parciales, trabajos prácticos y coloquios por materia, cohorte e instancia, consumiendo `GET/POST/PUT /api/v1/fechas-academicas`. Implementa F5.4.

#### Scenario: Crear fecha de evaluación
- **WHEN** el ADMIN crea la fecha del "Primer parcial" de "Álgebra Lineal" para la cohorte "MAR-2026"
- **THEN** la fecha aparece en la vista tabular y en el calendario

#### Scenario: Vista tabular y calendario
- **WHEN** el ADMIN accede a fechas de evaluaciones
- **THEN** la UI ofrece dos vistas: tabla (por materia/tipo/instancia) y calendario visual del mes

#### Scenario: Editar fecha existente
- **WHEN** el ADMIN cambia la fecha de un parcial
- **THEN** la UI actualiza la fecha en ambas vistas (tabla y calendario)
