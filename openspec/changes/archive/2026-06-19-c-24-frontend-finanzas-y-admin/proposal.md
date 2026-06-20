## Why

C-24 es el último change de la plataforma. El backend de liquidaciones (C-18), auditoría/métricas (C-19), estructura académica (C-06), usuarios (C-07), programas y fechas académicas (C-17) está completamente operativo pero sin UI. Sin C-24 los roles FINANZAS y ADMIN no pueden operar la plataforma: no hay forma de calcular ni cerrar liquidaciones, gestionar la grilla salarial, administrar la estructura académica, gestionar usuarios del tenant ni consultar el log de auditoría.

## What Changes

- Nueva feature `finanzas/` para rol FINANZAS: vista segmentada de liquidaciones (general / NEXO / factura) con KPIs, cierre de liquidación, historial, grilla salarial (salario base + plus), gestión de facturas de docentes (F10.1–F10.6, FL-08)
- Nueva feature `admin/` para rol ADMIN: estructura académica (ABM carreras, cohortes, materias), gestión de usuarios del tenant, programas de materia, fechas de evaluaciones (F5.1–F5.4, F4.1, FL-12)
- Nueva feature `auditoria/` para COORDINADOR/ADMIN: panel de interacciones con gráfico de actividad, estado de comunicaciones, métricas por docente y log de últimas acciones; log completo de auditoría solo para ADMIN (F9.1, F9.2, FL-11)
- Rutas con `RequireRole` y entradas de nav condicionales por rol

## Capabilities

### New Capabilities

- `liquidaciones-ui`: vista segmentada de liquidaciones del período (3 segmentos: general, NEXO, factura) + KPIs "Total sin factura" / "Total con factura", cerrar liquidación con confirmación, historial de períodos cerrados, exportación CSV (F10.1, F10.2, F10.3, F10.6, FL-08)
- `grilla-salarial-ui`: ABM de salario base por rol con vigencia y ABM de plus (clave, rol, descripción, vigencia) — permiso `liquidaciones:configurar-salarios` (F10.4)
- `facturas-ui`: ABM de comprobantes de docentes que facturan — filtros por docente/estado/fecha, cambio de estado pendiente↔abonada, archivo adjunto (F10.5)
- `estructura-academica-admin-ui`: ABM de carreras (código + nombre + estado), ABM de cohortes (nombre, año inicio, vigencia, estado), ABM de materias — solo ADMIN (F5.1, F5.2)
- `usuarios-admin-ui`: ABM de usuarios del tenant con rol docente — alta, edición, activación/desactivación, datos bancarios (CBU/alias cifrados), regional, modalidad de cobro (F4.1)
- `programas-fechas-admin-ui`: gestión de programas de materia (subida de documento por carrera × cohorte) y gestión de fechas de evaluaciones (parcial/TP/coloquio por materia, cohorte e instancia) con vista tabular y calendario — ADMIN y COORDINADOR (F5.3, F5.4)
- `auditoria-ui`: panel de interacciones (gráfico de acciones por día, estado de comunicaciones por docente, métricas de uso, log de últimas acciones con filtros) + log completo solo para ADMIN (F9.1, F9.2, FL-11)

### Modified Capabilities

_(ninguna — todas son capacidades nuevas)_

## Impact

- **Frontend**: 3 features nuevas (`finanzas/`, `admin/`, `auditoria/`) con ~7 sub-módulos
- **Backend**: solo consumo — todos los routers existen: `liquidaciones.py`, `facturas.py`, `carreras.py`, `cohortes.py`, `usuarios.py`, `programas.py`, `fechas_academicas.py`, `auditoria.py`
- **Router**: rutas `/finanzas/*` (`RequireRole(['FINANZAS', 'ADMIN'])`), `/admin/*` (`RequireRole(['ADMIN'])`), `/auditoria` (`RequireRole(['COORDINADOR', 'ADMIN'])`)
- **Nav**: secciones "Finanzas", "Administración" y "Auditoría" condicionales al rol
- **Seguridad**: datos bancarios (CBU/alias) vienen cifrados del backend — el frontend los muestra tal como los devuelve la API, nunca los envía en texto en el query string
