# Diseño — C-19 Panel de auditoría y métricas de uso

## Contexto

`audit_log` ya existe (C-05) como tabla append-only con la siguiente forma relevante para C-19:

| columna | tipo | uso en C-19 |
|---------|------|-------------|
| `id` | UUID PK | identificador de fila en el log |
| `tenant_id` | UUID FK | aislamiento row-level (filtro obligatorio) |
| `fecha_hora` | timestamptz | agregación por día, filtro de rango |
| `actor_id` | UUID | agrupar por docente, scope del COORDINADOR |
| `impersonado_id` | UUID? | informativo en el log |
| `materia_id` | UUID? | agrupar/filtrar por materia |
| `accion` | str(100) | catálogo de códigos; filtro y clasificación de estado |
| `detalle` | JSONB? | contexto adicional (estado de comunicación, etc.) |
| `filas_afectadas` | int | métrica de volumen |
| `ip`, `user_agent` | str? | detalle del log de últimas acciones |

El repositorio `AuditLogRepository` (C-05) NO hereda de `BaseRepository` y expone solo `crear`, `listar`, `get`. C-19 **extiende** ese repositorio con métodos de agregación y filtros de lectura; **mantiene la inmutabilidad** (sigue sin exponer update/delete).

## Decisión 1 — Solo lectura, sin tablas ni migración

C-19 NO crea tablas ni migración Alembic. Toda la funcionalidad son queries de agregación y filtros sobre `audit_log`. El repositorio existente se amplía con métodos de lectura; el contrato append-only de C-05 se preserva. La capability `audit-log` (C-05) no se modifica: C-19 agrega dos capabilities nuevas (`panel-interacciones`, `log-auditoria`).

## Decisión 2 — Scope del COORDINADOR `(propio)` resuelto en el Service

El permiso `auditoria:ver` se concede con tres alcances efectivos:

- **ADMIN / FINANZAS → `global`**: ven toda la auditoría del tenant.
- **COORDINADOR → `propio`**: ve la actividad de **los docentes de su equipo**, NO solo sus propias acciones.

La semántica `propio` de C-05 (`actor_id == current_user`) es insuficiente para el panel de supervisión: un COORDINADOR supervisa a su equipo. C-19 redefine el enforcement de `propio` en el Service:

1. El Service obtiene el conjunto de `usuario_id` de los docentes del equipo del coordinador a partir de `Asignacion` (C-07): docentes (PROFESOR/TUTOR) cuyas materias/cohortes están bajo la responsabilidad del coordinador (asignaciones vigentes donde `responsable_id == coordinador` o que comparten `materia_id`/`cohorte_id` con las asignaciones de coordinación del usuario).
2. Las queries de panel y log filtran `actor_id IN (equipo)` cuando el alcance es `propio`.
3. Con alcance `global` no se aplica filtro de actor.

El cálculo del equipo vive en el Service (lógica de negocio), nunca en el Router ni en el Repository. El Repository recibe ya resuelta la lista de `actor_id` permitidos (o `None` para global).

> **Governance ALTO**: este enforcement de scope es seguridad. Se propone aquí y se implementa solo tras revisión humana. Fail-closed: sin `auditoria:ver` → 403; con `propio` y equipo vacío → resultado vacío, nunca todo el tenant.

## Decisión 3 — Agregaciones F9.1

Todas las agregaciones se ejecutan en SQL (no en memoria), scoped por `tenant_id` y, si aplica, por `actor_id IN (equipo)`:

- **Acciones por día**: `SELECT date(fecha_hora) AS dia, COUNT(*) FROM audit_log WHERE tenant_id=:t AND fecha_hora BETWEEN :desde AND :hasta [AND actor_id IN :equipo] GROUP BY dia ORDER BY dia`. La conversión a día usa `date_trunc('day', fecha_hora)` para respetar timezone-aware timestamps.
- **Estado de comunicaciones por docente**: los estados se derivan de los códigos `accion` de la familia `COMUNICACION_*` (p. ej. `COMUNICACION_ENVIAR` → enviado; estados Pendiente/Enviando/Fallido/Cancelado provienen del `accion` o del campo `detalle`). `GROUP BY actor_id, <estado>` con `COUNT(*)`. El mapeo código→estado se centraliza en una tabla de constantes en el Service.
- **Interacciones por docente × materia**: `GROUP BY actor_id, materia_id` con `COUNT(*)` (y opcionalmente `SUM(filas_afectadas)`). Filas con `materia_id IS NULL` se agrupan bajo una clave "sin materia".
- **Últimas N acciones**: `ORDER BY fecha_hora DESC LIMIT :n`, con `n` configurable y **default 200**, acotado por un máximo duro (p. ej. 1000) para proteger performance.

## Decisión 4 — Filtros del log completo F9.2

El log filtrado acepta parámetros opcionales y combinables:

- `desde` / `hasta` (rango de `fecha_hora`).
- `materia_id`.
- `usuario_id` (filtra `actor_id`; si el alcance es `propio`, se intersecta con el equipo — un coordinador no puede consultar un usuario fuera de su equipo).
- `accion` (código exacto del catálogo) y/o `estado` (familia de comunicación).
- Paginación `limit`/`offset` (defaults razonables, `limit` acotado).

El listado se ordena por `fecha_hora DESC`. Todos los filtros se construyen en el Repository como cláusulas `WHERE` componibles.

## Decisión 5 — Performance e índices

`audit_log` ya está indexado por `tenant_id` (C-05) y ordena por `fecha_hora`. Las agregaciones por día y por actor se apoyan en el filtro de `tenant_id` + rango de fechas. Si el volumen lo exige, se evaluará un índice compuesto `(tenant_id, fecha_hora)` y/o `(tenant_id, actor_id, fecha_hora)`; esto se documenta como nota de seguimiento y NO requiere migración en este change salvo confirmación explícita (el índice por `tenant_id` ya existe).

## Decisión 6 — Estructura de capas

```
Router  app/api/v1/routers/auditoria.py
  └─ declara require_permission("auditoria:ver"), resuelve alcance del permiso,
     pasa current_user + filtros al Service. Sin lógica de negocio.
Service app/services/auditoria_service.py
  └─ resuelve el equipo del coordinador (Asignacion), mapea códigos→estado,
     orquesta las agregaciones y aplica el scope. Sin acceso directo a DB.
Repo    app/repositories/audit_log.py
  └─ queries de agregación y filtros, siempre scoped por tenant_id.
     Mantiene append-only (no update/delete).
Schemas app/schemas/auditoria.py
  └─ DTOs de respuesta (extra='forbid') para panel y log.
```

## Riesgos / supuestos

- Se asume que el catálogo de `accion` incluye los códigos `COMUNICACION_*` necesarios para derivar estados (definido en C-05 / C-10). Si faltan códigos de estado intermedio (Enviando/Cancelado), el mapeo los deja en "desconocido" sin romper la agregación.
- El cálculo del equipo del coordinador depende del modelo de `Asignacion` (C-07); la definición exacta de "equipo" (por `responsable_id` vs. por materia/cohorte compartida) se confirma con el dominio antes de implementar.
