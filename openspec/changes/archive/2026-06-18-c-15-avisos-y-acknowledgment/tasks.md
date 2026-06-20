> Strict TDD por task: Safety Net (si toca archivo existente) → RED (test que falla) → GREEN (mínimo) → TRIANGULATE (≥2 casos) → REFACTOR. Tests con DB real/efímera, sin mocks de DB. ≤500 LOC por archivo backend.

## 1. Modelos y migración

- [x] 1.1 RED+GREEN: modelo `Aviso` (E13) con `tenant_id`, `alcance` y `severidad` como VARCHAR+CHECK, `materia_id`/`cohorte_id`/`rol_destino` nullable, `titulo`, `cuerpo`, `inicio_en`, `fin_en`, `orden`, `activo`, `requiere_ack`, `deleted_at`, timestamps; test de persistencia tenant-scoped
- [x] 1.2 RED+GREEN: modelo `AcknowledgmentAviso` con FKs `aviso_id`/`usuario_id`, `confirmado_at` server_default; UNIQUE `(aviso_id, usuario_id)`; test de persistencia y unicidad
- [x] 1.3 Migración Alembic `013_avisos.py`: tablas `aviso` y `acknowledgment_aviso` con índices `(tenant_id, alcance)`, `(tenant_id, materia_id)`, `(tenant_id, cohorte_id)` en `aviso` y `(tenant_id, aviso_id)` en `acknowledgment_aviso`; verificar upgrade/downgrade
- [x] 1.4 RED+GREEN: constraint `@model_validator` en schema `AvisoCreate` — `PorMateria` exige `materia_id`, `PorCohorte` exige `cohorte_id`, `PorRol` exige `rol_destino`; test rechaza combinaciones incoherentes

## 2. Schemas Pydantic (extra='forbid')

- [x] 2.1 RED+GREEN: schemas `AvisoCreate`, `AvisoUpdate`, `AvisoResponse` (incluye `total_acks`) con `model_config = ConfigDict(extra='forbid')`; test rechaza campo extra y `alcance` inválido
- [x] 2.2 RED+GREEN: schema `AvisoListItem` (para `mis-avisos`) y `AckResponse` con `extra='forbid'`; test rechaza campo extra

## 3. Lógica pura — filtrado de audiencia y vigencia

- [x] 3.1 RED: test `aviso_es_vigente(inicio_en, fin_en, ahora)` → True cuando ahora está en rango
- [x] 3.2 GREEN: implementar `aviso_es_vigente` (mínimo)
- [x] 3.3 TRIANGULATE: caso `ahora < inicio_en` → False; caso `ahora > fin_en` → False; caso exactamente en borde → True
- [x] 3.4 RED+GREEN+TRIANGULATE: `usuario_en_audiencia(aviso_alcance, aviso_rol_destino, aviso_cohorte_id, aviso_materia_id, usuario_rol, usuario_cohorte_ids, usuario_materia_ids)` — Global→True siempre; PorRol→solo si rol coincide; PorCohorte→solo si cohorte_id en lista; PorMateria→solo si materia_id en lista
- [x] 3.5 REFACTOR: extraer constantes de alcance y severidad; limpiar nombres

## 4. Repositories (tenant-scoped, BaseRepository)

- [x] 4.1 RED+GREEN: `AvisoRepository` (create, get_by_id, list, update, soft_delete) filtrando por `tenant_id`; test de aislamiento entre tenants y soft delete excluye de listados
- [x] 4.2 RED+GREEN: `AvisoRepository.listar_para_usuario(usuario_id, rol, cohorte_ids, materia_ids, ahora)` — filtro SQL de audiencia + vigencia + activo + ack (NOT EXISTS); test que Global lo ven todos y PorRol solo el rol correcto
- [x] 4.3 RED+GREEN: `AcknowledgmentAvisoRepository` (create con captura de IntegrityError, contar_acks(aviso_id)); test de creación y unicidad
- [x] 4.4 RED+GREEN: `AvisoRepository.get_cohortes_del_usuario` no es de este repo — se usa `UsuarioRepository` existente; verificar que el método de cohortes existe o crear helper en service

## 5. Service — gestión de avisos

- [x] 5.1 RED+GREEN: `AvisoService.crear` setea `tenant_id` del JWT; test happy path con alcance Global y PorMateria
- [x] 5.2 RED+GREEN: `AvisoService.actualizar` y `eliminar` (soft delete) verifican que el aviso pertenece al tenant; test happy path y 404 si no existe
- [x] 5.3 RED+GREEN: `AvisoService.listar_para_usuario` obtiene cohorte/materia del usuario, arma filtro, retorna lista ordenada por `orden`; test orden correcto y exclusión de ack-eados
- [x] 5.4 RED+GREEN: `AvisoService.listar_admin` retorna todos los avisos activos del tenant con `total_acks`; test de contadores derivados

## 6. Service — acuse de recibo

- [x] 6.1 RED: test `AckService.acusar(aviso_id, current_user)` con aviso vigente y usuario en audiencia → crea ack
- [x] 6.2 GREEN: implementar `acusar` (verifica vigencia, audiencia, crea)
- [x] 6.3 TRIANGULATE: aviso no vigente → 404/403; usuario fuera de audiencia → 403; segundo ack → 409 (IntegrityError capturado)
- [x] 6.4 REFACTOR: si service supera ~350 LOC, separar `aviso_service.py` y `ack_service.py`

## 7. Routers + RBAC (fail-closed)

- [x] 7.1 RED+GREEN: `POST /api/avisos/` con `require_permission("avisos:publicar")`; test 403 sin permiso y 201 con permiso
- [x] 7.2 RED+GREEN: `PATCH /api/avisos/{id}` y `DELETE /api/avisos/{id}` con `avisos:publicar`; test 403 sin permiso y 404 para aviso de otro tenant
- [x] 7.3 RED+GREEN: `GET /api/avisos/mis-avisos` (cualquier rol autenticado); test listado filtrado por audiencia y vigencia; test 401 sin auth
- [x] 7.4 RED+GREEN: `GET /api/avisos/` (admin) con `avisos:publicar`; test incluye `total_acks` por aviso
- [x] 7.5 RED+GREEN: `POST /api/avisos/{id}/ack` con `avisos:ack`; test 201 happy path, 409 duplicado, 403 fuera de audiencia
- [x] 7.6 Registrar `avisos_router` en `main.py`; verificar `response_model` explícito y `async def` en cada handler

## 8. RBAC seed + integración E2E

- [x] 8.1 Alta de `avisos:publicar` (COORDINADOR/ADMIN) y `avisos:ack` (todos los roles) en catálogo/seed RBAC; test de asignación correcta por rol
- [x] 8.2 Test E2E FL-09: crear aviso Global requiere_ack → ALUMNO lo ve en mis-avisos → ALUMNO acusa recibo → aviso desaparece de mis-avisos → admin consulta total_acks=1
- [x] 8.3 Test E2E segmentación: aviso PorRol=ALUMNO → PROFESOR no lo ve, ALUMNO sí → aviso PorCohorte → solo la cohorte correcta lo ve
- [x] 8.4 Verificar cobertura ≥80% líneas / ≥90% reglas de negocio (vigencia, audiencia, unicidad ack)
- [x] 8.5 Verificar ≤500 LOC por archivo backend; separar si excede
