## Context

C-15 implementa la Épica 3.5 (Tablón de avisos) sobre la base construida en C-06 (estructura académica, FK a materias/cohortes) y C-04 (RBAC/JWT). El dominio tiene dos entidades (E13: `Aviso`, `AcknowledgmentAviso`) con lógica de segmentación y un filtrado multi-criterio no trivial: el `GET /api/avisos/mis-avisos` debe cruzar el rol del JWT con el alcance del aviso, la cohorte del usuario y la ventana de vigencia. Governance MEDIO: lógica de dominio con filtrado multi-criterio.

## Goals / Non-Goals

**Goals:**
- Modelos `Aviso` y `AcknowledgmentAviso` con `tenant_id`, soft delete, timestamps.
- ABM de avisos con permiso `avisos:publicar` (COORDINADOR/ADMIN).
- Listado personalizado `mis-avisos` filtrado por audiencia + vigencia + ack.
- Acuse de recibo idempotente (UNIQUE `(aviso_id, usuario_id)`).
- Contadores derivados via query (no denormalizados).
- RBAC fail-closed: `avisos:publicar` y `avisos:ack`.

**Non-Goals:**
- Notificaciones push ni emails al publicar un aviso (eso es C-12).
- Frontend del tablón (C-22/C-23).
- Historial de ediciones de un aviso.
- Programación automática de publicación futura.

## Decisions

### D1 — Segmentación: filtro puro en SQL, no en memoria
El `AvisoRepository.listar_para_usuario(usuario_id, rol, cohorte_ids)` construye el filtro de audiencia como condiciones SQL (OR compuesto). Nunca carga todos los avisos del tenant para filtrar en Python — en instancias grandes sería costoso.
- Filtro: `alcance='Global' OR (alcance='PorRol' AND rol_destino=:rol) OR (alcance='PorCohorte' AND cohorte_id IN :cohortes) OR (alcance='PorMateria' AND materia_id IN :materias)`
- La vigencia: `inicio_en <= now() AND fin_en >= now()`.
- El ack: LEFT JOIN / NOT EXISTS sobre `acknowledgment_aviso WHERE usuario_id=:me`.
- *Alternativa descartada*: cargar en memoria. Inviable con decenas de avisos activos y miles de usuarios.

### D2 — UNIQUE constraint en acknowledgment: captura de IntegrityError
El par `(aviso_id, usuario_id)` tiene UNIQUE constraint en DB. El repository captura `IntegrityError` y lo convierte en `LookupError` (→ 409 en el router). No se hace SELECT previo (TOCTOU). La operación es idempotente a nivel de negocio: si ya existe, 409 indica que ya se acusó.
- *Alternativa descartada*: `INSERT OR IGNORE` / upsert. Devolvería 200 silencioso, perdiendo la semántica de "ya estaba acusado".

### D3 — Contadores derivados: query agregada en el repository, no campo en Aviso
`AcknowledgmentAvisoRepository.contar_acks(aviso_id)` retorna un `COUNT(*)`. La vista de administración llama a este método por aviso. No se denormaliza el conteo.
- *Alternativa descartada*: columna `total_acks` en `Aviso`. Introduce inconsistencia eventual ante borrados o rollbacks; viola la regla KB (E13: "contadores se derivan").

### D4 — Validación de audiencia en el acuse: en el Service
`AvisoService.acusar_recibo(aviso_id, current_user)` verifica que el aviso esté activo, vigente y dirigido al rol/cohorte/materia del usuario antes de crear el ack. Si no cumple → 403. Así el service contiene la lógica de audiencia, no el router.

### D5 — Validación de coherencia alcance+FK: en el Schema
`AvisoCreate` valora que si `alcance='PorMateria'` entonces `materia_id` es required y `cohorte_id` es None; si `alcance='PorCohorte'` entonces `cohorte_id` es required y `materia_id` es None; etc. Se implementa con `@model_validator` en Pydantic v2. Esto evita filas incoherentes en la DB.

### D6 — RBAC: dos permisos, fail-closed
- `avisos:publicar` → COORDINADOR/ADMIN: crear/modificar/borrar avisos.
- `avisos:ack` → todos los roles autenticados: acusar recibo (se asigna a todos los roles en el seed).

### D7 — `cohorte_ids` del JWT: inferencia desde usuario
Para filtrar `PorCohorte`, el service necesita saber en qué cohortes está el usuario. Se consulta `UsuarioRepository.get_cohortes_del_usuario(usuario_id, tenant_id)` al armar el filtro de `mis-avisos`. Si el usuario no tiene cohortes asociadas, ese segmento del filtro es vacío (no error).

## Risks / Trade-offs

- **Filtro multi-criterio complejo** → El OR compuesto puede ser lento sin índices adecuados. Mitigación: índices `(tenant_id, alcance)`, `(tenant_id, materia_id)`, `(tenant_id, cohorte_id)`.
- **Cohortes del usuario no disponibles en JWT** → El service consulta `UsuarioRepository` para obtenerlas. Añade una query por request; aceptable al ser una tabla pequeña por tenant.
- **Avisos globales con muchos acks** → El NOT EXISTS / LEFT JOIN puede ser costoso en tenants grandes. Mitigación: índice `(aviso_id, usuario_id)` en `acknowledgment_aviso`.

## Migration Plan

1. Migración única `013_avisos.py`:
   - Tabla `aviso`: columnas, CHECK constraints para `alcance` y `severidad`, índices `(tenant_id, alcance)`, `(tenant_id, materia_id)`, `(tenant_id, cohorte_id)`.
   - Tabla `acknowledgment_aviso`: UNIQUE `(aviso_id, usuario_id)`, índice `(tenant_id, aviso_id)`.
   - Seed RBAC: `avisos:publicar` (COORDINADOR/ADMIN), `avisos:ack` (todos los roles).
2. Rollback: `downgrade` elimina ambas tablas.

## Open Questions

- ¿`PorMateria` requiere que el usuario sea PROFESOR de esa materia, o alcanza con cualquier asignación en el tenant? Se asume: cualquier usuario del tenant con asignación activa a esa materia.
- ¿Los avisos `activo=False` pueden ser vistos por el publicador como borrador? Se asume que no se expone una vista de borradores en esta iteración; `activo=False` excluye el aviso de `mis-avisos` y del listado admin (filtro por defecto).
