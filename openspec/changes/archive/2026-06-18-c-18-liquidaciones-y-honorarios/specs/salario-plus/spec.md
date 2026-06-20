# Spec Delta — salario-plus (C-18)

## ADDED Requirements

### Requirement: Grilla de plus por clave × rol con vigencia temporal abierta
El sistema SHALL almacenar montos de plus identificados por una `clave` (string libre configurable por tenant) cruzada con un `rol`, con vigencia `desde` (obligatorio) y `hasta` (nullable), aislados por tenant (RN-31, RN-33, PA-22).

#### Scenario: Crear un plus con clave libre
- **WHEN** un usuario FINANZAS con `liquidaciones:configurar-salarios` crea un plus con `clave = "PROG"`, `rol = PROFESOR`, `monto`, `desde` y `hasta = null`
- **THEN** el sistema persiste la fila aislada por `tenant_id` y retorna HTTP 201

#### Scenario: La clave es un string libre, no un enum global
- **WHEN** un tenant crea un plus con una clave que no existe en otros tenants
- **THEN** el sistema acepta la clave sin validarla contra un catálogo global

### Requirement: Selección del plus vigente para un mes
El sistema SHALL seleccionar, para una `clave`, un `rol` y un mes dado, la fila de plus cuyo rango de vigencia contiene el primer día de ese mes (RN-31).

#### Scenario: Toma el plus vigente al mes liquidado
- **WHEN** existen dos plus para `(PROG, PROFESOR)`, uno con vigencia hasta 2026-03 y otro desde 2026-04 abierto, y se consulta el vigente para el mes 2026-06
- **THEN** el sistema retorna la fila con vigencia desde 2026-04

#### Scenario: No hay plus vigente para la clave y rol
- **WHEN** se consulta el plus vigente de `(clave, rol)` para un mes sin fila vigente
- **THEN** el sistema no retorna ninguna fila vigente

### Requirement: No solapamiento de vigencias por clave y rol
El sistema SHALL impedir dos plus vigentes para el mismo `(clave, rol)` en un mismo instante, validando el no-solapamiento al crear o editar.

#### Scenario: Rango solapado para la misma clave y rol es rechazado
- **WHEN** existe un plus `(PROG, PROFESOR)` con vigencia abierta y se intenta crear otro `(PROG, PROFESOR)` con vigencia solapada
- **THEN** el sistema retorna HTTP 409 indicando el solapamiento

### Requirement: ABM de salario plus requiere `liquidaciones:configurar-salarios`
El sistema SHALL proteger todos los endpoints de escritura de salario plus con el guard `require_permission("liquidaciones:configurar-salarios")` (rol FINANZAS), fail-closed.

#### Scenario: Usuario sin permiso no puede gestionar la grilla de plus
- **WHEN** un usuario sin `liquidaciones:configurar-salarios` hace POST a la grilla de plus
- **THEN** el sistema retorna HTTP 403

### Requirement: Salario plus aislado por tenant y soft delete
El sistema SHALL filtrar toda consulta de salario plus por `tenant_id` del JWT y eliminar las filas con soft delete.

#### Scenario: Listado retorna solo las filas del tenant
- **WHEN** un usuario FINANZAS lista la grilla de plus
- **THEN** el sistema retorna únicamente las filas del tenant del usuario autenticado
