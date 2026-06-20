> Strict TDD por task: Safety Net (si toca archivo existente) → RED (test que falla) → GREEN (mínimo) → TRIANGULATE (≥2 casos) → REFACTOR. Tests con DB real/efímera, canal externo mockeable. Sin mocks de DB.

## 1. Modelos y migración

- [x] 1.1 RED+GREEN: modelo `SlotEncuentro` (E9) con `tenant_id`, FKs `asignacion_id`/`materia_id`, `dia_semana`/estados como VARCHAR+CHECK, `deleted_at`, timestamps; test de persistencia tenant-scoped
- [x] 1.2 RED+GREEN: modelo `InstanciaEncuentro` (E10) con `slot_id` nullable, `materia_id`, `estado` (Programado|Realizado|Cancelado), `video_url` nullable; test de persistencia
- [x] 1.3 RED+GREEN: modelo `Guardia` (E11) con FKs `asignacion_id`/`materia_id`/`carrera_id`/`cohorte_id`, `estado`, `creada_at`, `deleted_at`; test de persistencia
- [x] 1.4 Migración Alembic única: tablas `slot_encuentro`, `instancia_encuentro`, `guardia` con índices `(tenant_id, asignacion_id)` (slots/guardias) y `(tenant_id, slot_id)` (instancias); verificar upgrade/downgrade

## 2. Helpers puros (recurrencia + HTML)

- [x] 2.1 RED: test de `generar_fechas_recurrencia(dia_semana, fecha_inicio, cant_semanas)` con `cant_semanas=4` → 4 fechas paso 7 días
- [x] 2.2 GREEN: implementar `generar_fechas_recurrencia` (mínimo)
- [x] 2.3 TRIANGULATE: caso `fecha_inicio` que no cae en `dia_semana` → alinea al primer día correcto; caso `cant_semanas=1`
- [x] 2.4 REFACTOR: extraer constantes de día de semana; limpiar
- [x] 2.5 RED+GREEN+TRIANGULATE: `render_encuentros_html(instancias)` — test de estructura del fragmento (fechas, links `meet_url`/`video_url`), caso lista vacía

## 3. Repositories (tenant-scoped, BaseRepository)

- [x] 3.1 RED+GREEN: `SlotEncuentroRepository` (create, get_by_id) filtrando por `tenant_id`; test de aislamiento entre tenants
- [x] 3.2 RED+GREEN: `InstanciaEncuentroRepository` (bulk_create, get_by_id, update, list_by_asignacion); test bulk insert
- [x] 3.3 RED+GREEN: `GuardiaRepository` (create, list, soft_delete) tenant-scoped; test soft delete excluye de listados

## 4. Service de encuentros — creación recurrente (RN-13.1)

- [x] 4.1 RED: test `EncuentroService.crear_slot_recurrente` con `cant_semanas=4` genera 4 instancias `Programado`
- [x] 4.2 GREEN: implementar creación de slot + bulk de instancias usando el helper de recurrencia
- [x] 4.3 TRIANGULATE: validar tope `cant_semanas ≤ 52`; caso `fecha_inicio` desalineada
- [x] 4.4 RED+GREEN: validación RN-13 excluyente — ambos modos seteados → error de dominio; ningún modo → error
- [x] 4.5 REFACTOR: si el service supera ~400 LOC, separar helpers; revisar nombres

## 5. Service de encuentros — único (RN-13.2) y edición (RN-14)

- [x] 5.1 RED+GREEN+TRIANGULATE: `crear_encuentro_unico` genera 1 instancia con `slot_id=NULL`; caso sin `fecha_unica` → error
- [x] 5.2 RED: test `editar_instancia` marca `Realizado` + `video_url` y NO cambia el slot ni otras instancias del mismo slot (RN-14)
- [x] 5.3 GREEN: implementar `editar_instancia` operando solo sobre `instancia_encuentro`
- [x] 5.4 TRIANGULATE: transición a `Cancelado` conserva `fecha`/`hora`; edición de `meet_url`/`comentario`
- [x] 5.5 RED+GREEN: control de acceso — PROFESOR solo su asignación; COORDINADOR/ADMIN cualquiera

## 6. Service de encuentros — HTML y vista admin

- [x] 6.1 RED+GREEN: `generar_html_asignacion(asignacion_id)` arma instancias y delega al helper; test de fragmento
- [x] 6.2 RED+GREEN: `listar_admin_encuentros` transversal dentro del tenant (filtra `tenant_id`); test no devuelve otros tenants

## 7. Service de guardias

- [x] 7.1 RED+GREEN: `GuardiaService.registrar` setea `creada_at` server-side, tenant del JWT; test happy path
- [x] 7.2 TRIANGULATE: estado inicial provisto se respeta; caso datos inválidos → error
- [x] 7.3 RED+GREEN: `listar` para consulta/export filtrando por `tenant_id`; test aislamiento

## 8. Schemas Pydantic (extra='forbid')

- [x] 8.1 RED+GREEN: schemas request/response de slots y encuentros con `model_config = ConfigDict(extra='forbid')`; test rechaza campo extra
- [x] 8.2 RED+GREEN: schemas request/response de guardias con `extra='forbid'`; test rechaza campo extra

## 9. Routers + RBAC (fail-closed)

- [x] 9.1 RED+GREEN: `POST /api/v1/slots` con `require_permission("encuentros:gestionar")` y `get_current_user`; test 403 sin permiso
- [x] 9.2 RED+GREEN: `POST /api/v1/encuentros` (único) y `PATCH /api/v1/encuentros/{id}`; test edición + 403
- [x] 9.3 RED+GREEN: `GET /api/v1/encuentros/html` devuelve fragmento; test estructura
- [x] 9.4 RED+GREEN: `GET /api/v1/admin/encuentros` solo COORDINADOR/ADMIN; test 403 para PROFESOR
- [x] 9.5 RED+GREEN: `POST /api/v1/guardias` (TUTOR) y `GET /api/v1/guardias` (COORDINADOR/ADMIN); test 403 cruzado
- [x] 9.6 Registrar routers en la app; verificar `response_model` explícito en cada handler

## 10. RBAC seed + integración E2E

- [x] 10.1 Alta del permiso `encuentros:gestionar` en el catálogo/seed RBAC; test de asignación a PROFESOR/COORDINADOR/ADMIN
- [x] 10.2 Test E2E FL-06: crear slot recurrente → N instancias → editar una a Realizado+video → admin audita → HTML incluye grabación
- [x] 10.3 Verificar cobertura ≥80% líneas / ≥90% reglas de negocio (RN-13, RN-14, acceso scoped)
- [x] 10.4 Verificar ≤500 LOC por archivo backend; separar si excede
