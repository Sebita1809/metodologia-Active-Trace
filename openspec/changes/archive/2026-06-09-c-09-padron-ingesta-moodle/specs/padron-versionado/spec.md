## ADDED Requirements

### Requirement: Modelo versionado de padrón

El sistema SHALL representar el padrón de alumnos como versiones por `materia × cohorte`. Una `VersionPadron` agrupa una o más `EntradaPadron`. Toda fila de ambas entidades SHALL llevar `tenant_id` y SHALL filtrarse por tenant en todo acceso a datos. El borrado SHALL ser soft-delete (nunca físico).

#### Scenario: Crear una versión con sus entradas

- **WHEN** un usuario con permiso `padron:cargar` confirma una carga para `(materia, cohorte)`
- **THEN** el sistema crea una `VersionPadron` con `cargado_por`, `cargado_at` y `activa = true`, junto con una `EntradaPadron` por cada alumno detectado, todas con el mismo `tenant_id` derivado del JWT

#### Scenario: Aislamiento por tenant

- **WHEN** un repositorio de padrón consulta versiones o entradas
- **THEN** solo devuelve filas cuyo `tenant_id` coincide con el tenant del usuario autenticado y cuyo `deleted_at` es NULL

### Requirement: Una sola versión activa por materia y cohorte

El sistema SHALL garantizar que exista a lo sumo una `VersionPadron` con `activa = true` por combinación `(tenant_id, materia_id, cohorte_id)`. Activar una versión nueva SHALL desactivar la versión activa anterior de esa combinación, sin borrarla.

#### Scenario: Activar una versión nueva desactiva la anterior

- **WHEN** ya existe una versión activa para `(materia, cohorte)` y se confirma una carga nueva para la misma combinación
- **THEN** la versión anterior queda con `activa = false` y la nueva queda con `activa = true`, conservándose ambas en la base de datos

#### Scenario: El historial de versiones se conserva

- **WHEN** se han activado varias versiones sucesivas para `(materia, cohorte)`
- **THEN** todas las versiones previas permanecen consultables (no borradas) y exactamente una tiene `activa = true`

### Requirement: Entrada de padrón sin cuenta de usuario

El sistema SHALL permitir que una `EntradaPadron` exista con `usuario_id = NULL` cuando el alumno aún no tiene cuenta de usuario en el sistema. La entrada SHALL conservar de forma desnormalizada `nombre`, `apellidos`, `email`, `comision` y `regional` para el histórico.

#### Scenario: Alumno sin cuenta de usuario

- **WHEN** el archivo importado contiene un alumno que no corresponde a ningún `Usuario` existente del tenant
- **THEN** el sistema crea la `EntradaPadron` con `usuario_id = NULL` y los datos desnormalizados del alumno

### Requirement: Cifrado del email del alumno

El sistema SHALL almacenar el campo `email` de `EntradaPadron` cifrado con AES-256-GCM. El cifrado y descifrado SHALL ocurrir únicamente en la capa de servicio. El email en claro NUNCA SHALL aparecer en logs, en mensajes de error ni en `__repr__`.

#### Scenario: Email cifrado en reposo

- **WHEN** se persiste una `EntradaPadron`
- **THEN** el valor almacenado en la columna `email` es ciphertext y no el email en texto plano

### Requirement: Importación de padrón desde archivo con previsualización

El sistema SHALL aceptar archivos `.xlsx` y `.csv` para importar el padrón. La importación SHALL ocurrir en dos pasos: (1) **vista previa** que parsea el archivo y devuelve alumnos detectados, mapeo de columnas y errores de parseo SIN persistir nada; (2) **confirmación** que crea la nueva versión activa. Requiere permiso `padron:cargar`.

#### Scenario: Vista previa no persiste datos

- **WHEN** un usuario sube un archivo a la vista previa
- **THEN** el sistema devuelve la lista de alumnos detectados y los errores de parseo, y no crea ninguna `VersionPadron` ni `EntradaPadron`

#### Scenario: Confirmación crea la versión activa

- **WHEN** un usuario confirma una carga válida para `(materia, cohorte)`
- **THEN** el sistema crea la `VersionPadron` activa y sus `EntradaPadron`, y registra el evento de auditoría `PADRON_CARGAR`

#### Scenario: Archivo con formato inválido

- **WHEN** el archivo subido no es `.xlsx` ni `.csv`, o no contiene las columnas requeridas
- **THEN** el sistema responde con un error de validación (HTTP 422) y no persiste datos

#### Scenario: Sin permiso de carga

- **WHEN** un usuario sin permiso `padron:cargar` intenta importar o confirmar un padrón
- **THEN** el sistema responde HTTP 403 (fail-closed)

### Requirement: Consulta del padrón activo

El sistema SHALL exponer la consulta de la versión activa de padrón y sus entradas para un `(materia, cohorte)`. Requiere permiso `padron:ver`.

#### Scenario: Ver el padrón activo

- **WHEN** un usuario con permiso `padron:ver` consulta el padrón de `(materia, cohorte)`
- **THEN** el sistema devuelve las entradas de la versión con `activa = true`, con el `email` descifrado en la respuesta

#### Scenario: Sin permiso de lectura

- **WHEN** un usuario sin permiso `padron:ver` consulta el padrón
- **THEN** el sistema responde HTTP 403

### Requirement: Vaciar datos de padrón con aislamiento de scope

El sistema SHALL permitir vaciar los datos de padrón de un `(materia, cohorte)` desactivando (soft-delete) sus versiones y entradas, sin afectar el padrón de otras materias ni de otras cohortes. Requiere permiso `padron:vaciar`. El scope de los datos afectados SHALL respetar RN-04: un PROFESOR solo puede vaciar su propio scope.

#### Scenario: Vaciado aislado por materia y cohorte

- **WHEN** un usuario con permiso `padron:vaciar` vacía el padrón de `(materia A, cohorte X)`
- **THEN** las versiones y entradas de `(materia A, cohorte X)` quedan soft-deleted y el padrón de `(materia B, cohorte X)` y `(materia A, cohorte Y)` permanece intacto

#### Scenario: Sin permiso de vaciado

- **WHEN** un usuario sin permiso `padron:vaciar` intenta vaciar un padrón
- **THEN** el sistema responde HTTP 403

### Requirement: Auditoría de carga de padrón

El sistema SHALL registrar un evento de auditoría con código `PADRON_CARGAR` por cada confirmación de carga de padrón. El registro SHALL atribuirse al usuario autenticado (actor desde el JWT, nunca desde la petición) e incluir `filas_afectadas` y un `detalle` con `materia_id`, `cohorte_id`, `version_id` y origen (`archivo` | `moodle`).

#### Scenario: Auditoría emitida al confirmar carga

- **WHEN** un usuario confirma una carga de padrón
- **THEN** se crea un `AuditLog` con `accion = "PADRON_CARGAR"`, `actor_id` igual al usuario del JWT y `filas_afectadas` igual a la cantidad de entradas creadas
