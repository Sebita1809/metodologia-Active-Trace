## Why

El sistema carece de un canal institucional para que COORDINADOR y ADMIN comuniquen novedades segmentadas a grupos de usuarios (por materia, cohorte o rol), con control de vigencia temporal y trazabilidad de lectura (acuse de recibo). Sin este tablón los coordinadores no tienen forma de anunciar cambios de fechas, cortes de liquidaciones ni comunicados urgentes fuera del email externo.

## What Changes

- Modelo `Aviso` (E13): alcance `Global|PorMateria|PorCohorte|PorRol`, `materia_id`/`cohorte_id`/`rol_destino` nullable según alcance, `severidad`, `titulo`, `cuerpo`, ventana de vigencia (`inicio_en`/`fin_en`), `orden`, `activo`, `requiere_ack`, `deleted_at`, timestamps multi-tenant.
- Modelo `AcknowledgmentAviso`: `aviso_id`, `usuario_id`, `confirmado_at`; contadores derivados (no denormalizados).
- ABM de avisos vía `POST/PATCH/DELETE /api/avisos/` con permiso `avisos:publicar` (COORDINADOR/ADMIN).
- Listado personalizado `GET /api/avisos/mis-avisos` — filtra por rol, alcance, cohorte y ventana de vigencia del usuario autenticado.
- Acuse de recibo `POST /api/avisos/{id}/ack` — permiso `avisos:ack` (cualquier rol destinatario).
- Migración `013_avisos.py`: tablas `aviso`, `acknowledgment_aviso`, índices y seed RBAC.
- Tests: filtrado por scope, ventana de vigencia, ack que oculta aviso, orden de prioridad.

## Capabilities

### New Capabilities
- `aviso`: gestión y visualización de avisos institucionales segmentados (ABM, filtrado por audiencia, ventana de vigencia).
- `acknowledgment-aviso`: confirmación de lectura de avisos; contadores derivados sin denormalización.

### Modified Capabilities
<!-- No se modifica ninguna capability existente -->

## Impact

- **Nuevos archivos**: `models/aviso.py`, `models/acknowledgment_aviso.py`, `repositories/aviso_repository.py`, `repositories/acknowledgment_aviso_repository.py`, `services/aviso_service.py`, `api/v1/routers/avisos.py`, `schemas/avisos.py`.
- **Migración**: `013_avisos.py` — crea `aviso` y `acknowledgment_aviso`; UNIQUE `(aviso_id, usuario_id)` en ack; índices `(tenant_id, alcance)`, `(tenant_id, materia_id)`, `(tenant_id, cohorte_id)`.
- **main.py**: registrar `avisos_router`.
- **Dependencia**: C-06 (estructura académica, FK a `materias`/`cohortes`). Sin dependencia directa de C-07 (usuarios se consultan por FK en JWT, no se crea ningún join con la tabla de usuarios).
