## 1. Schemas Pydantic (equipos)

- [x] 1.1 Crear `backend/app/schemas/equipo.py` con `MiEquipoItem` (campos: id, usuario_id, rol, materia_id, carrera_id, cohorte_id, comisiones, desde, hasta, estado_vigencia, responsable_id)
- [x] 1.2 Agregar `AsignacionMasivaRequest` al schema: `usuario_ids: list[UUID]` (min_length=1), `rol`, `materia_id`, `carrera_id?`, `cohorte_id?`, `comisiones`, `desde`, `hasta?`
- [x] 1.3 Agregar `ClonarEquipoRequest` al schema: `origen: EquipoContextRef`, `destino: EquipoContextRef`, `desde`, `hasta?`; `EquipoContextRef = {materia_id, carrera_id?, cohorte_id?}`
- [x] 1.4 Agregar `ModificarVigenciaRequest` al schema: `filtro: EquipoContextRef`, `desde`, `hasta?`; response `ModificarVigenciaResponse = {modificadas: int}`
- [x] 1.5 Agregar `UsuarioBusquedaItem` al schema: `id`, `nombre`, `apellidos` (sin PII cifrada); y `ClonarEquipoResponse = {clonadas: int}`
- [x] 1.6 Agregar `model_config = ConfigDict(extra='forbid')` a todos los schemas nuevos

## 2. Repositorio — métodos de equipos

- [x] 2.1 Agregar `list_by_usuario` a `AsignacionRepository`: filtra por `tenant_id` + `usuario_id` (del JWT) con parámetros opcionales `estado_vigencia`, `materia_id`, `rol`, `carrera_id`, `cohorte_id`
- [x] 2.2 Agregar `bulk_create` a `AsignacionRepository`: inserta lista de `Asignacion` en una sola transacción; hace rollback completo ante cualquier fallo
- [x] 2.3 Agregar `clone_from` a `AsignacionRepository`: lee asignaciones vigentes de un contexto origen (`tenant_id`, `materia_id`, `cohorte_id`), retorna lista de objetos `Asignacion` listos para insertar con contexto destino
- [x] 2.4 Agregar `bulk_update_vigencia` a `AsignacionRepository`: UPDATE `desde`/`hasta` en todas las asignaciones del tenant que coincidan con `materia_id` (+ `carrera_id?` + `cohorte_id?`); retorna `filas_afectadas`
- [x] 2.5 Agregar `list_for_export` a `AsignacionRepository`: versión de query que hace JOIN con `usuarios`, `materias`, `carreras`, `cohortes` para obtener los campos del CSV en un único query

## 3. Búsqueda de usuarios (autocompletado)

- [x] 3.1 Agregar `UsuarioRepository.search_by_name(tenant_id, q: str) -> list[Usuario]`: filtra por `tenant_id` y `nombre ILIKE %q%` OR `apellidos ILIKE %q%`; retorna máx 20 resultados; requiere `len(q) >= 2`

## 4. Service — EquipoService

- [x] 4.1 Crear `backend/app/services/equipo_service.py` con clase `EquipoService`
- [x] 4.2 Implementar `get_mis_equipos(current_user, filtros)`: llama a `AsignacionRepository.list_by_usuario`, calcula `estado_vigencia` para cada registro, retorna lista de `MiEquipoItem`
- [x] 4.3 Implementar `buscar_usuarios(current_user, q: str)`: valida `len(q) >= 2`, llama a `UsuarioRepository.search_by_name`, retorna lista de `UsuarioBusquedaItem` sin PII cifrada
- [x] 4.4 Implementar `asignar_masiva(current_user, request)`: crea una `Asignacion` por cada `usuario_id`, llama a `bulk_create` en una transacción, luego llama a `audit_service.log(ASIGNACION_MODIFICAR, filas_afectadas=len(usuario_ids))`
- [x] 4.5 Implementar `clonar_equipo(current_user, request)`: llama a `clone_from`, aplica contexto destino y fechas, llama a `bulk_create`, registra auditoría `ASIGNACION_MODIFICAR`
- [x] 4.6 Implementar `modificar_vigencia(current_user, request)`: llama a `bulk_update_vigencia`, registra auditoría `ASIGNACION_MODIFICAR`
- [x] 4.7 Implementar `exportar_equipo(current_user, filtros)`: llama a `list_for_export` y genera generador de filas CSV

## 5. Router — equipos

- [x] 5.1 Crear `backend/app/api/v1/routers/equipos.py`
- [x] 5.2 Agregar `GET /api/equipos/mis-equipos`: requiere solo autenticación (no guard de equipos:asignar — el docente ve sus propios equipos); delega a `equipo_service.get_mis_equipos`
- [x] 5.3 Agregar `GET /api/equipos/usuarios/buscar`: requiere permiso `equipos:asignar`; delega a `equipo_service.buscar_usuarios`; valida `len(q) >= 2` en query param
- [x] 5.4 Agregar `POST /api/equipos/asignaciones/masiva`: requiere permiso `equipos:asignar`; delega a `equipo_service.asignar_masiva`; retorna HTTP 201
- [x] 5.5 Agregar `POST /api/equipos/asignaciones/clonar`: requiere permiso `equipos:asignar`; delega a `equipo_service.clonar_equipo`; retorna HTTP 201
- [x] 5.6 Agregar `PATCH /api/equipos/asignaciones/vigencia`: requiere permiso `equipos:asignar`; delega a `equipo_service.modificar_vigencia`; retorna HTTP 200
- [x] 5.7 Agregar `GET /api/equipos/asignaciones/exportar`: requiere permiso `equipos:asignar`; delega a `equipo_service.exportar_equipo`; retorna `StreamingResponse` con `Content-Type: text/csv`
- [x] 5.8 Registrar el router `equipos` en `backend/app/main.py` con prefijo `/api/equipos`

## 6. Tests — mis-equipos y búsqueda

- [x] 6.1 Test `GET /api/equipos/mis-equipos` — docente autenticado ve solo sus asignaciones del tenant
- [x] 6.2 Test `GET /api/equipos/mis-equipos` — filtro por `materia_id` retorna subconjunto correcto
- [x] 6.3 Test `GET /api/equipos/mis-equipos` — `estado_vigencia` se calcula correctamente (Vigente/Vencida según fechas)
- [x] 6.4 Test `GET /api/equipos/mis-equipos` — identidad no puede ser suplantada por querystring
- [x] 6.5 Test `GET /api/equipos/mis-equipos` sin token → HTTP 401
- [x] 6.6 Test `GET /api/equipos/usuarios/buscar?q=mar` — retorna usuarios del tenant con coincidencia
- [x] 6.7 Test `GET /api/equipos/usuarios/buscar?q=m` — retorna HTTP 422
- [x] 6.8 Test `GET /api/equipos/usuarios/buscar` — respuesta no expone PII cifrada

## 7. Tests — asignación masiva

- [x] 7.1 Test `POST /api/equipos/asignaciones/masiva` con 3 usuario_ids — crea 3 asignaciones, retorna HTTP 201
- [x] 7.2 Test masiva con `usuario_ids: []` — retorna HTTP 422
- [x] 7.3 Test masiva sin permiso — retorna HTTP 403
- [x] 7.4 Test masiva con usuario_id de otro tenant — rollback completo, ninguna asignación creada
- [x] 7.5 Test masiva — se registra `AuditLog` con `accion = "ASIGNACION_MODIFICAR"` y `filas_afectadas = 3`

## 8. Tests — clonar equipo

- [x] 8.1 Test `POST /api/equipos/asignaciones/clonar` — clona 3 asignaciones vigentes del origen al destino con nuevas fechas
- [x] 8.2 Test clonar con origen sin asignaciones vigentes — retorna `{ "clonadas": 0 }`
- [x] 8.3 Test clonar con origen de otro tenant — retorna `{ "clonadas": 0 }` (aislamiento)
- [x] 8.4 Test clonar — asignaciones del origen NO se modifican (son copias independientes)
- [x] 8.5 Test clonar — se registra `AuditLog` con `filas_afectadas` correcto

## 9. Tests — modificar vigencia y exportar

- [x] 9.1 Test `PATCH /api/equipos/asignaciones/vigencia` — actualiza `desde`/`hasta` de las asignaciones del equipo y retorna `{ "modificadas": N }`
- [x] 9.2 Test modificar vigencia con filtro sin coincidencias — retorna `{ "modificadas": 0 }`
- [x] 9.3 Test modificar vigencia con `hasta: null` — setea vigencia abierta en todas las asignaciones
- [x] 9.4 Test modificar vigencia — se registra `AuditLog` con `filas_afectadas` correcto
- [x] 9.5 Test `GET /api/equipos/asignaciones/exportar` — retorna HTTP 200 con `Content-Type: text/csv` y header `Content-Disposition`
- [x] 9.6 Test exportar con filtro por `materia_id` — CSV contiene solo filas de esa materia
- [x] 9.7 Test exportar sin permiso — retorna HTTP 403
- [x] 9.8 Test exportar — CSV tiene columnas esperadas (usuario_id, nombre, apellidos, rol, materia, carrera, cohorte, comisiones, desde, hasta, estado_vigencia)

## 10. Multi-tenancy e integración

- [x] 10.1 Test de aislamiento: un usuario de tenant B no puede ver mis-equipos de tenant A
- [x] 10.2 Test de aislamiento: masiva de tenant A no puede asignar usuarios de tenant B
- [x] 10.3 Test end-to-end: crear equipo con masiva → clonar a nueva cohorte → exportar → verificar CSV
