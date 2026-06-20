## Context

C-07 entregó la entidad `Usuario` con PII cifrada (AES-256-GCM) y su ABM administrativo bajo `/api/admin/usuarios` (permiso `usuarios:gestionar`). C-03 entregó auth JWT con `get_current_user` (identidad desde el token) y `POST /api/auth/logout`. C-12 entregó `Comunicacion`: cola de emails salientes hacia alumnos (externos).

Faltan dos piezas de la Épica 11 y la F3.4:
1. Que el propio usuario edite su ficha sin pasar por un ADMIN, con CUIL inmutable.
2. Una bandeja de mensajes **interna** entre usuarios registrados, distinta de los emails a alumnos (FL-10 lo declara explícitamente paralelo).

Restricciones del proyecto: arquitectura Routers → Services → Repositories → Models; identidad siempre desde JWT; multi-tenancy row-level (`tenant_id` en cada tabla, filtrado por defecto en repositories); PII cifrada con `CryptoService`; Pydantic `extra='forbid'`; soft delete; tests sin mocks de DB; ≤500 LOC por archivo.

El modelo `Usuario` actual NO tiene los campos `sexo` ni `modalidad_cobro` que F11.1 lista como editables. Hay que agregarlos.

## Goals / Non-Goals

**Goals:**
- Endpoint de autogestión de perfil (`/api/perfil`) que reuse `UsuarioService`/`UsuarioRepository` existentes, resolviendo el `usuario_id` desde el JWT.
- Garantizar que `cuil` sea inmutable vía `/api/perfil` (el schema de update no lo acepta; sigue editable solo por el ABM admin).
- Entidad `Mensaje` con hilos entre usuarios del mismo tenant, con endpoints de inbox: listar hilos recibidos, ver hilo, responder.
- Aislamiento estricto: un usuario solo ve los hilos donde es destinatario (o participante) dentro de su tenant.
- Reutilizar el logout de C-03 para F11.3 (sin código nuevo).

**Non-Goals:**
- No se construye UI/frontend (solo API).
- No se toca la cola de emails a alumnos (`Comunicacion`, C-12).
- No se implementa borrado de mensajes, archivado, ni notificaciones push/email del inbox (fuera de scope de F3.4/FL-10).
- No se agrega permiso RBAC nuevo: el perfil propio y el inbox son accesibles por cualquier usuario autenticado (identidad desde JWT, no `require_permission` de módulo).

## Decisions

### D1 — `/api/perfil` reutiliza UsuarioService, resolviendo el id desde el JWT
`PerfilService` (o el router de perfil) obtiene `current_user.user_id` del JWT y delega en `UsuarioService.get(user_id)` / `UsuarioService.update(user_id, ...)`. No se acepta ningún `usuario_id` por path/body. Alternativa descartada: duplicar lógica de cifrado en un service nuevo → viola DRY y arriesga inconsistencias de cifrado de PII.

### D2 — CUIL inmutable por schema, no por lógica condicional
El schema `PerfilUpdate` (Pydantic, `extra='forbid'`) simplemente NO declara el campo `cuil`. Cualquier intento de enviarlo produce 422 (campo no permitido). Esto es fail-closed y declarativo, sin ramas `if`. El `cuil` se expone en `PerfilResponse` como solo lectura. El ABM admin (C-07) conserva la capacidad de editar `cuil` con `usuarios:gestionar`.

### D3 — Nueva entidad `Mensaje` con hilo por `thread_id`, separada de `Comunicacion`
`Mensaje` modela mensajería interna usuario↔usuario; `Comunicacion` modela emails salientes a alumnos. Son dominios distintos (FL-10) → tablas separadas. Estructura de `Mensaje`:
- `tenant_id`, `thread_id` (UUID que agrupa el hilo), `remitente_id` (FK usuarios, siempre del JWT), `destinatario_id` (FK usuarios), `asunto` (solo en el mensaje raíz del hilo, nullable en respuestas), `cuerpo` (texto), `leido_at` (nullable; marcado al abrir), `creado_at` (server-side).
- El primer mensaje de un hilo genera un `thread_id` nuevo; una respuesta reusa el `thread_id` del mensaje al que responde e invierte remitente/destinatario.
Alternativa descartada: tabla `Thread` + `Mensaje` separadas → sobre-ingeniería para el alcance de F3.4 (un hilo es solo un `thread_id` compartido entre dos usuarios).

### D4 — Aislamiento del inbox por destinatario + tenant en el repository
`MensajeRepository` hereda el filtro por `tenant_id` de `BaseRepository`. Los métodos de inbox filtran además por `destinatario_id = current_user.user_id` (hilos recibidos) o por participación en el hilo (`remitente_id` o `destinatario_id` = usuario actual) para la vista de hilo. Un usuario nunca puede leer un hilo en el que no participa → 404.

### D5 — Responder valida pertenencia al hilo antes de insertar
Al responder, el service verifica que el `thread_id` exista y que el usuario actual sea participante del hilo (remitente o destinatario de algún mensaje del hilo). El nuevo mensaje fija `remitente_id` desde el JWT y `destinatario_id` = el otro participante del hilo. El `asunto` se hereda del hilo (no se reenvía desde el cliente).

### D6 — `modalidad_cobro` como enum nullable; `sexo` como texto libre nullable
`modalidad_cobro` ∈ {`Factura`, `Liquidacion`} (consistente con el dominio de liquidaciones C-18 / `facturador`). `sexo` se modela como texto corto nullable (el dominio no fija un enum cerrado). Ambos son aditivos y nullable → la migración no rompe filas existentes.

### D7 — Logout (F11.3) sin código nuevo
F11.3 se satisface con `POST /api/auth/logout` de C-03 (revoca el refresh token). La tarea correspondiente es un test de integración que confirma el flujo, no nueva implementación.

## Risks / Trade-offs

- **[El cliente intenta editar CUIL por `/api/perfil`]** → Mitigación: `extra='forbid'` en `PerfilUpdate` rechaza el campo con 422; test explícito de "CUIL no modificable".
- **[Fuga de hilos entre usuarios o tenants]** → Mitigación: filtro de tenant heredado + filtro de participación en cada query del inbox; tests de aislamiento por usuario y por tenant.
- **[`thread_id` falsificado en respuesta para inyectar mensaje en hilo ajeno]** → Mitigación: el service valida participación en el hilo antes de insertar (D5); responder a un hilo inexistente o ajeno → 404.
- **[Migración sobre tabla core `usuarios`]** → Mitigación: columnas aditivas nullable, sin defaults destructivos; una sola migración Alembic; no altera el contrato del ABM admin.
- **[PII en mensajes]** → El cuerpo de los mensajes internos es texto operativo entre usuarios; no se cifra (no es PII estructurada como CBU/DNI). Se documenta como decisión: el inbox interno no almacena PII sensible en el sentido de C-07.

## Migration Plan

1. Crear migración Alembic: `ALTER TABLE usuarios ADD COLUMN sexo VARCHAR(50) NULL, ADD COLUMN modalidad_cobro VARCHAR(20) NULL` + `CREATE TABLE mensajes (...)` con FKs a `usuarios` e índice por `(tenant_id, thread_id)` y `(tenant_id, destinatario_id)`.
2. Desplegar backend con los nuevos routers registrados.
3. Rollback: `downgrade` revierte ambas columnas y dropea `mensajes`; sin pérdida de datos preexistentes (columnas nullable, tabla nueva).

## Open Questions

- Ninguna bloqueante. El alcance de F3.4/FL-10 es deliberadamente acotado (recibir/leer/responder). Funcionalidad futura (búsqueda, archivado, adjuntos) queda fuera de esta change.
