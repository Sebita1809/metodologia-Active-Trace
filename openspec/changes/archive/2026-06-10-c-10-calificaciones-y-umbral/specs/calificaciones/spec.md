## ADDED Requirements

### Requirement: Modelo Calificacion con aprobado derivado

El sistema SHALL persistir una `Calificacion` por alumno por actividad evaluable, con `nota_numerica` y/o `nota_textual`, `aprobado` calculado al momento del import, `origen` (Importado | Manual) y `tenant_id`. El soft-delete SHALL aplicar (nunca hard-delete). Toda consulta SHALL filtrar por `tenant_id` derivado del JWT.

#### Scenario: aprobado derivado por nota numérica

- **WHEN** se persiste una `Calificacion` con `nota_numerica` y existe un `UmbralMateria` para esa `asignacion_id`
- **THEN** `aprobado = (nota_numerica >= umbral_pct)` y se almacena en la fila

#### Scenario: aprobado derivado por nota textual

- **WHEN** se persiste una `Calificacion` con `nota_textual` y sin `nota_numerica`
- **THEN** `aprobado = (nota_textual ∈ valores_aprobatorios del UmbralMateria)`; si `nota_textual` es "Satisfactorio" o "Supera lo esperado" el resultado SHALL ser `true` (RN-02)

#### Scenario: aprobado con umbral por defecto

- **WHEN** no existe `UmbralMateria` para la `asignacion_id` en el momento de la importación
- **THEN** se usa `umbral_pct = 60` como valor por defecto (RN-03) y `valores_aprobatorios = ["Satisfactorio", "Supera lo esperado"]`

#### Scenario: aislamiento por tenant

- **WHEN** un repositorio consulta calificaciones
- **THEN** solo devuelve filas cuyo `tenant_id` coincide con el tenant del JWT autenticado y cuyo `deleted_at` es NULL

### Requirement: Modelo UmbralMateria por asignación

El sistema SHALL persistir un `UmbralMateria` por `asignacion_id`, con `umbral_pct` (entero, defecto 60) y `valores_aprobatorios` (lista de texto). SHALL existir a lo sumo un `UmbralMateria` por `(tenant_id, asignacion_id)` (constraint UNIQUE). El umbral aplica exclusivamente al docente de esa asignación y no afecta a otros docentes en la misma materia (RN-03, RN-04).

#### Scenario: un umbral por asignación

- **WHEN** se crea un segundo `UmbralMateria` para la misma `asignacion_id`
- **THEN** el sistema rechaza la operación con error de unicidad (HTTP 409)

#### Scenario: umbral aislado entre docentes

- **WHEN** el docente A configura `umbral_pct = 70` para su asignación en Materia X
- **THEN** las calificaciones del docente B en Materia X siguen usando su propio umbral (o el defecto 60)

### Requirement: Importación de calificaciones desde LMS en dos fases

El sistema SHALL aceptar archivos `.xlsx` y `.csv` exportados del LMS. La importación SHALL ocurrir en dos pasos: (1) **preview** que parsea el archivo, detecta actividades numéricas (columnas que terminan en `(Real)`, RN-01) y textuales, y devuelve la lista de actividades detectadas SIN persistir; (2) **confirm** que recibe la lista de actividades seleccionadas, persiste las `Calificacion` correspondientes y emite auditoría `CALIFICACIONES_IMPORTAR`. Requiere permiso `calificaciones:importar`.

#### Scenario: preview detecta columnas numéricas por sufijo (Real)

- **WHEN** el archivo contiene una columna cuyo encabezado termina en `(Real)`
- **THEN** el sistema la incluye en la lista de actividades numéricas de la respuesta de preview

#### Scenario: preview detecta columnas textuales

- **WHEN** el archivo contiene columnas de escala textual (valores como "Satisfactorio", "No satisfactorio")
- **THEN** el sistema las incluye en la lista de actividades textuales de la respuesta de preview

#### Scenario: preview no persiste datos

- **WHEN** un usuario sube un archivo al endpoint de preview
- **THEN** el sistema devuelve las actividades detectadas y no crea ninguna `Calificacion`

#### Scenario: confirm persiste solo actividades seleccionadas

- **WHEN** el usuario confirma el import con una lista de `actividades_seleccionadas`
- **THEN** el sistema crea `Calificacion` solo para las actividades incluidas en esa lista y emite `CALIFICACIONES_IMPORTAR`

#### Scenario: formato de archivo inválido

- **WHEN** el archivo subido no es `.xlsx` ni `.csv`, o no contiene las columnas de identificación de alumno
- **THEN** el sistema responde HTTP 422 y no persiste datos

#### Scenario: sin permiso de importación

- **WHEN** un usuario sin permiso `calificaciones:importar` llama a preview o confirm
- **THEN** el sistema responde HTTP 403

### Requirement: Preview de reporte de finalización (stateless)

El sistema SHALL aceptar el reporte de finalización exportado del LMS y devolver un listado de actividades finalizadas por alumno que no tienen calificación registrada (RN-07, RN-08). Esta operación SHALL ser stateless: no persiste nada. Solo aplica a actividades de escala textual (RN-08). Requiere permiso `calificaciones:importar`.

#### Scenario: detecta entregadas sin calificar

- **WHEN** el reporte de finalización indica que el alumno A finalizó la actividad X y no existe `Calificacion` para ese alumno y actividad
- **THEN** la actividad X del alumno A aparece en el resultado del preview de finalización

#### Scenario: excluye actividades numéricas

- **WHEN** la actividad Y es de escala numérica
- **THEN** no aparece en el resultado del preview de finalización (RN-08)

#### Scenario: sin permiso

- **WHEN** un usuario sin permiso `calificaciones:importar` llama al endpoint de finalización
- **THEN** el sistema responde HTTP 403

### Requirement: Configuración del umbral por asignación

El sistema SHALL exponer un endpoint `PUT /api/calificaciones/umbral` para que el PROFESOR configure `umbral_pct` y `valores_aprobatorios` para su propia asignación. Si no existe un `UmbralMateria` para esa asignación, SHALL crearse (upsert). Requiere permiso `calificaciones:configurar`. El cambio de umbral no recalcula calificaciones ya persistidas.

#### Scenario: crear umbral nuevo

- **WHEN** un usuario con permiso `calificaciones:configurar` llama `PUT /umbral` y no existe `UmbralMateria` para esa asignación
- **THEN** se crea el `UmbralMateria` con los valores indicados

#### Scenario: actualizar umbral existente

- **WHEN** ya existe un `UmbralMateria` para esa asignación y el usuario llama `PUT /umbral` con nuevos valores
- **THEN** se actualiza el registro existente (upsert)

#### Scenario: umbral no recalcula calificaciones previas

- **WHEN** el docente cambia `umbral_pct` de 60 a 80 después de haber importado calificaciones
- **THEN** las `Calificacion` ya persistidas conservan su `aprobado` original; solo los imports futuros usarán el nuevo umbral

#### Scenario: sin permiso de configuración

- **WHEN** un usuario sin permiso `calificaciones:configurar` llama al endpoint de umbral
- **THEN** el sistema responde HTTP 403

### Requirement: Auditoría de importación de calificaciones

El sistema SHALL registrar un evento de auditoría con código `CALIFICACIONES_IMPORTAR` por cada confirmación de import. El registro SHALL atribuirse al usuario autenticado (actor desde el JWT) e incluir `filas_afectadas` y un `detalle` con `materia_id`, `asignacion_id` y actividades importadas.

#### Scenario: auditoría emitida al confirmar import

- **WHEN** un usuario confirma una importación de calificaciones
- **THEN** se crea un `AuditLog` con `accion = "CALIFICACIONES_IMPORTAR"`, `actor_id` igual al usuario del JWT y `filas_afectadas` igual a la cantidad de `Calificacion` creadas
