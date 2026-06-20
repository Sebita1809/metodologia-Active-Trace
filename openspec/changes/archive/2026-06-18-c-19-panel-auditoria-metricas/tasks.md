# Tasks — C-19 Panel de auditoría y métricas de uso

> Governance ALTO: proponer y esperar revisión humana antes de escribir código.
> Sin migración: `audit_log` ya existe (C-05). Solo lectura. Strict TDD: test que falla → código mínimo → triangular → refactor.

## 1. Repositorio (queries de agregación y filtros sobre audit_log)

- [x] 1.1 Extender `AuditLogRepository` con `acciones_por_dia(*, desde, hasta, actor_ids=None)` agrupando por `date_trunc('day', fecha_hora)`, scoped por tenant
- [x] 1.2 Agregar `comunicaciones_por_docente(*, actor_ids=None)` que cuente acciones `COMUNICACION_*` agrupadas por `actor_id` y código de acción
- [x] 1.3 Agregar `interacciones_por_docente_materia(*, actor_ids=None)` agrupando por `actor_id` y `materia_id` (incluye clave "sin materia" para `materia_id` nulo)
- [x] 1.4 Agregar `ultimas_acciones(*, limit, actor_ids=None)` ordenado por `fecha_hora` desc con acotamiento del límite al máximo duro
- [x] 1.5 Extender `listar` (o agregar `listar_filtrado`) con filtros opcionales `desde`, `hasta`, `materia_id`, `accion`, `actor_ids`, manteniendo paginación y orden desc
- [x] 1.6 Verificar que ningún método nuevo expone mutación (preserva el contrato append-only de C-05)
- [x] 1.7 Garantizar que todas las queries filtran por `self._tenant_id` por defecto

## 2. Schemas (DTOs de respuesta, extra='forbid')

- [x] 2.1 `AccionesPorDiaItem` y respuesta de serie temporal (`dia`, `total`)
- [x] 2.2 `ComunicacionesPorDocenteItem` (`actor_id`, conteos por estado)
- [x] 2.3 `InteraccionesDocenteMateriaItem` (`actor_id`, `materia_id`, `total`)
- [x] 2.4 DTO de "últimas acciones" reutilizando/alineando con `AuditLogResponse` existente
- [x] 2.5 Schema de query/filtros del log completo (`desde`, `hasta`, `materia_id`, `usuario_id`, `accion`/`estado`, `limit`, `offset`)
- [x] 2.6 Confirmar `model_config = ConfigDict(extra='forbid')` en todos los DTOs

## 3. Service (lógica de negocio + enforcement de scope)

- [x] 3.1 Crear `AuditoriaService` orquestando repositorio + resolución de scope
- [x] 3.2 Implementar `resolver_equipo_coordinador(usuario_id)` a partir de `Asignacion` (C-07) → conjunto de `actor_id` del equipo
- [x] 3.3 Implementar resolución de `actor_ids` según alcance: `global` → None; `propio` → equipo del coordinador (fail-closed: equipo vacío → conjunto vacío)
- [x] 3.4 Centralizar el mapeo código `COMUNICACION_*` → estado (Pendiente/Enviando/Enviado/Fallido/Cancelado)
- [x] 3.5 Método `panel_acciones_por_dia(...)` aplicando scope
- [x] 3.6 Método `panel_comunicaciones_por_docente(...)` aplicando scope
- [x] 3.7 Método `panel_interacciones_docente_materia(...)` aplicando scope
- [x] 3.8 Método `panel_ultimas_acciones(limit=200)` aplicando scope y default 200
- [x] 3.9 Método `log_filtrado(...)` aplicando filtros + scope (intersección usuario_id con equipo en `propio`)

## 4. Router (`/api/v1/auditoria/*`)

- [x] 4.1 `GET /api/v1/auditoria/panel/acciones-por-dia` con `desde`/`hasta`, guard `auditoria:ver`
- [x] 4.2 `GET /api/v1/auditoria/panel/comunicaciones-por-docente` con guard `auditoria:ver`
- [x] 4.3 `GET /api/v1/auditoria/panel/interacciones-docente-materia` con guard `auditoria:ver`
- [x] 4.4 `GET /api/v1/auditoria/panel/ultimas-acciones` con `limit` (default 200), guard `auditoria:ver`
- [x] 4.5 `GET /api/v1/auditoria/log` con filtros (fechas, materia, usuario, acción/estado, paginación), guard `auditoria:ver`
- [x] 4.6 Resolver el alcance del permiso en el router y pasarlo al service (sin lógica de negocio en el router)
- [x] 4.7 Identidad y tenant siempre desde la sesión (`current_user`), nunca desde parámetros

## 5. Tests (sin mocks de DB; base/contenedor real)

- [x] 5.1 Acciones por día: conteo correcto dentro del rango y exclusión fuera del rango
- [x] 5.2 Estado de comunicaciones por docente: distribución por estado y exclusión de acciones no comunicacionales
- [x] 5.3 Interacciones por docente×materia: conteo por materia y clave "sin materia"
- [x] 5.4 Últimas N acciones: default 200, límite configurable respetado, acotamiento al máximo duro
- [x] 5.5 Log filtrado: rango de fechas, materia, usuario, acción y estado (cada filtro y combinaciones)
- [x] 5.6 Paginación del log (limit/offset, orden desc)
- [x] 5.7 Scope `propio` del COORDINADOR: solo equipo visible; equipo vacío → resultado vacío (fail-closed)
- [x] 5.8 Scope `propio`: filtro por `usuario_id` fuera del equipo → vacío
- [x] 5.9 Scope `global` (ADMIN/FINANZAS): ve todo el tenant
- [x] 5.10 Sin `auditoria:ver` → 403 en panel y log
- [x] 5.11 Aislamiento por tenant: un tenant no ve auditoría/agregaciones de otro
- [x] 5.12 Repositorio no expone update/delete (preserva append-only)
