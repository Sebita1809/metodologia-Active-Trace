## 1. Tipos y estructura base

- [x] 1.1 Leer los routers de backend (C-08, C-12, C-13, C-14, C-15, C-16) para confirmar paths exactos de endpoints antes de implementar services
- [x] 1.2 Crear estructura de directorios `features/coordinacion/{equipos,avisos,tareas,encuentros,coloquios,monitor-general,comunicaciones}/`
- [x] 1.3 Definir tipos TypeScript para Asignacion, ClonarEquipoRequest, AsignacionMasivaRequest, AsignacionMasivaResult en `coordinacion/equipos/types.ts`
- [x] 1.4 Definir tipos TypeScript para Aviso, CrearAvisoRequest, AckAviso en `coordinacion/avisos/types.ts`
- [x] 1.5 Definir tipos TypeScript para Tarea, ComentarioTarea, CrearTareaRequest, CambiarEstadoTareaRequest en `coordinacion/tareas/types.ts`
- [x] 1.6 Definir tipos TypeScript para Encuentro (admin view), Guardia, RegistrarGuardiaRequest en `coordinacion/encuentros/types.ts`
- [x] 1.7 Definir tipos TypeScript para Evaluacion (convocatoria), Reserva, ResultadoColoquio, ImportarAlumnosRequest en `coordinacion/coloquios/types.ts`
- [x] 1.8 Definir tipos TypeScript para MonitorGeneral (alumno + estado actividades) en `coordinacion/monitor-general/types.ts`
- [x] 1.9 Definir tipos TypeScript para LoteComunicacion (aprobación) en `coordinacion/comunicaciones/types.ts`
- [x] 1.10 Crear schemas Zod para todos los formularios del módulo (AsignacionForm, AsignacionMasivaForm, ClonarEquipoForm, AvisoForm, TareaForm, GuardiaForm, ConvocatoriaForm)

## 2. Services (API layer)

- [x] 2.1 Crear `coordinacion/equipos/services/asignacionesService.ts` con: `getAsignaciones(filters)`, `createAsignacion(data)`, `createMasiva(data)`, `clonarEquipo(data)`, `updateVigencia(id, data)`, `exportarEquipo(filters)` → CSV blob
- [x] 2.2 Crear `coordinacion/avisos/services/avisosService.ts` con: `getAvisos()`, `createAviso(data)`, `updateAviso(id, data)`, `deleteAviso(id)`, `getAckCount(id)`
- [x] 2.3 Crear `coordinacion/tareas/services/tareasService.ts` con: `getTareas(filters)`, `createTarea(data)`, `updateTarea(id, data)`, `addComentario(id, texto)`
- [x] 2.4 Crear `coordinacion/encuentros/services/encuentrosService.ts` con: `getEncuentrosTenant(filters)` y `coordinacion/encuentros/services/guardiasService.ts` con `getGuardias(filters)`, `createGuardia(data)`, `exportarGuardias(filters)` → CSV blob
- [x] 2.5 Crear `coordinacion/coloquios/services/coloquiosService.ts` con: `getEvaluaciones()`, `createEvaluacion(data)`, `importarAlumnos(id, file)`, `getReservas(evaluacion_id)`, `getResultados(evaluacion_id)`, `getMetricas()`
- [x] 2.6 Crear `coordinacion/monitor-general/services/monitorGeneralService.ts` con: `getMonitorGeneral(filters)`, `exportarMonitor(filters)` → CSV blob
- [x] 2.7 Crear `coordinacion/comunicaciones/services/aprobacionService.ts` con: `getLotesPendientes()`, `aprobarLote(id)`, `cancelarLote(id)`

## 3. Hooks (TanStack Query)

- [x] 3.1 Crear hooks de equipos: `useAsignaciones(filters)`, `useCreateAsignacion()`, `useCreateMasiva()`, `useClonarEquipo()`, `useUpdateVigencia()`
- [x] 3.2 Crear hooks de avisos: `useAvisos()`, `useCreateAviso()`, `useUpdateAviso()`, `useDeleteAviso()`, `useAckCount(id)`
- [x] 3.3 Crear hooks de tareas: `useTareas(filters)`, `useCreateTarea()`, `useUpdateTarea()`, `useAddComentario()`
- [x] 3.4 Crear hooks de encuentros: `useEncuentrosTenant(filters)`, `useGuardias(filters)`, `useCreateGuardia()`
- [x] 3.5 Crear hooks de coloquios: `useEvaluaciones()`, `useCreateEvaluacion()`, `useImportarAlumnos()`, `useReservas(evaluacionId)`, `useResultados(evaluacionId)`, `useMetricasColoquios()`
- [x] 3.6 Crear hook `useMonitorGeneral(filters)` — verificar endpoint real antes de implementar
- [x] 3.7 Crear hooks de aprobación: `useLotesPendientes()`, `useAprobarLote()`, `useCancelarLote()`

## 4. Feature — Equipos docentes

- [x] 4.1 Crear `EquiposPage.tsx` con tabs: "Asignaciones", "Alta masiva", "Clonar equipo", "Vigencias"
- [x] 4.2 Crear `AsignacionesView.tsx`: tabla filtrable (materia, carrera, cohorte, docente, rol) + botón "Nueva asignación" + botón "Exportar CSV" (descarga blob)
- [x] 4.3 Crear `AsignacionForm.tsx` (RHF+Zod): campos materia, carrera, cohorte, rol, docente (select con búsqueda), vigencia_desde, vigencia_hasta. Validar fecha_hasta > fecha_desde
- [x] 4.4 Crear `AsignacionMasivaForm.tsx` (RHF+Zod): multi-select de docentes + campos materia × carrera × cohorte × rol + vigencia. Mostrar resultado parcial (éxitos/errores)
- [x] 4.5 Crear `ClonarEquipoForm.tsx` (RHF+Zod): selector origen (materia × carrera × cohorte) + selector destino + confirmación. Mostrar advertencia si destino tiene asignaciones existentes
- [x] 4.6 Crear `VigenciasView.tsx`: selector de equipo (materia × carrera × cohorte) + formulario de nuevas fechas + confirmación masiva

## 5. Feature — Avisos

- [x] 5.1 Crear `AvisosPage.tsx` con listado y botón "Nuevo aviso"
- [x] 5.2 Crear `AvisosTable.tsx`: tabla con columnas título, severidad, alcance, estado, fecha inicio, fecha fin, acks. Acciones inline: editar, toggle activo, eliminar
- [x] 5.3 Crear `AvisoForm.tsx` (RHF+Zod): título, cuerpo, alcance (global/materia/cohorte), contexto condicional (materia/cohorte aparecen si alcance ≠ global), roles destinatarios (multi-select), severidad, fecha_inicio, fecha_fin, orden, activo (toggle), require_ack (toggle). Validar fecha_fin > fecha_inicio y contexto condicional
- [x] 5.4 Crear `AckPanel.tsx`: panel de detalle que muestra conteo de acks vs. total de destinatarios para avisos con require_ack=true
- [x] 5.5 Crear `ConfirmDeleteDialog.tsx` reutilizable para confirmación de eliminación (usado también en otras partes del módulo)

## 6. Feature — Tareas internas

- [x] 6.1 Crear `TareasPage.tsx`: bifurcación condicional por rol — TUTOR/PROFESOR ven `MisTareasView`; COORDINADOR/ADMIN ven `TareasGlobalView` con tab "Mis tareas" + tab "Todas las tareas"
- [x] 6.2 Crear `MisTareasView.tsx`: listado de tareas asignadas al usuario con estado, materia, asignador. Selector de estado inline (dropdown Abierta/En progreso/Completada)
- [x] 6.3 Crear `TareaHiloView.tsx`: panel lateral/modal con hilo de comentarios de la tarea + formulario para agregar comentario. Validar que el comentario no esté vacío
- [x] 6.4 Crear `TareasGlobalView.tsx`: tabla de todas las tareas del tenant con filtros por docente, asignador, materia, estado, búsqueda libre. Acciones: cambiar estado, devolver con observación
- [x] 6.5 Crear `CrearTareaForm.tsx` (RHF+Zod): materia, docente asignado (select), descripción, criterio de cierre. Solo visible para COORDINADOR/ADMIN
- [x] 6.6 Implementar acción "Devolver tarea": dialog con campo observación obligatorio + `PUT /tareas/{id}` con estado "En progreso" y comentario

## 7. Feature — Encuentros admin

- [x] 7.1 Crear `EncuentrosAdminPage.tsx` con tabs "Encuentros del tenant" y "Guardias"
- [x] 7.2 Crear `EncuentrosTenantView.tsx`: tabla de todos los encuentros con columnas docente, materia, fecha, horario, estado, enlace grabación. Filtros por docente y mes
- [x] 7.3 Crear `GuardiasView.tsx`: tabla de guardias con filtros por tutor, materia, estado y rango de fechas. Botón "Registrar guardia" + botón "Exportar CSV"
- [x] 7.4 Crear `GuardiaForm.tsx` (RHF+Zod): quién cubrió (select docentes), materia, carrera/cohorte, día, horario (time), estado, comentarios. Validar horario requerido

## 8. Feature — Coloquios

- [x] 8.1 Crear `ColoquiosPage.tsx`: cabecera con 4 KPIs (`useMetricasColoquios`) + tabs "Convocatorias", "Agenda de reservas", "Registro académico"
- [x] 8.2 Crear `ConvocatoriasView.tsx`: tabla de convocatorias activas con métricas operativas. Botón "Nueva convocatoria" + botón "Importar alumnos" por fila
- [x] 8.3 Crear `ConvocatoriaForm.tsx` (RHF+Zod): materia, instancia, array de días disponibles (campo dinámico: agregar/quitar días con cupos). Validar cupos > 0
- [x] 8.4 Crear `ImportarAlumnosDialog.tsx`: upload de archivo + botón confirmar → `useImportarAlumnos`. Mostrar resultado (N alumnos cargados / errores)
- [x] 8.5 Crear `AgendaReservasView.tsx`: selector de convocatoria → `useReservas(evaluacionId)` → tabla de reservas agrupadas por día (alumno, turno, cupo)
- [x] 8.6 Crear `RegistroAcademicoView.tsx`: selector de convocatoria → `useResultados(evaluacionId)` → tabla de resultados (alumno, instancia, nota)

## 9. Feature — Monitor general

- [x] 9.1 Crear `MonitorGeneralPage.tsx` con filtros: materia (select), regional (text), comisión (text), búsqueda libre, estado de actividad (select), criterio de clasificación (select). Botón "Limpiar filtros"
- [x] 9.2 Crear `MonitorGeneralTable.tsx`: tabla paginada de alumnos con estado de actividades. Botón "Exportar CSV"
- [x] 9.3 Verificar endpoint real de `GET /calificaciones/monitor` (o equivalente) leyendo el router antes de implementar el service

## 10. Feature — Aprobación de comunicaciones

- [x] 10.1 Crear `AprobacionComunicacionesPage.tsx`: listado de lotes pendientes con columnas docente emisor, materia, destinatarios, fecha. Acciones: "Aprobar" y "Cancelar"
- [x] 10.2 Implementar acción "Cancelar lote": dialog de confirmación con cantidad de mensajes afectados → `useCancelarLote`
- [x] 10.3 Implementar acción "Aprobar lote": confirmación opcional (inline o dialog) → `useAprobarLote` → mover lote fuera de la cola

## 11. Extensión monitor-seguimiento (F2.9)

- [x] 11.1 Actualizar `useMonitorSeguimiento` en `features/gestion-comision/hooks/` para aceptar parámetros opcionales `fecha_desde` y `fecha_hasta`
- [x] 11.2 Actualizar `MonitorSeguimiento.tsx` para mostrar condicionalmente los filtros de rango de fechas cuando el usuario tiene rol COORDINADOR o ADMIN

## 12. Integración y routing

- [x] 12.1 Agregar rutas en `frontend/src/router/index.tsx`:
  - `/coordinacion/equipos` — `RequireRole(['COORDINADOR', 'ADMIN'])`
  - `/coordinacion/avisos` — `RequireRole(['COORDINADOR', 'ADMIN'])`
  - `/coordinacion/encuentros` — `RequireRole(['COORDINADOR', 'ADMIN'])`
  - `/coordinacion/coloquios` — `RequireRole(['COORDINADOR', 'ADMIN'])`
  - `/coordinacion/monitor-general` — `RequireRole(['COORDINADOR', 'ADMIN'])`
  - `/coordinacion/comunicaciones/aprobacion` — `RequireRole(['COORDINADOR', 'ADMIN'])`
  - `/tareas` — `RequireRole(['TUTOR', 'PROFESOR', 'COORDINADOR', 'ADMIN'])`
- [x] 12.2 Agregar entradas de nav en `NavMenu.tsx` condicionales al rol: "Equipos", "Avisos", "Tareas", "Encuentros", "Coloquios", "Monitor" bajo sección "Coordinación"
- [x] 12.3 Verificar que el acceso fail-closed funciona: usuario PROFESOR no puede acceder a `/coordinacion/*` (devuelve 403 o redirige)

## 13. Tests

- [x] 13.1 Tests de `AsignacionesView`: render con datos, filtro por materia, botón exportar dispara descarga
- [x] 13.2 Tests de `ClonarEquipoForm`: validación de origen y destino, advertencia con asignaciones existentes, confirmación exitosa
- [x] 13.3 Tests de `AvisoForm`: validación de contexto condicional (materia requerida si alcance="materia"), validación de fechas, toggle require_ack
- [x] 13.4 Tests de `TareasPage`: bifurcación por rol (PROFESOR ve solo sus tareas, COORDINADOR ve global), cambio de estado inline, agregar comentario
- [x] 13.5 Tests de `ColoquiosPage`: KPIs en cabecera, crear convocatoria con múltiples días, importar alumnos (éxito + error), agenda de reservas vacía
- [x] 13.6 Tests de `AprobacionComunicacionesPage`: listado vacío, aprobar lote actualiza estado, cancelar lote requiere confirmación
- [x] 13.7 Tests de `MonitorSeguimiento` extendido: filtros de fecha visibles para COORDINADOR, ocultos para PROFESOR
