# Spec Delta — liquidacion (C-18)

## ADDED Requirements

### Requirement: Cálculo de liquidación Base + Plus por período
El sistema SHALL calcular, para cada docente con asignaciones activas en una cohorte y mes, una liquidación cuyo `total_monto = base_monto + plus_monto`, donde `base_monto` es el salario base vigente del rol para ese mes y `plus_monto = Σ(plus_vigente(clave, rol, mes) × N_comisiones_de_esa_clave)` (RN-21, RN-34).

#### Scenario: Total es base más suma de plus
- **WHEN** se calcula la liquidación de un docente PROFESOR con base vigente 1000 y un plus `(PROG, PROFESOR)` vigente de 200 sobre 1 comisión de clave PROG
- **THEN** el sistema persiste `base_monto = 1000`, `plus_monto = 200` y `total_monto = 1200`

#### Scenario: Materia sin clave_plus no aporta plus
- **WHEN** un docente tiene una comisión de una materia con `clave_plus` nulo
- **THEN** esa comisión no incrementa `plus_monto` y el `total_monto` es solo la base

### Requirement: El plus acumula N veces por N comisiones de la misma clave
El sistema SHALL acumular el plus de una clave tantas veces como comisiones activas de materias con esa clave tenga el docente en el período, sin tope (RN-33).

#### Scenario: Tres comisiones de la misma clave acumulan tres veces
- **WHEN** un docente tiene 3 comisiones activas de materias con `clave_plus = "PROG"` y el plus vigente `(PROG, rol)` es 200
- **THEN** el `plus_monto` aportado por la clave PROG es 600

#### Scenario: Comisiones de claves distintas suman cada plus por separado
- **WHEN** un docente tiene 2 comisiones de clave "PROG" (plus 200) y 1 comisión de clave "BD" (plus 150)
- **THEN** el `plus_monto` es `2×200 + 1×150 = 550`

### Requirement: Selección de valores vigentes al mes liquidado
El sistema SHALL tomar, para el cálculo, los valores de base y plus vigentes al primer día del mes liquidado (RN-31).

#### Scenario: Cambio de grilla a mitad de año usa la vigente al mes
- **WHEN** la base PROFESOR cambia de 1000 (hasta 2026-03) a 1200 (desde 2026-04) y se liquida el mes 2026-05
- **THEN** la liquidación usa `base_monto = 1200`

### Requirement: Liquidación se opera por (cohorte, mes)
El sistema SHALL usar la dupla `(cohorte, periodo_mes, periodo_anio)` como unidad de liquidación; distintas cohortes tienen liquidaciones independientes (RN-37). El par `(tenant_id, usuario_id, cohorte_id, periodo_anio, periodo_mes)` SHALL ser único entre filas vivas.

#### Scenario: Cohortes distintas liquidan independientemente
- **WHEN** un docente tiene asignaciones en dos cohortes para el mismo mes
- **THEN** el sistema genera una liquidación por cada cohorte, independientes entre sí

#### Scenario: Recalcular el mismo período no duplica filas vivas
- **WHEN** se recalcula un período abierto ya calculado para un docente y cohorte
- **THEN** el sistema no crea una segunda fila viva para la misma combinación

### Requirement: Tratamiento diferenciado del rol NEXO
El sistema SHALL marcar `es_nexo = true` cuando la liquidación corresponde al rol NEXO. Los importes NEXO se presentan en una sección diferenciada pero se incluyen en el total general (RN-36).

#### Scenario: NEXO suma al total general
- **WHEN** se calcula el período con liquidaciones de roles generales y de rol NEXO
- **THEN** las liquidaciones NEXO tienen `es_nexo = true` y su total se incluye en `total_sin_factura`

### Requirement: Docentes facturantes excluidos de la liquidación general
El sistema SHALL marcar `excluido_por_factura = true` para docentes con `facturador = true` y NO incluir su total en la liquidación general; su pago se gestiona por el módulo de facturas (RN-35).

#### Scenario: Facturante no suma al total de liquidación
- **WHEN** se calcula el período incluyendo un docente facturante
- **THEN** su liquidación tiene `excluido_por_factura = true` y su monto no se suma al total de liquidación general

### Requirement: Cierre inmutable de la liquidación
El sistema SHALL permitir cerrar las liquidaciones de un período `(cohorte, mes)`, dejándolas inmutables: una vez `estado = 'Cerrada'`, ninguna escritura (editar, recalcular, eliminar) es admisible (RN-22). El cierre setea `cerrada_at`.

#### Scenario: Cerrar inmoviliza el período
- **WHEN** un usuario FINANZAS con `liquidaciones:cerrar` cierra el período de una cohorte
- **THEN** todas las liquidaciones de ese período quedan con `estado = 'Cerrada'` y `cerrada_at` seteado

#### Scenario: Modificar una liquidación cerrada es rechazado
- **WHEN** se intenta editar o recalcular una liquidación con `estado = 'Cerrada'`
- **THEN** el sistema retorna HTTP 409 sin modificar la fila

### Requirement: El cierre emite evento de auditoría LIQUIDACION_CERRAR
El sistema SHALL registrar un evento de auditoría con código `LIQUIDACION_CERRAR` al cerrar un período, atribuido al actor de la sesión (JWT), con `filas_afectadas` igual a la cantidad de liquidaciones cerradas (RN-23).

#### Scenario: Cierre genera registro de auditoría
- **WHEN** un usuario FINANZAS cierra un período con N liquidaciones
- **THEN** el sistema persiste un `AuditLog` con `accion = "LIQUIDACION_CERRAR"`, `actor_id` del JWT y `filas_afectadas = N`

### Requirement: Vista del período con segmentación y KPIs
El sistema SHALL exponer la vista del período en tres segmentos —general (PROFESOR/TUTOR/COORDINADOR no facturantes), NEXO y facturantes— con KPIs de cabecera `total_sin_factura` y `total_con_factura` (F10.6, RN-36, RN-38).

#### Scenario: La vista distingue universo con y sin factura
- **WHEN** un usuario FINANZAS consulta la vista de un período con docentes generales, NEXO y facturantes
- **THEN** el sistema retorna los tres segmentos y los KPIs `total_sin_factura` (general + NEXO) y `total_con_factura` por separado

### Requirement: Historial y aislamiento por tenant
El sistema SHALL exponer el historial de liquidaciones cerradas para consulta y auditoría, filtrado por `tenant_id` del JWT, protegido por `liquidaciones:ver`.

#### Scenario: Historial retorna solo liquidaciones del tenant
- **WHEN** un usuario FINANZAS consulta el historial de liquidaciones
- **THEN** el sistema retorna únicamente las liquidaciones cerradas del tenant del usuario

### Requirement: Endpoints de liquidación protegidos por permisos FINANZAS
El sistema SHALL proteger los endpoints de liquidación fail-closed: `liquidaciones:ver` (vista, detalle, historial, exportar), `liquidaciones:calcular` (cálculo) y `liquidaciones:cerrar` (cierre).

#### Scenario: Usuario sin permiso no puede calcular
- **WHEN** un usuario sin `liquidaciones:calcular` dispara el cálculo de un período
- **THEN** el sistema retorna HTTP 403
