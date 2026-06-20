## ADDED Requirements

### Requirement: Listado de usuarios del tenant

La feature SHALL presentar todos los usuarios del tenant con sus roles, estado (activo/inactivo) y datos básicos, consumiendo `GET /api/v1/usuarios`. Solo ADMIN. Implementa F4.1.

#### Scenario: Ver listado de usuarios
- **WHEN** el ADMIN accede al módulo de usuarios
- **THEN** la UI muestra la tabla con columnas: nombre, identificación, rol, regional, estado, modalidad de cobro

#### Scenario: Sin usuarios cargados
- **WHEN** el tenant no tiene usuarios además del ADMIN
- **THEN** la UI muestra el estado vacío con acción "Crear usuario"

### Requirement: Crear usuario docente

La feature SHALL permitir crear un usuario con rol docente (PROFESOR, TUTOR, NEXO, COORDINADOR) incluyendo nombre, identificación fiscal, datos bancarios (banco, CBU/alias), regional, rol, modalidad de cobro y estado. Enviar `POST /api/v1/usuarios`. Los campos CBU/alias se envían en el body JSON nunca en URL. Implementa F4.1 y FL-12 paso 4.

#### Scenario: Crear usuario con datos bancarios
- **WHEN** el ADMIN crea un PROFESOR con CBU válido
- **THEN** el usuario aparece en el listado con su rol y estado "activo"

#### Scenario: Validar campos requeridos
- **WHEN** el usuario intenta crear sin nombre o sin rol
- **THEN** Zod bloquea el envío con errores inline en los campos faltantes

### Requirement: Editar y activar/desactivar usuario

La feature SHALL permitir editar los datos de un usuario y cambiar su estado activo/inactivo enviando `PUT /api/v1/usuarios/{id}`. Implementa F4.1.

#### Scenario: Desactivar usuario
- **WHEN** el ADMIN desactiva un usuario
- **THEN** el usuario queda con estado "inactivo" y no puede iniciar sesión

#### Scenario: Editar datos bancarios
- **WHEN** el ADMIN actualiza el CBU de un usuario
- **THEN** los nuevos datos se guardan en el backend y se muestran en la vista de detalle

### Requirement: Vista de detalle de usuario

La feature SHALL mostrar todos los datos del usuario en una vista de detalle, incluyendo los datos bancarios descifrados por el backend. Los datos se muestran como texto plano en la UI (el descifrado ocurre en el backend).

#### Scenario: Ver detalle con CBU
- **WHEN** el ADMIN abre el detalle de un usuario con CBU registrado
- **THEN** la UI muestra el CBU tal como lo devuelve la API (el backend descifra antes de responder)
