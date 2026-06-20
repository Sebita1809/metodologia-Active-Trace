## ADDED Requirements

### Requirement: Vista de mis tareas (docente)

La feature SHALL presentar las tareas asignadas al usuario autenticado filtradas por sus comisiones, consumiendo `GET /api/v1/tareas?asignado_a=<user_id>`. Accesible a TUTOR, PROFESOR, COORDINADOR. Implementa F8.1.

#### Scenario: Ver tareas propias
- **WHEN** un PROFESOR accede al módulo de tareas
- **THEN** la UI muestra solo las tareas asignadas a ese usuario con estado, materia y asignador

#### Scenario: Sin tareas asignadas
- **WHEN** el usuario no tiene tareas asignadas
- **THEN** la UI muestra el estado vacío "sin tareas asignadas"

### Requirement: Cambiar estado de tarea propia

La feature SHALL permitir al docente cambiar el estado de una tarea asignada (Abierta → En progreso → Completada) enviando `PUT /api/v1/tareas/{id}`. Implementa F8.1 y FL-05 paso 4.

#### Scenario: Marcar tarea en progreso
- **WHEN** el docente cambia el estado de "Abierta" a "En progreso"
- **THEN** la UI actualiza el estado de la fila sin recargar el listado

### Requirement: Agregar comentario a una tarea

La feature SHALL permitir agregar comentarios/evidencias al hilo de una tarea enviando `POST /api/v1/tareas/{id}/comentarios`. Implementa FL-05 paso 5.

#### Scenario: Agregar comentario exitoso
- **WHEN** el usuario escribe un comentario y confirma
- **THEN** el comentario aparece en el hilo de la tarea con timestamp y autor

#### Scenario: Comentario vacío bloqueado
- **WHEN** el usuario intenta enviar un comentario vacío
- **THEN** la UI bloquea el envío

### Requirement: Vista global de tareas (coordinador)

La feature SHALL presentar todas las tareas del tenant con filtros por docente asignado, docente asignador, materia, estado y búsqueda libre, consumiendo `GET /api/v1/tareas`. Visible solo para COORDINADOR y ADMIN. Implementa F8.3.

#### Scenario: Filtrar tareas por docente y estado
- **WHEN** el COORDINADOR filtra por docente "López" y estado "Abierta"
- **THEN** la UI muestra solo las tareas abiertas asignadas a ese docente

#### Scenario: Limpiar filtros
- **WHEN** el COORDINADOR limpia todos los filtros
- **THEN** la UI muestra el listado completo del tenant

### Requirement: Crear tarea y asignar a docente

La feature SHALL permitir al COORDINADOR crear una tarea con materia, docente asignado, descripción y criterio de cierre enviando `POST /api/v1/tareas`. Implementa FL-05 paso 1.

#### Scenario: Crear tarea asignada
- **WHEN** el COORDINADOR crea una tarea para el docente "García" en la materia "Álgebra"
- **THEN** la tarea aparece en el listado global con estado "Abierta" y en el panel de mis tareas del docente

### Requirement: Aprobar cierre o devolver tarea (coordinador)

La feature SHALL permitir al COORDINADOR cambiar el estado de cualquier tarea a "Cerrada" o devolverla al docente con una observación. Implementa FL-05 pasos 6–7.

#### Scenario: Aprobar cierre de tarea
- **WHEN** el COORDINADOR marca una tarea como "Cerrada"
- **THEN** la tarea sale del panel de tareas activas del docente y queda en el historial

#### Scenario: Devolver tarea con observación
- **WHEN** el COORDINADOR devuelve la tarea al docente con comentario "Falta adjuntar evidencia"
- **THEN** el comentario queda en el hilo y la tarea vuelve al estado "En progreso"
