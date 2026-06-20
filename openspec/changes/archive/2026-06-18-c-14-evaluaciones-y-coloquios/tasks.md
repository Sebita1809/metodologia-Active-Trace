> Strict TDD por task: Safety Net (si toca archivo existente) → RED (test que falla) → GREEN (mínimo) → TRIANGULATE (≥2 casos) → REFACTOR. Tests con DB real/efímera, sin mocks de DB. ≤500 LOC por archivo backend.

## 1. Modelos y migración

- [x] 1.1 RED+GREEN: modelo `Evaluacion` (E14) con `tenant_id`, FKs `materia_id`/`cohorte_id`, `tipo` y `estado` como VARCHAR+CHECK, `instancia`, `dias_disponibles`, `cupo_por_dia`, `deleted_at`, timestamps; test de persistencia tenant-scoped
- [x] 1.2 RED+GREEN: modelo `ReservaEvaluacion` (E14) con FKs `evaluacion_id`/`alumno_id`, `fecha_hora`, `estado` (Activa|Cancelada) VARCHAR+CHECK, `deleted_at`, timestamps; test de persistencia
- [x] 1.3 RED+GREEN: modelo `ResultadoEvaluacion` (E14) con FKs `evaluacion_id`/`alumno_id`, `nota_final` (texto), `deleted_at`, timestamps; test de persistencia
- [x] 1.4 Migración Alembic única `012_evaluaciones_coloquios.py`: tablas `evaluacion`, `reserva_evaluacion`, `resultado_evaluacion` con índices `(tenant_id, materia_id)` (evaluacion) y `(tenant_id, evaluacion_id)` (reservas/resultados); verificar upgrade/downgrade
- [x] 1.5 RED+GREEN: constraint UNIQUE `(evaluacion_id, alumno_id)` en `resultado_evaluacion` y UNIQUE parcial `(evaluacion_id, alumno_id) WHERE estado='Activa'` en `reserva_evaluacion`; test que la segunda fila viola la constraint

## 2. Schemas Pydantic (extra='forbid')

- [x] 2.1 RED+GREEN: schemas request/response de `Evaluacion` (crear, listado-con-métricas) con `model_config = ConfigDict(extra='forbid')`; test rechaza campo extra y `tipo` inválido
- [x] 2.2 RED+GREEN: schemas de importación de padrón (lista de `alumno_id`) y de `ReservaEvaluacion` (request `fecha_hora`, response) con `extra='forbid'`; test rechaza campo extra
- [x] 2.3 RED+GREEN: schemas de `ResultadoEvaluacion` y del panel de métricas con `extra='forbid'`; test rechaza campo extra

## 3. Lógica pura — cupo y métricas

- [x] 3.1 RED: test `hay_cupo(reservas_activas_en_fecha, cupo_por_dia)` → True cuando `reservas < cupo`
- [x] 3.2 GREEN: implementar `hay_cupo` (mínimo)
- [x] 3.3 TRIANGULATE: caso `reservas == cupo` → False (lleno); caso `cupo=0` → False
- [x] 3.4 RED+GREEN+TRIANGULATE: `cupos_libres(cupo_por_dia, reservas_activas)` y derivación de métricas (convocados/reservas_activas/notas) a partir de contadores; casos con cero y con saturación
- [x] 3.5 REFACTOR: extraer constantes/enums de estado y tipo; limpiar nombres

## 4. Repositories (tenant-scoped, BaseRepository)

- [x] 4.1 RED+GREEN: `EvaluacionRepository` (create, get_by_id, list, soft_delete) filtrando por `tenant_id`; test de aislamiento entre tenants y soft delete excluye de listados
- [x] 4.2 RED+GREEN: `EvaluacionRepository.contar_reservas_activas(evaluacion_id, fecha)` y agregados de métricas (convocados, reservas_activas, notas_registradas, instancias_activas); test de conteo por estado/fecha
- [x] 4.3 RED+GREEN: `ReservaEvaluacionRepository` (create con captura de IntegrityError, get_by_id, cambiar_estado, list_by_evaluacion); test de creación y listado tenant-scoped
- [x] 4.4 RED+GREEN: `ResultadoEvaluacionRepository` (create, list_by_evaluacion); test que el duplicado `(evaluacion_id, alumno_id)` lanza IntegrityError
- [x] 4.5 RED+GREEN: import de padrón en bulk validando existencia/tenant de cada `alumno_id`; test rechaza lote con alumno de otro tenant

## 5. Service — convocatoria, padrón y métricas

- [x] 5.1 RED+GREEN: `EvaluacionService.crear` setea `estado='Activa'` y tenant del JWT; test happy path
- [x] 5.2 RED+GREEN: `importar_padron` valida y carga candidatos; test lote válido y caso alumno de otro tenant → error
- [x] 5.3 RED+GREEN: `listar_con_metricas` arma por evaluación convocados/reservas_activas/cupos_libres; test de cálculo correcto
- [x] 5.4 RED+GREEN: `metricas_panel` (F7.1) devuelve los cuatro contadores tenant-scoped; test de agregación

## 6. Service — reserva (cupo + unicidad + cancelación)

- [x] 6.1 RED: test `ReservaService.reservar` con cupo disponible crea reserva `Activa` con `alumno_id` del JWT
- [x] 6.2 GREEN: implementar `reservar` (cuenta reservas activas en fecha, valida cupo, crea)
- [x] 6.3 TRIANGULATE: cupo lleno (`reservas == cupo_por_dia`) → 409; segunda reserva activa del mismo alumno → 409 (vía IntegrityError del índice parcial)
- [x] 6.4 RED+GREEN: `cancelar` cambia `Activa → Cancelada` solo si la reserva es del `current_user` y la evaluación está `Activa`; test happy path libera cupo
- [x] 6.5 TRIANGULATE: cancelar reserva ajena → 403; cancelar sobre evaluación `Cerrada` → error; reserva ya cancelada no recuenta
- [x] 6.6 RED+GREEN: `listar_agenda(evaluacion_id)` tenant-scoped; test aislamiento entre tenants
- [x] 6.7 REFACTOR: si el service supera ~400 LOC, separar `evaluacion_service.py`/`reserva_service.py`/helpers de cupo

## 7. Service — resultados

- [x] 7.1 RED+GREEN: `ResultadoService.registrar` crea nota tenant-scoped; test happy path
- [x] 7.2 TRIANGULATE: segundo resultado para el mismo `(evaluacion_id, alumno_id)` → rechazo (IntegrityError → 409); nota cualitativa vs numérica aceptadas
- [x] 7.3 RED+GREEN: `listar_resultados(evaluacion_id)` tenant-scoped; test aislamiento

## 8. Routers + RBAC (fail-closed)

- [x] 8.1 RED+GREEN: `POST /api/v1/coloquios/` con `require_permission("coloquios:gestionar")` y `get_current_user`; test 403 sin permiso
- [x] 8.2 RED+GREEN: `GET /api/v1/coloquios/` y `GET /api/v1/coloquios/metricas` con `coloquios:ver`; test 403 para ALUMNO, response_model explícito
- [x] 8.3 RED+GREEN: `POST /api/v1/coloquios/{id}/alumnos` (importar padrón) con `coloquios:gestionar`; test 403 sin permiso
- [x] 8.4 RED+GREEN: `POST /api/v1/coloquios/{id}/reservas` con `coloquios:reservar`, `alumno_id` del JWT; test cupo lleno → 409 y 403 sin permiso
- [x] 8.5 RED+GREEN: `DELETE /api/v1/coloquios/{id}/reservas/{rid}` con `coloquios:reservar` (propia); test cancela y 403 sobre reserva ajena
- [x] 8.6 RED+GREEN: `GET /api/v1/coloquios/{id}/reservas` (agenda) con `coloquios:ver`; test 403 sin permiso
- [x] 8.7 RED+GREEN: `POST /api/v1/coloquios/{id}/resultados` (`coloquios:gestionar`) y `GET /api/v1/coloquios/{id}/resultados` (`coloquios:ver`); test 403 cruzado y duplicado → 409
- [x] 8.8 Registrar el router de coloquios en la app; verificar `response_model` explícito en cada handler y `async def`

## 9. RBAC seed + integración E2E

- [x] 9.1 Alta de `coloquios:gestionar`, `coloquios:ver`, `coloquios:reservar` en el catálogo/seed RBAC; test de asignación a COORDINADOR/ADMIN/PROFESOR/ALUMNO
- [x] 9.2 Test E2E FL-07: importar padrón → crear convocatoria con cupos → ALUMNO reserva → cupo lleno rechaza → cancelar libera cupo → coordinador consulta agenda y registra notas
- [x] 9.3 Verificar cobertura ≥80% líneas / ≥90% reglas de negocio (cupo, unicidad reserva, cancelación, unicidad resultado)
- [x] 9.4 Verificar ≤500 LOC por archivo backend; separar si excede
