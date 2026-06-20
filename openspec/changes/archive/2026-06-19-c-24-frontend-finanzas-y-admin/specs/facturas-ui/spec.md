## ADDED Requirements

### Requirement: Listado de facturas con filtros

La feature SHALL presentar los comprobantes de docentes que facturan con filtros por docente, estado (pendiente/abonada), rango de fechas y búsqueda libre, consumiendo `GET /api/v1/facturas`. Implementa F10.5 y RN-35.

#### Scenario: Listar facturas filtradas por estado
- **WHEN** FINANZAS filtra por estado "pendiente"
- **THEN** la UI muestra solo los comprobantes en estado pendiente con columnas: fecha_carga, docente, período, detalle, archivo, tamaño, estado, datos_pago

#### Scenario: Sin facturas para los filtros
- **WHEN** no hay comprobantes que coincidan con los filtros
- **THEN** la UI muestra el estado vacío "sin comprobantes para los criterios seleccionados"

### Requirement: Cambiar estado de factura

La feature SHALL permitir cambiar el estado de un comprobante entre "pendiente" y "abonada" enviando `PUT /api/v1/facturas/{id}`. Implementa F10.5.

#### Scenario: Marcar factura como abonada
- **WHEN** FINANZAS marca un comprobante como "abonada"
- **THEN** la UI actualiza el estado en la tabla sin recargar el listado

#### Scenario: Revertir a pendiente
- **WHEN** FINANZAS revierte un comprobante de "abonada" a "pendiente"
- **THEN** la UI actualiza el estado correctamente

### Requirement: Cargar nuevo comprobante

La feature SHALL permitir registrar un nuevo comprobante con: docente, período facturado, detalle, archivo adjunto y datos de pago, enviando `POST /api/v1/facturas` como multipart/form-data. Implementa F10.5.

#### Scenario: Cargar comprobante con archivo
- **WHEN** FINANZAS sube un PDF como comprobante de un docente para el período marzo 2025
- **THEN** el comprobante aparece en el listado con estado "pendiente" y el tamaño del archivo visible

#### Scenario: Validar campos requeridos
- **WHEN** el usuario intenta guardar sin seleccionar docente
- **THEN** Zod bloquea el envío con error en el campo docente
