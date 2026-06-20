## ADDED Requirements

### Requirement: ABM de carreras

La feature SHALL permitir al ADMIN crear, editar y cambiar el estado (activa/inactiva) de carreras, consumiendo `GET/POST/PUT /api/v1/carreras`. Implementa F5.1 y FL-12 paso 3.

#### Scenario: Crear carrera
- **WHEN** el ADMIN crea una carrera con código "ING-SIS" y nombre "Ingeniería en Sistemas"
- **THEN** la carrera aparece en el listado con estado "activa"

#### Scenario: Desactivar carrera
- **WHEN** el ADMIN cambia el estado de una carrera a "inactiva"
- **THEN** la carrera permanece en el listado con badge "inactiva" y no está disponible para nuevas cohortes

#### Scenario: Validar código único
- **WHEN** el usuario intenta crear una carrera con un código ya existente
- **THEN** la UI muestra el error devuelto por el backend

### Requirement: ABM de cohortes

La feature SHALL permitir al ADMIN crear, editar y cambiar el estado de cohortes con nombre, año de inicio y fechas de vigencia (desde/hasta), consumiendo `GET/POST/PUT /api/v1/cohortes`. Implementa F5.2 y FL-12 paso 3.

#### Scenario: Crear cohorte
- **WHEN** el ADMIN crea la cohorte "MAR-2026" con año 2026 y fechas de vigencia
- **THEN** la cohorte aparece en el listado y está disponible para asignaciones

#### Scenario: Validar fechas de vigencia
- **WHEN** el usuario ingresa fecha_hasta anterior a fecha_desde
- **THEN** Zod bloquea el envío con error en el campo fecha_hasta

### Requirement: ABM de materias

La feature SHALL permitir al ADMIN crear, editar y cambiar el estado de materias, consumiendo `GET/POST/PUT /api/v1/materias`. Implementa F5.1 contexto materias.

#### Scenario: Crear materia
- **WHEN** el ADMIN crea la materia "Álgebra Lineal"
- **THEN** la materia aparece disponible para asignaciones y programas

#### Scenario: Desactivar materia
- **WHEN** el ADMIN desactiva una materia
- **THEN** la materia no aparece en los selectores de nuevas asignaciones pero mantiene sus datos históricos
