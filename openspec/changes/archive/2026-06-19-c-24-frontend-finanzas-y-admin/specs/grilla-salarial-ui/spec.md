## ADDED Requirements

### Requirement: ABM de salario base por rol

La feature SHALL permitir gestionar los importes de salario base por rol (PROFESOR, TUTOR, NEXO, COORDINADOR) con fechas de vigencia desde/hasta. Consumir `GET/POST/PUT/DELETE /api/v1/liquidaciones/salarios-base` (verificar paths en router). Requiere permiso `liquidaciones:configurar-salarios`. Implementa F10.4 y RN-31.

#### Scenario: Listar salarios base vigentes
- **WHEN** el usuario accede a la grilla salarial
- **THEN** la UI muestra la tabla de salarios base con columnas: rol, importe, vigencia_desde, vigencia_hasta

#### Scenario: Crear nuevo salario base
- **WHEN** el usuario crea un salario base para PROFESOR con vigencia desde 2025-03-01
- **THEN** el nuevo salario aparece en la tabla con sus datos

#### Scenario: Validar vigencia
- **WHEN** el usuario ingresa vigencia_hasta anterior a vigencia_desde
- **THEN** Zod bloquea el envío con error en el campo vigencia_hasta

### Requirement: ABM de plus salariales

La feature SHALL permitir gestionar los plus adicionales identificados por clave, rol y descripción con vigencia temporal. Consumir `GET/POST/PUT/DELETE /api/v1/liquidaciones/plus`. Implementa F10.4 y RN-32, RN-33.

#### Scenario: Listar plus activos
- **WHEN** el usuario accede a la sección de plus
- **THEN** la UI muestra la tabla de plus con columnas: clave, rol, descripción, importe, vigencia_desde, vigencia_hasta

#### Scenario: Crear plus
- **WHEN** el usuario crea un plus "comision-extra" para TUTOR con importe 5000
- **THEN** el plus aparece en la tabla y puede asociarse en liquidaciones futuras

#### Scenario: Eliminar plus con confirmación
- **WHEN** el usuario elimina un plus
- **THEN** la UI muestra diálogo de confirmación antes de enviar el DELETE
