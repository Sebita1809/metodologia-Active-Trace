# C-19 — Panel de auditoría y métricas de uso

## Why

El sistema ya persiste cada acción significativa en `audit_log` (append-only, scoped por tenant) desde **C-05**. Esa información hoy solo se expone como un listado plano (`GET /api/auditoria/`). Falta la capa de **supervisión**: COORDINADOR y ADMIN necesitan ver el uso del sistema de forma agregada para detectar docentes inactivos, comunicaciones fallidas y patrones de actividad por materia.

Las funcionalidades **F9.1 (panel de interacciones)** y **F9.2 (log completo de auditoría con filtros)** cubren el flujo **FL-11** (auditoría de actividad por docente). Ambas son de **solo lectura** sobre `audit_log`: no introducen nuevas tablas ni mutan datos. Reglas asociadas: **RN-23** (toda acción significativa se audita) y **RN-24** (inmutabilidad del log).

## What Changes

- **Panel de interacciones (F9.1)** — agregaciones de solo lectura sobre `audit_log`:
  - Acciones por día en un rango de fechas (serie temporal de volumen de uso).
  - Estado de comunicaciones por docente (distribución Pendiente / Enviando / OK / Fallido / Cancelado a partir de códigos `COMUNICACION_*`).
  - Interacciones por docente × materia (conteo por `actor_id` × `materia_id`).
  - Log de últimas N acciones (máximo configurable; por defecto **200**).
- **Log completo de auditoría (F9.2)** — listado paginado con filtros: rango de fechas (`desde`/`hasta`), `materia_id`, `usuario_id` y `accion`/estado.
- **Endpoints `/api/v1/auditoria/*`** protegidos con `auditoria:ver` (ADMIN y FINANZAS alcance `global`; COORDINADOR alcance `propio`).
- **Scope `(propio)` del COORDINADOR**: el COORDINADOR ve únicamente la actividad de los docentes de su equipo (resuelto vía `Asignacion` de C-07), no solo sus propias acciones. ADMIN y FINANZAS ven todo el tenant.
- **Sin migración**: `audit_log` ya existe (C-05). Solo se agregan queries de agregación y filtros al repositorio existente, nuevos schemas de respuesta, un service de métricas y rutas en el router de auditoría.

## Capabilities

- `panel-interacciones` — agregaciones F9.1 (acciones/día, estado de comunicaciones por docente, interacciones docente×materia, últimas N acciones) con scope del COORDINADOR.
- `log-auditoria` — log completo F9.2 con paginación, filtros (fechas, materia, usuario, acción/estado), scope del COORDINADOR y aislamiento por tenant.

## Impact

- **Dominio**: auditoría (Épica 9). Governance **ALTO** — propuesta primero, código solo tras revisión humana.
- **Dependencias**: C-05 (audit-log, tabla y repositorio base), C-07 (equipos/asignaciones, para el scope `propio` del COORDINADOR).
- **Backend**:
  - `backend/app/repositories/audit_log.py` — nuevos métodos de agregación y filtros (extiende el repo existente; sigue sin exponer mutación).
  - `backend/app/schemas/auditoria.py` — DTOs de respuesta para panel y log.
  - `backend/app/services/auditoria_service.py` — lógica de agregación y enforcement de scope.
  - `backend/app/api/v1/routers/auditoria.py` — nuevas rutas de panel y log filtrado.
- **Sin nuevas tablas, sin migración Alembic.** `audit_log` ya está indexado por `tenant_id` + `fecha_hora` (C-05); las agregaciones se apoyan en esos índices.
- **No modifica specs existentes**: C-19 es puramente aditivo y de solo lectura sobre la capability `audit-log`.
