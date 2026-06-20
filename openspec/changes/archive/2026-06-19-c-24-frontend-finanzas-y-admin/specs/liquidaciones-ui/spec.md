## ADDED Requirements

### Requirement: Vista segmentada de liquidaciones del período

La feature SHALL presentar la liquidación del período seleccionado en tres segmentos diferenciados: (1) Detalle general (PROFESOR, TUTOR, COORDINADOR que no facturan), (2) NEXO (calculado separado pero sumado al total general), (3) Docentes que facturan (informativos, excluidos del total). Consumir `GET /api/v1/liquidaciones` con filtros por cohorte, mes y opcionalmente docente. Implementa F10.1, F10.6 y FL-08 pasos 1–3.

#### Scenario: Ver liquidación con los tres segmentos
- **WHEN** FINANZAS selecciona cohorte y mes
- **THEN** la UI muestra las tres secciones con sus filas de docente/rol/base/plus/total y los KPIs "Total sin factura" y "Total con factura" en la cabecera

#### Scenario: Período sin datos
- **WHEN** no existen liquidaciones para el período seleccionado
- **THEN** la UI muestra el estado vacío "sin datos para el período seleccionado"

### Requirement: KPIs de cabecera de liquidación

La feature SHALL mostrar en la cabecera de la vista de liquidación los KPIs "Total sin factura" (segmentos general + NEXO) y "Total con factura" (suma incluyendo los docentes que facturan). Implementa F10.6.

#### Scenario: KPIs actualizados al cambiar período
- **WHEN** FINANZAS cambia el mes o la cohorte
- **THEN** los KPIs de cabecera se actualizan con los totales del nuevo período

### Requirement: Exportar liquidación

La feature SHALL permitir descargar la planilla del período como CSV consumiendo `GET /api/v1/liquidaciones/exportar` (verificar path exacto en el router). Implementa FL-08 paso 4.

#### Scenario: Exportar planilla
- **WHEN** FINANZAS pulsa "Exportar"
- **THEN** el navegador descarga la planilla del período con todos los segmentos

### Requirement: Cerrar liquidación con doble confirmación

La feature SHALL requerir doble confirmación antes de enviar `POST /api/v1/liquidaciones/{id}/cerrar`. El diálogo SHALL mostrar el período y el total a cerrar. Una vez cerrada, la fila SHALL mostrarse como inmutable con badge "Cerrada". Implementa F10.2 y RN-22.

#### Scenario: Confirmar cierre de liquidación
- **WHEN** FINANZAS confirma el cierre en el diálogo mostrando el período y el total
- **THEN** la UI envía el cierre y marca la liquidación como inmutable con badge "Cerrada"

#### Scenario: Cancelar cierre
- **WHEN** FINANZAS descarta el diálogo de confirmación
- **THEN** la liquidación permanece abierta sin ningún cambio

#### Scenario: Liquidación ya cerrada
- **WHEN** la liquidación del período ya está cerrada
- **THEN** el botón "Cerrar" está deshabilitado y se muestra el badge "Cerrada"

### Requirement: Historial de liquidaciones cerradas

La feature SHALL presentar el historial de liquidaciones de períodos anteriores consumiendo `GET /api/v1/liquidaciones/historial`. Implementa F10.3.

#### Scenario: Ver historial
- **WHEN** FINANZAS accede a la sección de historial
- **THEN** la UI muestra la lista de períodos cerrados con fecha de cierre y total liquidado

#### Scenario: Sin historial
- **WHEN** no hay liquidaciones cerradas previas
- **THEN** la UI muestra el estado vacío "sin liquidaciones cerradas"
