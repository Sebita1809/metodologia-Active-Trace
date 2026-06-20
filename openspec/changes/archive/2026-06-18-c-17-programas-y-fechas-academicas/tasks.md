## 1. Migración

- [x] 1.1 Crear `backend/alembic/versions/015_programas_fechas_academicas.py` (revision "015", revises "014", Create Date 2026-06-18)
- [x] 1.2 Definir tabla `programa_materia` con columnas BaseTenantModel (id, tenant_id, created_at, updated_at, deleted_at) + materia_id (FK materias RESTRICT), carrera_id (FK carreras RESTRICT), cohorte_id (FK cohortes RESTRICT), titulo (texto), referencia_archivo (texto)
- [x] 1.3 Definir tabla `fecha_academica` con columnas BaseTenantModel + materia_id (FK materias RESTRICT), cohorte_id (FK cohortes RESTRICT), tipo (VARCHAR 20), numero (entero), periodo (texto nullable), fecha (DATE), titulo (texto)
- [x] 1.4 Agregar CheckConstraint `ck_fecha_academica_tipo_valid` (tipo IN Parcial, TP, Coloquio, Recuperatorio) y `ck_fecha_academica_numero_positivo` (numero >= 1)
- [x] 1.5 Crear índice único parcial `uq_programa_materia_combo` sobre (tenant_id, materia_id, carrera_id, cohorte_id) WHERE deleted_at IS NULL
- [x] 1.6 Crear índice único parcial `uq_fecha_academica_combo` sobre (tenant_id, materia_id, cohorte_id, tipo, numero) WHERE deleted_at IS NULL
- [x] 1.7 Crear índices `ix_programa_materia_tenant_materia` y `ix_fecha_academica_tenant_materia_cohorte` (tenant_id, materia_id, cohorte_id)
- [x] 1.8 Seed RBAC del permiso `estructura:gestionar` (COORDINADOR, ADMIN; alcance global) por tenant, con ON CONFLICT DO NOTHING
- [x] 1.9 Implementar `downgrade` que dropea índices, constraints y ambas tablas

## 2. Modelos

- [x] 2.1 Crear `TipoFechaAcademica(StrEnum)` con Parcial, TP, Coloquio, Recuperatorio
- [x] 2.2 Crear `backend/app/models/programa_materia.py` (`ProgramaMateria(BaseTenantModel)`) con columnas materia_id, carrera_id, cohorte_id, titulo, referencia_archivo
- [x] 2.3 Crear `backend/app/models/fecha_academica.py` (`FechaAcademica(BaseTenantModel)`) con columnas + CheckConstraints de tipo y numero
- [x] 2.4 Registrar ambos modelos en `backend/app/models/__init__.py`

## 3. Repositories

- [x] 3.1 Crear `backend/app/repositories/programa_materia_repository.py` (`ProgramaMateriaRepository(BaseRepository)`)
- [x] 3.2 Implementar `get_vivo_por_combo(materia_id, carrera_id, cohorte_id)` tenant-scoped (excluye soft-deleted)
- [x] 3.3 Implementar `listar(filtros materia_id/carrera_id/cohorte_id opcionales)` tenant-scoped
- [x] 3.4 Crear `backend/app/repositories/fecha_academica_repository.py` (`FechaAcademicaRepository(BaseRepository)`)
- [x] 3.5 Implementar `listar_por_materia_cohorte(materia_id, cohorte_id)` ordenado por `fecha` asc, tenant-scoped
- [x] 3.6 Implementar `existe_combo(materia_id, cohorte_id, tipo, numero)` tenant-scoped (excluye soft-deleted)
- [x] 3.7 Implementar `get_by_id` tenant-scoped (excluye soft-deleted)

## 4. Schemas

- [x] 4.1 Crear `backend/app/schemas/programas.py` con `model_config = ConfigDict(extra='forbid')`
- [x] 4.2 `ProgramaCreate` (materia_id, carrera_id, cohorte_id, titulo, referencia_archivo) — sin tenant_id
- [x] 4.3 `ProgramaResponse` (todos los campos persistidos) y `ProgramaFiltros` (materia_id?, carrera_id?, cohorte_id?)
- [x] 4.4 Crear `backend/app/schemas/fechas_academicas.py` con `model_config = ConfigDict(extra='forbid')`
- [x] 4.5 `FechaAcademicaCreate` (materia_id, cohorte_id, tipo: TipoFechaAcademica, numero, fecha, titulo, periodo?)
- [x] 4.6 `FechaAcademicaUpdate` (fecha?, titulo?, periodo?)
- [x] 4.7 `FechaAcademicaResponse` (todos los campos persistidos)
- [x] 4.8 `FragmentoLmsResponse` (materia_id, cohorte_id, formato, contenido)

## 5. Services

- [x] 5.1 Crear `backend/app/services/programa_materia_service.py`
- [x] 5.2 `asociar_programa` — validar materia/carrera/cohorte del tenant; si existe programa vivo del combo, soft-delete del anterior y crear el nuevo
- [x] 5.3 `obtener_por_combo` y `listar` tenant-scoped
- [x] 5.4 Crear `backend/app/services/fecha_academica_service.py`
- [x] 5.5 `crear_fecha` — validar materia/cohorte del tenant, validar unicidad del combo (tipo+numero), persistir
- [x] 5.6 `actualizar_fecha` y `eliminar_fecha` (soft-delete) tenant-scoped
- [x] 5.7 `listar_por_materia_cohorte` tenant-scoped
- [x] 5.8 `generar_fragmento_lms` — formatear las fechas vivas de la combinación ordenadas por fecha en texto/HTML, sin llamar al LMS

## 6. Routers

- [x] 6.1 Crear `backend/app/api/v1/routers/programas.py` con prefix `/api/v1/programas`, todos los endpoints con `require_permission("estructura:gestionar")`
- [x] 6.2 Endpoints programas: POST (asociar/reemplazar), GET por combo, GET listado
- [x] 6.3 Crear `backend/app/api/v1/routers/fechas_academicas.py` con prefix `/api/v1/fechas-academicas`, todos los endpoints con `require_permission("estructura:gestionar")`
- [x] 6.4 Endpoints fechas: POST crear, GET listado por materia×cohorte, PATCH actualizar, DELETE (soft), GET `/fragmento-lms`
- [x] 6.5 Registrar ambos routers en `backend/app/main.py`

## 7. Tests

- [x] 7.1 Tests de migración 015: upgrade/downgrade, índices únicos parciales y CheckConstraints aplican
- [x] 7.2 Tests programa: alta nueva combinación, referencia opaca, listado y filtros (DB real)
- [x] 7.3 Tests programa: reemplazo soft-deletea el anterior y deja un único vivo; re-alta sobre combo borrado funciona
- [x] 7.4 Tests programa: validación de materia/carrera/cohorte de otro tenant rechazada
- [x] 7.5 Tests programa: aislamiento por tenant (404 cross-tenant, listado acotado)
- [x] 7.6 Tests fecha: alta válida, tipo fuera de enum y numero=0 rechazados, combo duplicado rechazado
- [x] 7.7 Tests fecha: listado tabular ordenado por fecha; update y soft-delete; re-alta sobre combo borrado
- [x] 7.8 Tests fecha: generación de fragmento LMS (formato, orden, combinación vacía) sin llamada a LMS
- [x] 7.9 Tests fecha: validación de referencias y aislamiento por tenant
- [x] 7.10 Tests RBAC: endpoints de ambos routers responden 403 sin `estructura:gestionar`
