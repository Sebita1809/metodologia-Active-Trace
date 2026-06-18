# Especificación — Estructura Académica

> Capacidad: `estructura-academica`
> Change: C-06
> Permiso requerido: `estructura:gestionar` (rol ADMIN)
> Multi-tenancy: row-level por `tenant_id` en todas las entidades

---

## ADDED Requirements

### Requirement: Carrera — Crear

El sistema SHALL permitir crear una carrera dentro de un tenant con codigo, nombre y estado.

#### Scenario: Crear carrera con datos válidos
- **WHEN** un usuario ADMIN envía una solicitud POST a `/api/admin/carreras` con `codigo` y `nombre` válidos
- **THEN** el sistema SHALL crear la carrera y retornar 201 con los datos completos incluyendo el UUID generado

#### Scenario: Crear carrera con codigo duplicado en el mismo tenant
- **WHEN** un usuario ADMIN envía una solicitud POST a `/api/admin/carreras` con un `codigo` que ya existe en el mismo tenant
- **THEN** el sistema SHALL retornar 409 Conflict con un mensaje de error indicando violación de unicidad

#### Scenario: Crear carrera con codigo duplicado en tenant distinto
- **WHEN** un usuario ADMIN de otro tenant envía una solicitud POST a `/api/admin/carreras` con el mismo `codigo` que existe en otro tenant
- **THEN** el sistema SHALL crear la carrera y retornar 201 sin conflictos

---

### Requirement: Carrera — Leer

El sistema SHALL permitir consultar carreras por ID y listar carreras del tenant.

#### Scenario: Obtener carrera por ID
- **WHEN** un usuario ADMIN envía una solicitud GET a `/api/admin/carreras/{id}` con un UUID válido
- **THEN** el sistema SHALL retornar 200 con los datos de la carrera

#### Scenario: Listar carreras del tenant
- **WHEN** un usuario ADMIN envía una solicitud GET a `/api/admin/carreras`
- **THEN** el sistema SHALL retornar 200 con la lista de carreras del tenant (excluyendo carreras soft-deleted)

#### Scenario: Obtener carrera de otro tenant
- **WHEN** un usuario ADMIN envía una solicitud GET a `/api/admin/carreras/{id}` con un UUID que pertenece a otro tenant
- **THEN** el sistema SHALL retornar 404 Not Found

---

### Requirement: Carrera — Actualizar

El sistema SHALL permitir actualizar nombre y estado de una carrera existente.

#### Scenario: Actualizar nombre de carrera
- **WHEN** un usuario ADMIN envía una solicitud PATCH a `/api/admin/carreras/{id}` con un nuevo `nombre`
- **THEN** el sistema SHALL actualizar el campo y retornar 200 con los datos actualizados

#### Scenario: Desactivar carrera sin cohortes activas
- **WHEN** un usuario ADMIN envía una solicitud PATCH a `/api/admin/carreras/{id}` con `estado: Inactiva` y la carrera no tiene cohortes activas
- **THEN** el sistema SHALL cambiar el estado a Inactiva y retornar 200

#### Scenario: Desactivar carrera con cohortes activas
- **WHEN** un usuario ADMIN envía una solicitud PATCH a `/api/admin/carreras/{id}` con `estado: Inactiva` y la carrera tiene al menos una cohorte activa
- **THEN** el sistema SHALL retornar 409 Conflict indicando que no se puede desactivar una carrera con cohortes activas

#### Scenario: Reactivar carrera
- **WHEN** un usuario ADMIN envía una solicitud PATCH a `/api/admin/carreras/{id}` con `estado: Activa` sobre una carrera inactiva
- **THEN** el sistema SHALL cambiar el estado a Activa y retornar 200

---

### Requirement: Carrera — Eliminar (soft delete)

El sistema SHALL permitir eliminar lógicamente una carrera sin cohortes activas.

#### Scenario: Eliminar carrera sin cohortes activas
- **WHEN** un usuario ADMIN envía una solicitud DELETE a `/api/admin/carreras/{id}` y la carrera no tiene cohortes activas
- **THEN** el sistema SHALL marcar `deleted_at` con la fecha actual y retornar 204 No Content

#### Scenario: Eliminar carrera con cohortes activas
- **WHEN** un usuario ADMIN envía una solicitud DELETE a `/api/admin/carreras/{id}` y la carrera tiene cohortes activas
- **THEN** el sistema SHALL retornar 409 Conflict indicando que no se puede eliminar

---

### Requirement: Cohorte — Crear

El sistema SHALL permitir crear una cohorte asociada a una carrera activa.

#### Scenario: Crear cohorte para carrera activa
- **WHEN** un usuario ADMIN envía una solicitud POST a `/api/admin/cohortes` con `carrera_id`, `nombre`, `anio` y `vig_desde` válidos para una carrera activa
- **THEN** el sistema SHALL crear la cohorte y retornar 201

#### Scenario: Crear cohorte para carrera inactiva
- **WHEN** un usuario ADMIN envía una solicitud POST a `/api/admin/cohortes` con `carrera_id` de una carrera inactiva
- **THEN** el sistema SHALL retornar 422 Unprocessable Entity indicando que la carrera no está activa

#### Scenario: Crear cohorte con nombre duplicado en misma carrera y tenant
- **WHEN** un usuario ADMIN envía una solicitud POST a `/api/admin/cohortes` con un `nombre` que ya existe para la misma `carrera_id` en el mismo tenant
- **THEN** el sistema SHALL retornar 409 Conflict

#### Scenario: Crear cohorte con vig_hasta en el pasado
- **WHEN** un usuario ADMIN envía una solicitud POST a `/api/admin/cohortes` con `vig_hasta` anterior a la fecha actual
- **THEN** el sistema SHALL crear la cohorte y retornar 201 (es un dato histórico válido)

---

### Requirement: Cohorte — Leer

El sistema SHALL permitir consultar cohortes por ID y listar cohortes del tenant.

#### Scenario: Obtener cohorte por ID
- **WHEN** un usuario ADMIN envía una solicitud GET a `/api/admin/cohortes/{id}` con un UUID válido
- **THEN** el sistema SHALL retornar 200 con los datos de la cohorte

#### Scenario: Listar cohortes filtradas por carrera
- **WHEN** un usuario ADMIN envía una solicitud GET a `/api/admin/cohortes?carrera_id={carrera_id}`
- **THEN** el sistema SHALL retornar 200 con la lista de cohortes de esa carrera scoped al tenant

#### Scenario: Obtener cohorte de otro tenant
- **WHEN** un usuario ADMIN envía una solicitud GET a `/api/admin/cohortes/{id}` con un UUID de otro tenant
- **THEN** el sistema SHALL retornar 404 Not Found

---

### Requirement: Cohorte — Actualizar

El sistema SHALL permitir actualizar una cohorte existente respetando las reglas de carrera activa.

#### Scenario: Actualizar nombre de cohorte
- **WHEN** un usuario ADMIN envía una solicitud PATCH a `/api/admin/cohortes/{id}` con un nuevo `nombre`
- **THEN** el sistema SHALL actualizar el campo y retornar 200

#### Scenario: Actualizar cohorte cambiando a carrera inactiva
- **WHEN** un usuario ADMIN envía una solicitud PATCH a `/api/admin/cohortes/{id}` con un `carrera_id` de una carrera inactiva
- **THEN** el sistema SHALL retornar 422 indicando que la carrera destino no está activa

---

### Requirement: Cohorte — Eliminar (soft delete)

El sistema SHALL permitir eliminar lógicamente una cohorte.

#### Scenario: Eliminar cohorte
- **WHEN** un usuario ADMIN envía una solicitud DELETE a `/api/admin/cohortes/{id}`
- **THEN** el sistema SHALL marcar `deleted_at` y retornar 204 No Content

---

### Requirement: Materia — Crear

El sistema SHALL permitir crear una materia dentro de un tenant con codigo y nombre.

#### Scenario: Crear materia con datos válidos
- **WHEN** un usuario ADMIN envía una solicitud POST a `/api/admin/materias` con `codigo` y `nombre` válidos
- **THEN** el sistema SHALL crear la materia y retornar 201

#### Scenario: Crear materia con codigo duplicado en el mismo tenant
- **WHEN** un usuario ADMIN envía una solicitud POST a `/api/admin/materias` con un `codigo` que ya existe en el mismo tenant
- **THEN** el sistema SHALL retornar 409 Conflict

#### Scenario: Crear materia con codigo duplicado en tenant distinto
- **WHEN** un usuario ADMIN de otro tenant envía una solicitud POST a `/api/admin/materias` con el mismo `codigo` que existe en otro tenant
- **THEN** el sistema SHALL crear la materia y retornar 201 sin conflictos

---

### Requirement: Materia — Leer

El sistema SHALL permitir consultar materias por ID y listar materias del tenant.

#### Scenario: Obtener materia por ID
- **WHEN** un usuario ADMIN envía una solicitud GET a `/api/admin/materias/{id}` con un UUID válido
- **THEN** el sistema SHALL retornar 200 con los datos de la materia

#### Scenario: Listar materias del tenant
- **WHEN** un usuario ADMIN envía una solicitud GET a `/api/admin/materias`
- **THEN** el sistema SHALL retornar 200 con la lista de materias del tenant

#### Scenario: Obtener materia de otro tenant
- **WHEN** un usuario ADMIN envía una solicitud GET a `/api/admin/materias/{id}` con un UUID de otro tenant
- **THEN** el sistema SHALL retornar 404 Not Found

---

### Requirement: Materia — Actualizar

El sistema SHALL permitir actualizar nombre y estado de una materia.

#### Scenario: Actualizar nombre de materia
- **WHEN** un usuario ADMIN envía una solicitud PATCH a `/api/admin/materias/{id}` con un nuevo `nombre`
- **THEN** el sistema SHALL actualizar el campo y retornar 200

#### Scenario: Desactivar materia
- **WHEN** un usuario ADMIN envía una solicitud PATCH a `/api/admin/materias/{id}` con `estado: Inactiva`
- **THEN** el sistema SHALL cambiar el estado y retornar 200

---

### Requirement: Materia — Eliminar (soft delete)

El sistema SHALL permitir eliminar lógicamente una materia.

#### Scenario: Eliminar materia
- **WHEN** un usuario ADMIN envía una solicitud DELETE a `/api/admin/materias/{id}`
- **THEN** el sistema SHALL marcar `deleted_at` y retornar 204 No Content

---

### Requirement: Multi-tenancy — Aislamiento entre tenants

Todas las operaciones SHALL respetar el tenant del usuario autenticado.

#### Scenario: Usuario de tenant A no ve datos de tenant B
- **WHEN** un usuario del tenant A consulta carreras, cohortes o materias
- **THEN** el sistema SHALL retornar exclusivamente los registros con `tenant_id = tenant_A`

#### Scenario: Usuario de tenant B no modifica datos de tenant A
- **WHEN** un usuario del tenant B envía una solicitud de modificación sobre un registro del tenant A
- **THEN** el sistema SHALL retornar 404 (el registro no existe en el scope del tenant actual)

---

### Requirement: RBAC — Protección de endpoints

Todos los endpoints de estructura académica SHALL requerir el permiso `estructura:gestionar`.

#### Scenario: Usuario sin permiso recibe 403
- **WHEN** un usuario autenticado sin el permiso `estructura:gestionar` envía cualquier solicitud a `/api/admin/carreras`, `/api/admin/cohortes` o `/api/admin/materias`
- **THEN** el sistema SHALL retornar 403 Forbidden

---

### Requirement: Validación de schemas

Todos los DTOs SHALL rechazar campos no declarados.

#### Scenario: Envío con campos extra es rechazado
- **WHEN** un usuario ADMIN envía una solicitud con campos no definidos en el schema Pydantic
- **THEN** el sistema SHALL retornar 422 Unprocessable Entity

---

### Requirement: Soft delete — Auditoría

Ninguna entidad SHALL ser eliminada físicamente de la base de datos.

#### Scenario: Registro eliminado no aparece en listados
- **WHEN** un usuario ADMIN lista carreras, cohortes o materias después de eliminar un registro
- **THEN** el sistema SHALL excluir los registros con `deleted_at` no nulo

#### Scenario: Registro eliminado es accesible por ID directo
- **WHEN** un usuario ADMIN consulta por ID un registro soft-deleted
- **THEN** el sistema SHALL retornar 404 Not Found
