# Spec Delta — factura (C-18)

## ADDED Requirements

### Requirement: Registro de factura de docente facturante
El sistema SHALL registrar facturas presentadas por docentes con `facturador = true`, con `usuario_id`, período (`periodo_mes`, `periodo_anio`), `detalle` libre, `referencia_archivo`, `tamano_kb`, `monto` y `cargada_at`, aisladas por tenant (RN-40).

#### Scenario: Cargar una factura
- **WHEN** un usuario FINANZAS con `facturas:gestionar` carga una factura para un docente facturante con período, detalle y monto
- **THEN** el sistema persiste la factura con `estado = 'Pendiente'` y `cargada_at` seteado, y retorna HTTP 201

#### Scenario: Monto negativo es rechazado
- **WHEN** se intenta cargar una factura con `monto` negativo
- **THEN** el sistema retorna HTTP 422 sin persistir

### Requirement: Factura tiene exactamente dos estados
El sistema SHALL admitir solo dos estados de factura: `Pendiente` (cargada, sin pago) y `Abonada` (pago confirmado). Al pasar a `Abonada` SHALL setear `abonada_at` (RN-39).

#### Scenario: Marcar factura como abonada
- **WHEN** un usuario FINANZAS marca una factura Pendiente como Abonada
- **THEN** el sistema setea `estado = 'Abonada'` y `abonada_at` con la fecha/hora actual

#### Scenario: Estado fuera del conjunto es rechazado
- **WHEN** se intenta setear un estado distinto de `Pendiente` o `Abonada`
- **THEN** el sistema retorna HTTP 422

### Requirement: Facturas no se incluyen en la liquidación general
El sistema SHALL mantener el pago de facturantes exclusivamente por el módulo de facturas; los montos de facturas no forman parte de la liquidación general Base+Plus, pero sí del KPI `total_con_factura` (RN-35, RN-38).

#### Scenario: El total de facturas alimenta el KPI con factura
- **WHEN** existen facturas cargadas para un período de una cohorte
- **THEN** la suma de sus montos se refleja en `total_con_factura` y no en `total_sin_factura`

### Requirement: ABM de factura requiere `facturas:gestionar` y aislamiento por tenant
El sistema SHALL proteger todos los endpoints de factura con `require_permission("facturas:gestionar")` (rol FINANZAS), fail-closed, y filtrar por `tenant_id` del JWT. Las facturas usan soft delete.

#### Scenario: Usuario sin permiso no puede gestionar facturas
- **WHEN** un usuario sin `facturas:gestionar` hace POST a `/api/facturas`
- **THEN** el sistema retorna HTTP 403

#### Scenario: Listado retorna solo facturas del tenant
- **WHEN** un usuario FINANZAS lista facturas
- **THEN** el sistema retorna únicamente las facturas del tenant del usuario autenticado
