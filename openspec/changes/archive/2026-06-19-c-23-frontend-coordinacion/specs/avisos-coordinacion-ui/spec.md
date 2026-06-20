## ADDED Requirements

### Requirement: Listar avisos activos e inactivos

La feature SHALL presentar todos los avisos del tenant con su estado (activo/inactivo), severidad, alcance, roles destinatarios y contadores de acknowledgment, consumiendo `GET /api/v1/avisos`.

#### Scenario: Ver listado de avisos
- **WHEN** el COORDINADOR accede al módulo de avisos
- **THEN** la UI muestra la tabla de avisos con columnas: título, severidad, alcance, estado, fecha inicio, fecha fin, acks recibidos

#### Scenario: Sin avisos creados
- **WHEN** no existen avisos en el tenant
- **THEN** la UI muestra un estado vacío con acción para crear el primer aviso

### Requirement: Crear aviso con scope y configuración completa

La feature SHALL permitir crear un aviso mediante formulario con: título, cuerpo (texto enriquecido), alcance (global/materia/cohorte), contexto condicional (materia y/o cohorte si el alcance no es global), roles destinatarios (multi-select), severidad, fecha inicio, fecha fin, orden de prioridad, estado activo, y require_ack. Envía `POST /api/v1/avisos`. Implementa FL-09.

#### Scenario: Crear aviso global con ack requerido
- **WHEN** el COORDINADOR completa el formulario con alcance global, roles PROFESOR+TUTOR y require_ack=true
- **THEN** la UI crea el aviso y lo muestra en el listado con contador de acks en 0

#### Scenario: Validar contexto condicional
- **WHEN** el usuario selecciona alcance "materia" pero no elige ninguna materia
- **THEN** Zod bloquea el envío e indica que el campo materia es requerido para este alcance

#### Scenario: Fecha fin anterior a fecha inicio
- **WHEN** el usuario ingresa fecha_fin anterior a fecha_inicio
- **THEN** Zod bloquea el envío con error en el campo fecha_fin

### Requirement: Editar y desactivar aviso existente

La feature SHALL permitir editar los campos de un aviso existente enviando `PUT /api/v1/avisos/{id}` y cambiar su estado activo/inactivo.

#### Scenario: Desactivar aviso
- **WHEN** el COORDINADOR cambia el estado de un aviso de activo a inactivo
- **THEN** la UI actualiza el estado y el aviso deja de mostrarse a los destinatarios

### Requirement: Eliminar aviso (soft delete)

La feature SHALL permitir eliminar un aviso enviando `DELETE /api/v1/avisos/{id}` con confirmación previa al usuario.

#### Scenario: Confirmar eliminación
- **WHEN** el usuario pulsa "Eliminar" en un aviso
- **THEN** la UI muestra un diálogo de confirmación antes de enviar la petición

#### Scenario: Cancelar eliminación
- **WHEN** el usuario cancela el diálogo de confirmación
- **THEN** el aviso no es eliminado y permanece en el listado

### Requirement: Panel de acknowledgments por aviso

La feature SHALL mostrar cuántos destinatarios confirmaron la lectura de un aviso con require_ack=true, en una vista de detalle del aviso.

#### Scenario: Ver contadores de ack
- **WHEN** el COORDINADOR abre el detalle de un aviso con require_ack=true
- **THEN** la UI muestra el conteo de usuarios que confirmaron lectura vs. total de destinatarios
