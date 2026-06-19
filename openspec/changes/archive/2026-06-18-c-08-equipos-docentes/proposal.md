## Why

C-07 habilitó el modelo `Asignacion` con CRUD individual, pero la operatoria real del COORDINADOR requiere operaciones de alto nivel: armar equipos completos en bloque, clonar equipos entre períodos lectivos, modificar vigencias masivamente y exportar la composición del equipo. Sin C-08, estas operaciones deben hacerse una asignación a la vez, lo que hace impracticable la gestión de equipos docentes en instituciones con decenas de materias y cientos de docentes.

Este cambio es el que transforma `Asignacion` de un registro de membresía individual en un **módulo de gestión de equipos docentes** operativo para el COORDINADOR.

## What Changes

- Nuevo router `/api/equipos/*` con operaciones de alto nivel sobre asignaciones
- Endpoint `GET /api/equipos/mis-equipos` para que un docente vea sus materias/comisiones asignadas (F4.2)
- Endpoint `GET /api/equipos/materias/{materia_id}` para que COORDINADOR/ADMIN consulte el equipo completo de una materia (F4.3)
- Endpoint `POST /api/equipos/asignacion-masiva` para asignar N docentes en bloque a materia × carrera × cohorte × rol con vigencia (F4.4)
- Endpoint `POST /api/equipos/clonar` para duplicar asignaciones entre cohortes (F4.5, RN-12)
- Endpoint `PATCH /api/equipos/vigencia` para modificar desde/hasta de todo un equipo en una operación (F4.6)
- Endpoint `GET /api/equipos/{materia_id}/exportar` para descargar equipo docente como archivo (F4.7)
- Servicio `EquipoDocenteService` con lógica de negocio: validación de asignación masiva, clonado con ajuste de fechas, modificación de vigencia en bloque, generación de exportación
- Guard de permisos `equipos:asignar` para operaciones de gestión, y lectura propia para `mis-equipos` (autenticación vía `get_current_user`)
- Eventos de auditoría con acción `ASIGNACION_MODIFICAR` para todas las operaciones de escritura
- Validación en soft-delete de materia/carrera/cohorte: rechazar desactivación si hay asignaciones activas (pendiente delegado de C-07)
- Tests de integración para todas las operaciones

## Capabilities

### New Capabilities

- `equipos-docentes`: Gestión de equipos docentes — mis-equipos, asignación masiva, clonado entre períodos, modificación de vigencia en bloque, exportación, y validación de desactivación de entidades académicas con asignaciones activas

### Modified Capabilities

<!-- Sin cambios en specs existentes — role-assignment (CRUD individual de Asignacion) permanece intacto. C-08 agrega operaciones de dominio de alto nivel sobre el mismo modelo. -->

## Impact

- **Backend**: nuevo `EquipoDocenteService`, nuevo router `/api/equipos/*`, extensión de `AsignacionRepository` con queries de agrupación y batch
- **No requiere migración de base de datos** — opera sobre `Asignacion` existente
- **No requiere nuevos modelos** — toda la lógica opera sobre `Asignacion`, `Usuario`, `Materia`, `Carrera`, `Cohorte`
- **Permisos**: endpoint propio (F4.2) se protege con `get_current_user`; todos los demás con guard `equipos:asignar`
- **Auditoría**: eventos `ASIGNACION_MODIFICAR` en cada operación de escritura
- **Dependencia con C-06**: validación de soft-delete de materia/carrera/cohorte al tener asignaciones activas
