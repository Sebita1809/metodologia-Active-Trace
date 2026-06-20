## ADDED Requirements

### Requirement: Visualización del umbral de aprobación

La feature SHALL mostrar el umbral de aprobación vigente y los valores aprobatorios de la comisión seleccionada consumiendo `GET /api/calificaciones/umbral`, presentando el default (60 %) cuando no haya umbral configurado.

#### Scenario: Umbral por defecto
- **WHEN** la comisión no tiene umbral configurado
- **THEN** la UI muestra el umbral por defecto (60 %) y los valores aprobatorios por defecto

#### Scenario: Umbral configurado
- **WHEN** la comisión ya tiene un umbral configurado
- **THEN** la UI muestra el porcentaje y los valores aprobatorios persistidos

### Requirement: Configuración del umbral de aprobación

La feature SHALL permitir fijar el umbral porcentual y los valores aprobatorios vía `PUT /api/calificaciones/umbral`, validando la entrada con React Hook Form + Zod antes de enviarla.

#### Scenario: Guardar umbral válido
- **WHEN** el usuario ingresa un umbral porcentual válido y confirma
- **THEN** la UI envía la configuración al backend y refleja el umbral actualizado tras la respuesta

#### Scenario: Umbral fuera de rango
- **WHEN** el usuario ingresa un porcentaje fuera del rango permitido
- **THEN** la validación de Zod impide el envío y muestra el mensaje de error en el formulario
