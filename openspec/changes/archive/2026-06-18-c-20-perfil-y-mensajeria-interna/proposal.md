## Why

Hoy todo cambio sobre la ficha de un Usuario pasa por el ABM administrativo (`/api/admin/usuarios`, permiso `usuarios:gestionar`), por lo que un docente no puede mantener sus propios datos fiscales/bancarios sin intervención de un ADMIN. Además, la comunicación interna entre usuarios registrados (avisos personalizados de coordinación, respuestas de alumnos) no tiene canal propio: solo existe la cola de emails salientes a alumnos (C-12). Esta change cierra la Épica 11 (Perfil y Sesión) y la mensajería interna de la Épica 3 (F3.4), habilitando autogestión del perfil y una bandeja de mensajes por hilo entre usuarios.

## What Changes

- **Perfil propio (F11.1)**: nuevo endpoint `GET /api/perfil` y `PATCH /api/perfil` para que cualquier usuario autenticado lea y edite su propia ficha. Campos editables: nombre, apellidos, datos fiscales/bancarios (CUIT/CUIL fiscal de facturación, banco, CBU, alias), regional, sexo, email, matrícula profesional y modalidad de cobro (factura / liquidación). El `cuil` (identificador tributario principal) es **solo lectura** desde este endpoint. La identidad se resuelve siempre desde el JWT — el usuario solo puede editarse a sí mismo.
- **Modelo Usuario ampliado**: se agregan dos columnas para cubrir F11.1: `sexo` (plaintext, nullable) y `modalidad_cobro` (enum `Factura` | `Liquidacion`, nullable). Migración Alembic única.
- **Mensajería interna (F3.4, F11.2, FL-10)**: nueva entidad `Mensaje` con hilos (`thread_id`) entre usuarios del tenant, paralela y distinta de `Comunicacion` (emails a alumnos, C-12). Endpoints bajo `/api/inbox/*`: listar hilos recibidos, ver un hilo, responder dentro del hilo. Aislamiento por usuario y por tenant.
- **Cierre de sesión (F11.3)**: se reutiliza el logout existente de C-03 (`POST /api/auth/logout`). No se crea lógica nueva; se documenta como criterio de aceptación.

## Capabilities

### New Capabilities
- `perfil-propio`: autogestión de la ficha del propio usuario autenticado (lectura y edición de campos editables; CUIL de solo lectura; identidad desde JWT).
- `mensajeria-interna`: bandeja de mensajes interna entre usuarios registrados del tenant, organizada por hilos (recibir, leer, responder), aislada por usuario y tenant.

### Modified Capabilities
- `usuario`: se añaden los atributos editables `sexo` y `modalidad_cobro` a la entidad `Usuario`, y se establece que el `cuil` es inmutable desde la autogestión de perfil (sigue siendo editable solo por el ABM administrativo con `usuarios:gestionar`).

## Impact

- **Backend nuevo**: `app/models/mensaje.py`, `app/repositories/mensaje_repository.py`, `app/services/mensaje_service.py`, `app/services/perfil_service.py`, `app/api/v1/routers/perfil.py`, `app/api/v1/routers/inbox.py`, schemas Pydantic (`app/schemas/perfil.py`, `app/schemas/mensaje.py`), una migración Alembic (columnas `sexo`, `modalidad_cobro` en `usuarios` + tabla `mensajes`).
- **Backend modificado**: `app/models/usuario.py` (dos columnas nuevas), registro de routers en `app/api/v1/__init__.py`.
- **Auth**: reutiliza `get_current_user` (C-03) y `POST /api/auth/logout` (C-03) sin cambios.
- **Sin impacto** en C-12 comunicaciones (la mensajería interna es una entidad separada) ni en el ABM administrativo de usuarios (C-07), que conserva su contrato.
- **Governance**: BAJO (autogestión + CRUD de mensajería); las columnas tocan core-model `Usuario` pero de forma aditiva y no rompen el contrato existente.
