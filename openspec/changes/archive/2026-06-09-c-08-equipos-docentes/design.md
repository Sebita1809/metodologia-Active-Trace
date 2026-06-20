## Context

C-07 entregó el modelo `Asignacion`, su repositorio base y los endpoints CRUD en `/api/asignaciones`. C-08 construye sobre esa base para agregar las operaciones de gestión de equipos docentes del Épica 4: la vista del propio docente (mis-equipos), las operaciones en bloque del coordinador (masiva, clonar, vigencia) y la exportación.

El modelo de datos no cambia — todo el comportamiento nuevo es lógica de servicio sobre registros `Asignacion` ya existentes. No hay migraciones de schema en este change.

**Estado actual**: `Asignacion` tiene CRUD básico y filtros por materia/carrera/cohorte/usuario/rol/responsable. Faltan las operaciones de negocio de alto nivel.

**Constraints**:
- Governance ALTO: implementar con checkpoints; operaciones de escritura en bloque generan audit trail (`ASIGNACION_MODIFICAR`).
- Multi-tenancy: todas las queries filtran por `tenant_id` del JWT; no existen cruzamientos entre tenants.
- TDD estricto: test que falla → código mínimo → triangulación → refactor.
- ≤500 LOC por archivo backend.

## Goals / Non-Goals

**Goals:**
- Vista `GET /api/equipos/mis-equipos` para el propio docente (F4.2) con filtros.
- Gestión de asignaciones individuales para COORDINADOR/ADMIN (F4.3) — puede reutilizar `/api/asignaciones` de C-07 o agregar aliases bajo `/api/equipos/`.
- `POST /api/equipos/asignaciones/masiva`: asignación en bloque con autocomplete de usuarios (F4.4, RN-30).
- `POST /api/equipos/asignaciones/clonar`: duplica asignaciones vigentes de origen → destino con nuevas fechas (F4.5, RN-12).
- `PATCH /api/equipos/asignaciones/vigencia`: actualiza `desde`/`hasta` en bloque para un equipo (F4.6).
- `GET /api/equipos/asignaciones/exportar`: descarga CSV con detalle del equipo (F4.7).
- Auditoría `ASIGNACION_MODIFICAR` en todas las operaciones de escritura.

**Non-Goals:**
- Cambios al esquema de base de datos (no hay migración).
- Gestión de permisos RBAC (eso vive en C-04).
- Importación de padrón (C-09) ni calificaciones (C-10).
- Frontend de equipos (C-23).

## Decisions

### D-01 — Router separado `/api/equipos/` vs extender `/api/asignaciones/`

**Decisión**: nuevo router `equipos.py` bajo `/api/equipos/`, dejando `/api/asignaciones` de C-07 intacto.

**Razón**: las operaciones de equipos tienen semántica distinta al CRUD de asignaciones (operaciones en bloque, vista "mis equipos"), y mezclarlas en el mismo router supera las 500 LOC. El cliente distingue claramente la gestión individual (C-07) de las operaciones de equipo (C-08).

**Alternativa descartada**: extender el router `asignaciones.py` con rutas adicionales — supera el límite de LOC y mezcla responsabilidades.

---

### D-02 — `mis-equipos` devuelve las asignaciones del JWT, con `estado_vigencia` derivado

**Decisión**: `GET /api/equipos/mis-equipos` filtra `Asignacion` por `usuario_id = current_user.id` y `tenant_id = current_user.tenant_id`. Incluye asignaciones vigentes y vencidas (la UI filtra por defecto a vigentes pero puede pedir todas). El campo `estado_vigencia` se computa en el service, nunca se almacena.

**Razón**: la identidad viene SIEMPRE del JWT (regla de oro). No existe parámetro en la URL que permita ver equipos de otro usuario.

---

### D-03 — Clonar equipo es una operación transaccional en service

**Decisión**: `clone_equipo` en `EquipoService` recibe `(origen: CohorteEquipoRef, destino: CohorteEquipoRef, desde: date, hasta: date | None)`. Lee todas las asignaciones vigentes del origen, las duplica con el nuevo contexto de cohorte y las fechas indicadas, y las persiste en una única transacción. Si alguna falla, hace rollback completo.

**Razón**: RN-12 define el clonado como una operación atómica. Fallo parcial dejaría el equipo destino incompleto.

**Alternativa descartada**: bulk insert sin transacción — genera estado inconsistente ante fallos.

---

### D-04 — Asignación masiva con búsqueda de usuarios por autocompletado en servidor

**Decisión**: `GET /api/equipos/usuarios/buscar?q=<texto>` retorna lista paginada de usuarios del tenant que coinciden con nombre/apellido/email (desencriptando el email solo para comparar, devolviendo nombre/apellido). El endpoint de asignación masiva recibe la lista de `usuario_id` ya seleccionados.

**Razón**: RN-30 exige autocompletado asistido por el servidor. La búsqueda debe operar sobre datos cifrados (email) — se busca por nombre/apellido solo a nivel DB, y el email se usa para mostrar al coordinador al seleccionar.

**Alternativa descartada**: enviar la lista completa de usuarios al frontend — no escala con tenants de cientos de docentes y expone PII innecesariamente.

---

### D-05 — Exportación como CSV con streaming response

**Decisión**: `GET /api/equipos/asignaciones/exportar` genera un `StreamingResponse` con `Content-Type: text/csv`. No genera archivos temporales en disco; los datos se serializan fila a fila desde el cursor de DB.

**Razón**: volumen manejable (<10K filas típicas), sin overhead de archivo temporal, y compatible con proxies sin buffering.

---

### D-06 — Auditoría en el service, no en el router

**Decisión**: las llamadas a `audit_service.log(AccionAuditoria.ASIGNACION_MODIFICAR, ...)` viven dentro de `EquipoService`, no en el router. El router solo resuelve identidad y delega.

**Razón**: la lógica de auditoría es parte de la regla de negocio, no de la presentación HTTP. El service es quien conoce cuántos registros fueron afectados.

## Risks / Trade-offs

- **[Riesgo] Clonado de equipo grande en un solo commit** → en tenants con 100+ asignaciones por equipo, el bulk insert puede tardar. Mitigación: la operación es síncrona pero rápida (<100ms esperado); si el volumen crece se puede pasar a un worker background en C-12.
- **[Trade-off] Exportación sin paginación** → para exportaciones de equipos muy grandes, el streaming puede mantener la conexión abierta mucho tiempo. Aceptable para los volúmenes actuales.
- **[Riesgo] Race condition en asignación masiva** → dos coordinadores asignando al mismo docente en simultáneo. Mitigación: la unicidad no está forzada a nivel DB en asignaciones (un docente puede tener varios roles); el sistema acepta duplicados y los muestra en el histórico. Riesgo bajo.
- **[Riesgo] Autocompletado de usuarios sobre email cifrado** → la búsqueda solo opera sobre `nombre`/`apellidos` (no cifrado). Si el coordinador busca por email, no puede. Mitigación: buscar por nombre/apellido es suficiente para el caso de uso. El email se muestra en el resultado para confirmar identidad.

## Migration Plan

No hay migración de schema. El deploy es:
1. Merge a main con los nuevos routers y servicios.
2. Reiniciar la API.
3. No requiere rollback especial — los endpoints nuevos son aditivos.

## Open Questions

- **OQ-1**: ¿El endpoint de exportación debe soportar filtros (por materia/cohorte) o exporta el equipo completo del tenant? → Asumido: acepta parámetros opcionales de filtro (mismos que el listado) para exportar subconjuntos.
- **OQ-2**: ¿El clonar equipo debe verificar que las asignaciones del destino no existan previamente? → Asumido: no verifica, permite clonar sobre un equipo destino ya parcialmente configurado (útil para completar gaps). Documentar en la respuesta cuántas asignaciones fueron creadas.
