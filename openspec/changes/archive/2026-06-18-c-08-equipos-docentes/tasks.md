## 1. EquipoDocenteService — Infraestructura

- [x] 1.1 Crear `backend/app/services/equipos/__init__.py`
- [x] 1.2 Crear `backend/app/services/equipos/equipo_docente_service.py` con clase `EquipoDocenteService` e inyección de dependencias (AsignacionRepository, UsuarioRepository, UmbralMateriaRepository, AuditLogService)
- [x] 1.3 Crear `backend/app/services/equipos/export_service.py` con clase `ExportService` para generación de CSV
- [x] 1.4 Registrar ambos servicios en el contenedor de dependencias (FastAPI `Depends()`)

## 2. Router /api/equipos

- [x] 2.1 Crear `backend/app/api/v1/routers/equipos.py` con `APIRouter(prefix="/api/equipos")`
- [x] 2.2 Implementar `GET /mis-equipos` protegido con `get_current_user` — retorna asignaciones vigentes del usuario autenticado
- [x] 2.3 Implementar `GET /materias/{materia_id}` protegido con `equipos:asignar` — retorna equipo completo con filtro opcional `?cohorte_id=`
- [x] 2.4 Implementar `POST /asignacion-masiva` protegido con `equipos:asignar` — asigna N docentes en bloque
- [x] 2.5 Implementar `POST /clonar` protegido con `equipos:asignar` — clona equipo entre cohortes
- [x] 2.6 Implementar `PATCH /vigencia` protegido con `equipos:asignar` — modifica fechas en bloque
- [x] 2.7 Implementar `GET /{materia_id}/exportar` protegido con `equipos:asignar` — descarga CSV del equipo
- [x] 2.8 Registrar el router en `backend/app/api/v1/routers/__init__.py`

## 3. EquipoDocenteService — Mis equipos (F4.2)

- [x] 3.1 Implementar `EquipoDocenteService.get_mis_equipos(usuario_id)` — query de asignaciones vigentes filtradas por usuario_id + tenant
- [x] 3.2 Incluir datos relacionados (materia.nombre, carrera.nombre, cohorte.nombre) en la respuesta

## 4. EquipoDocenteService — Consulta equipo por materia (F4.3)

- [x] 4.1 Implementar `EquipoDocenteService.get_equipo_por_materia(materia_id, cohorte_id=None)` — query de asignaciones por materia
- [x] 4.2 Agrupar respuesta por cohorte para facilitar visualización
- [x] 4.3 Validar que la materia existe en el tenant (404 si no)

## 5. EquipoDocenteService — Asignación masiva (F4.4)

- [x] 5.1 Implementar `EquipoDocenteService.asignacion_masiva(datos)` con validación previa completa
- [x] 5.2 Validar que materia/carrera/cohorte existen en el tenant
- [x] 5.3 Validar que el rol es un valor conocido del dominio
- [x] 5.4 Validar que `desde <= hasta`
- [x] 5.5 Validar que TODOS los `usuario_id` existen, están activos y pertenecen al tenant
- [x] 5.6 Validar límite de 200 docentes por request
- [x] 5.7 Ejecutar creación en transacción (all-or-nothing)
- [x] 5.8 Por cada asignación con rol docente (PROFESOR/TUTOR) y materia_id, crear UmbralMateria con umbral_pct=60
- [x] 5.9 Retornar lista de asignaciones creadas con resumen

## 6. EquipoDocenteService — Clonar equipo entre períodos (F4.5, RN-12)

- [x] 6.1 Implementar `EquipoDocenteService.clonar_equipo(origen, destino, desde, hasta)` con validación
- [x] 6.2 Validar que `cohorte_origen_id != cohorte_destino_id`
- [x] 6.3 Validar que materia y cohortes existen en el tenant
- [x] 6.4 Query de asignaciones vigentes del origen
- [x] 6.5 Crear copias con nuevos UUIDs, fechas del destino, preservando responsable_id
- [x] 6.6 Retornar lista de asignaciones creadas + conteo

## 7. EquipoDocenteService — Modificar vigencia en bloque (F4.6)

- [x] 7.1 Implementar `EquipoDocenteService.modificar_vigencia(materia_id, desde, hasta, cohorte_id=None)` con validación
- [x] 7.2 Validar que `desde <= hasta`
- [x] 7.3 Ejecutar UPDATE en todas las asignaciones vigentes que coincidan con los filtros
- [x] 7.4 Retornar conteo de asignaciones afectadas

## 8. ExportService — Exportar equipo (F4.7)

- [x] 8.1 Implementar `ExportService.generar_csv_equipo(asignaciones)` usando `csv.writer` + `io.StringIO`
- [x] 8.2 Formato CSV: Docente | Rol | Carrera | Cohorte | Comisiones | Desde | Hasta | Estado
- [x] 8.3 Implementar `EquipoDocenteService.exportar_equipo(materia_id, cohorte_id=None)` que consulta y delega en ExportService
- [x] 8.4 Retornar `StreamingResponse` con `text/csv` y `Content-Disposition: attachment`

## 9. Validación de desactivación C-06

- [x] 9.1 Agregar método `AsignacionRepository.tiene_asignaciones_activas(materia_id)` y equivalentes para carrera/cohorte
- [x] 9.2 Modificar `MateriaService.desactivar()` para verificar asignaciones activas antes de desactivar
- [x] 9.3 Modificar `CarreraService.desactivar()` para verificar asignaciones activas antes de desactivar
- [x] 9.4 Modificar `CohorteService.desactivar()` para verificar asignaciones activas antes de desactivar

## 10. UmbralMateria — Creación automática

- [x] 10.1 Agregar hook en `AsignacionService.crear()`: si rol es PROFESOR o TUTOR y materia_id está definido, crear UmbralMateria con umbral_pct=60
- [x] 10.2 Agregar hook en `EquipoDocenteService.asignacion_masiva()`: mismo comportamiento para cada asignación creada
- [x] 10.3 Agregar hook en `EquipoDocenteService.clonar_equipo()`: mismo comportamiento para cada asignación clonada

## 11. Auditoría

- [x] 11.1 Registrar evento `ASIGNACION_MODIFICAR` en asignación masiva exitosa
- [x] 11.2 Registrar evento `ASIGNACION_MODIFICAR` en clonación exitosa
- [x] 11.3 Registrar evento `ASIGNACION_MODIFICAR` en modificación de vigencia exitosa
- [x] 11.4 Asegurar que el detalle del evento incluya contexto relevante (conteo, materia_id, cohorte_id según corresponda)

## 12. Tests de integración

- [x] 12.1 Test: `GET /api/equipos/mis-equipos` retorna asignaciones del usuario autenticado
- [x] 12.2 Test: `GET /api/equipos/mis-equipos` con usuario sin asignaciones retorna lista vacía
- [x] 12.3 Test: `GET /api/equipos/materias/{id}` retorna equipo completo
- [x] 12.4 Test: `GET /api/equipos/materias/{id}` con materia inexistente retorna 404
- [x] 12.5 Test: `POST /api/equipos/asignacion-masiva` exitosa crea todas las asignaciones + UmbralMateria
- [x] 12.6 Test: `POST /api/equipos/asignacion-masiva` con docente inactivo retorna 422 sin crear ninguna
- [x] 12.7 Test: `POST /api/equipos/asignacion-masiva` con rol inválido retorna 422
- [x] 12.8 Test: `POST /api/equipos/asignacion-masiva` excede límite de 200 docentes retorna 422
- [x] 12.9 Test: `POST /api/equipos/clonar` exitosa duplica asignaciones
- [x] 12.10 Test: `POST /api/equipos/clonar` con cohortes iguales retorna 422
- [x] 12.11 Test: `POST /api/equipos/clonar` con cohorte destino inexistente retorna 404
- [x] 12.12 Test: `PATCH /api/equipos/vigencia` exitosa actualiza fechas
- [x] 12.13 Test: `PATCH /api/equipos/vigencia` con rango inválido retorna 422
- [x] 12.14 Test: `GET /api/equipos/{materia_id}/exportar` retorna archivo CSV
- [x] 12.15 Test: Desactivación de materia con asignaciones activas retorna 409
- [x] 12.16 Test: Desactivación de materia sin asignaciones activas se permite
- [x] 12.17 Test: Asignación masiva genera evento de auditoría
- [x] 12.18 Test: Clonación genera evento de auditoría
- [x] 12.19 Test: Modificación de vigencia genera evento de auditoría
- [x] 12.20 Test: Aislamiento multi-tenant — operación no cruza tenants
