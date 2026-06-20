## Why

El backend de equipos docentes (C-08), avisos (C-15), tareas internas (C-16), encuentros (C-13), coloquios (C-14) y aprobación de comunicaciones (C-12) está completamente implementado, pero no existe interfaz para que el COORDINADOR o ADMIN los opere. Sin C-23, todo el ciclo de coordinación —setup de cuatrimestre, publicación de avisos, workflow de tareas, gestión de encuentros y coloquios— requiere acceso directo a la API.

## What Changes

- Nueva feature `coordinacion` con pages y componentes para COORDINADOR y ADMIN
- Vista de **equipos docentes**: mis-equipos, asignaciones, alta masiva, clonado entre períodos, modificación de vigencia y exportación (F4.2–F4.7, FL-03)
- **Avisos**: ABM completo con scope, severidad, vigencia y acknowledgment de lectura (F3.5, FL-09)
- **Tareas internas**: workflow asignación → progreso → cierre con comentarios (F8.1–F8.3, FL-05)
- **Monitor general**: vista transversal de todos los alumnos del tenant con filtros amplios (F2.7)
- **Encuentros admin**: vista supervisora de todos los encuentros del tenant + registro de guardias (F6.5, F6.6)
- **Coloquios**: panel de métricas, convocatorias, importación de padrón, agenda de reservas y registro académico (F7.1–F7.5, FL-07)
- **Cola de aprobación** de comunicaciones masivas desde el panel COORDINADOR (F3.3, FL-04 parte B)
- Delta en `monitor-seguimiento-ui`: filtro de rango de fechas disponible solo para COORDINADOR/ADMIN (F2.9)
- Rutas con `RequireRole` y entradas de nav para los nuevos módulos

## Capabilities

### New Capabilities

- `equipos-coordinacion-ui`: gestión completa de equipos docentes para COORDINADOR/ADMIN — vista de asignaciones, alta individual y masiva, clonado entre períodos, cambio de vigencia, exportación CSV
- `avisos-coordinacion-ui`: ABM de avisos del sistema — scope (global/materia/cohorte), severidad, roles destinatarios, ventana de visibilidad, require_ack, panel de confirmaciones
- `tareas-coordinacion-ui`: workflow de tareas internas — vista del docente (mis tareas), vista coordinador (global con filtros), cambio de estado, comentarios, historial
- `encuentros-admin-ui`: vista transversal de encuentros del tenant + registro y consulta de guardias de tutores (F6.5, F6.6)
- `coloquios-ui`: panel de coloquios para COORDINADOR/ADMIN — métricas, convocatorias (alta, agenda, importación de alumnos), resultados académicos consolidados (F7.1–F7.5)
- `monitor-general-ui`: monitor global de actividad de todos los alumnos del tenant con filtros por materia, regional, comisión, búsqueda y estado de actividad (F2.7)

### Modified Capabilities

- `monitor-seguimiento-ui`: agregar filtro de rango de fechas visible solo para COORDINADOR/ADMIN (F2.9 extiende F2.8)
- `comunicacion-atrasados-ui`: agregar vista de cola de aprobación de envíos masivos (aprobar/cancelar por lote o individual) para rol con permiso `comunicacion:aprobar` (F3.3, FL-04 parte B)

## Impact

- **Frontend**: nueva feature `coordinacion/` con ~7 sub-módulos; ajustes menores en `gestion-comision/` (aprobación de comunicaciones) y `monitor-seguimiento` (filtro de fechas)
- **Backend**: solo lectura/consumo — todos los endpoints necesarios ya existen en C-08, C-12, C-13, C-14, C-15, C-16
- **Router**: nuevas rutas `/coordinacion/*` protegidas con `RequireRole(['COORDINADOR', 'ADMIN'])`; `/tareas` accesible también a PROFESOR y TUTOR (sus propias tareas)
- **Nav**: entradas de menú nuevas condicionales al rol del usuario autenticado
