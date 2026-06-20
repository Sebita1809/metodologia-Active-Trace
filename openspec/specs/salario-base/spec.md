# Spec Delta — salario-base (C-18)

## ADDED Requirements

### Requirement: Grilla de salario base por rol con vigencia temporal abierta
El sistema SHALL almacenar montos de salario base por `rol` con un rango de vigencia `desde` (obligatorio) y `hasta` (nullable = vigente sin límite), aislados por tenant. Los roles con base definida son PROFESOR, TUTOR, NEXO y COORDINADOR (RN-31, RN-32).

#### Scenario: Crear una base con vigencia abierta
- **WHEN** un usuario FINANZAS con `liquidaciones:configurar-salarios` crea una base para rol PROFESOR con `monto`, `desde` y `hasta = null`
- **THEN** el sistema persiste la fila aislada por `tenant_id` y retorna HTTP 201 con el recurso creado

#### Scenario: Monto negativo es rechazado
- **WHEN** se intenta crear una base con `monto` negativo
- **THEN** el sistema retorna HTTP 422 sin persistir la fila

### Requirement: Selección de la base vigente para un mes
El sistema SHALL seleccionar, para un rol y un mes dado, la fila de salario base cuyo rango de vigencia contiene el primer día de ese mes: `desde <= ref_date AND (hasta IS NULL OR hasta >= ref_date)` (RN-31).

#### Scenario: Toma la base vigente al mes liquidado
- **WHEN** existen dos bases para PROFESOR, una con vigencia 2026-01 a 2026-03 y otra desde 2026-04 abierta, y se consulta la vigente para el mes 2026-05
- **THEN** el sistema retorna la fila con vigencia desde 2026-04

#### Scenario: No hay base vigente para el mes
- **WHEN** se consulta la base vigente de un rol para un mes anterior a la `desde` de toda fila existente
- **THEN** el sistema no retorna ninguna fila vigente

### Requirement: No solapamiento de vigencias por rol
El sistema SHALL impedir que existan dos bases vigentes para el mismo `rol` en un mismo instante, validando el no-solapamiento de rangos al crear o editar (RN-31: una sola entrada vigente por rol en un instante dado).

#### Scenario: Rango solapado para el mismo rol es rechazado
- **WHEN** existe una base PROFESOR con vigencia 2026-01 abierta y se intenta crear otra base PROFESOR con `desde` 2026-06
- **THEN** el sistema retorna HTTP 409 indicando el solapamiento de vigencias

### Requirement: ABM de salario base requiere `liquidaciones:configurar-salarios`
El sistema SHALL proteger todos los endpoints de escritura de salario base con el guard `require_permission("liquidaciones:configurar-salarios")` (rol FINANZAS), fail-closed.

#### Scenario: Usuario sin permiso no puede gestionar la grilla
- **WHEN** un usuario sin `liquidaciones:configurar-salarios` hace POST a la grilla de salario base
- **THEN** el sistema retorna HTTP 403

### Requirement: Salario base aislado por tenant y soft delete
El sistema SHALL filtrar toda consulta de salario base por `tenant_id` del JWT y eliminar las filas con soft delete (`deleted_at`).

#### Scenario: Listado retorna solo las filas del tenant
- **WHEN** un usuario FINANZAS lista la grilla de salario base
- **THEN** el sistema retorna únicamente las filas cuyo `tenant_id` coincide con el del usuario autenticado

#### Scenario: Eliminar una base la marca con deleted_at
- **WHEN** un usuario FINANZAS elimina una fila de salario base
- **THEN** el sistema setea `deleted_at` y la fila deja de aparecer en los listados normales
