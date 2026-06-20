## 1. Modelo y migración

- [x] 1.1 Agregar columnas `sexo` (String(50), nullable) y `modalidad_cobro` (String(20), nullable) a `app/models/usuario.py`, documentando que `modalidad_cobro` ∈ {Factura, Liquidacion}
- [x] 1.2 Crear `app/models/mensaje.py`: entidad `Mensaje` (BaseTenantModel) con `thread_id` (UUID), `remitente_id` (FK usuarios RESTRICT), `destinatario_id` (FK usuarios RESTRICT), `asunto` (Text nullable), `cuerpo` (Text), `leido_at` (DateTime tz nullable), `creado_at` (server_default func.now()); `__repr__` sin exponer cuerpo
- [x] 1.3 Registrar `Mensaje` en `app/models/__init__.py`
- [x] 1.4 Crear una única migración Alembic: ADD COLUMN `sexo`/`modalidad_cobro` en `usuarios` + CREATE TABLE `mensajes` con índices `(tenant_id, thread_id)` y `(tenant_id, destinatario_id)`; verificar `downgrade` reversible

## 2. Perfil propio — repository/service

- [x] 2.1 (TDD) Test: `UsuarioService.update` cifra y persiste `sexo` y `modalidad_cobro` correctamente
- [x] 2.2 Extender `UsuarioService.create`/`update` y `UsuarioDecifrado` con `sexo` y `modalidad_cobro`
- [x] 2.3 Crear `app/services/perfil_service.py` (o helper en el router) que resuelva `usuario_id` desde el JWT y delegue en `UsuarioService` para leer/editar el perfil propio (sin aceptar id desde la petición)

## 3. Perfil propio — schemas y router

- [x] 3.1 (TDD) Test: `PerfilUpdate` (Pydantic, extra='forbid') rechaza el campo `cuil` con error de validación
- [x] 3.2 Crear `app/schemas/perfil.py`: `PerfilResponse` (incluye `cuil` descifrado, sin `email_hash`) y `PerfilUpdate` (campos editables: nombre, apellidos, email, sexo, banco, cbu, alias_cbu, regional, legajo_profesional, modalidad_cobro; SIN `cuil`; `extra='forbid'`)
- [x] 3.3 Crear `app/api/v1/routers/perfil.py`: `GET /api/perfil` y `PATCH /api/perfil` usando `get_current_user`; sin lógica de negocio en el router
- [x] 3.4 Registrar el router de perfil en `app/api/v1/__init__.py`

## 4. Perfil propio — tests de integración

- [x] 4.1 Test: `GET /api/perfil` retorna la ficha del usuario del JWT con PII descifrada y sin `email_hash`
- [x] 4.2 Test: `GET /api/perfil` sin token → 401
- [x] 4.3 Test: `PATCH /api/perfil` actualiza cbu/alias_cbu/modalidad_cobro y persiste cifrado
- [x] 4.4 Test: `PATCH /api/perfil` con campo `cuil` → 422 (CUIL no modificable) y CUIL sin cambios
- [x] 4.5 Test: aislamiento — el perfil resuelto pertenece al tenant del JWT; no se puede afectar a otro usuario/tenant
- [x] 4.6 Test (F11.3): `POST /api/auth/logout` revoca el refresh token y un refresh posterior con ese token → 401

## 5. Mensajería interna — repository

- [x] 5.1 Crear `app/repositories/mensaje_repository.py` (BaseRepository[Mensaje], tenant isolation heredada)
- [x] 5.2 (TDD) Test: `list_inbox(destinatario_id)` retorna solo hilos donde el usuario es destinatario, agrupados por `thread_id`, dentro del tenant
- [x] 5.3 Implementar `list_inbox`, `get_thread(thread_id)` (mensajes ordenados por `creado_at` asc), `is_participant(thread_id, user_id)` y `mark_thread_read(thread_id, user_id)`

## 6. Mensajería interna — service

- [x] 6.1 (TDD) Test: enviar mensaje fija `remitente_id` desde el JWT e ignora cualquier remitente del body; genera `thread_id` nuevo en el mensaje raíz
- [x] 6.2 (TDD) Test: responder en hilo ajeno o inexistente → error que el router traduce a 404; el asunto se hereda del hilo
- [x] 6.3 Crear `app/services/mensaje_service.py`: `enviar`, `listar_inbox`, `leer_hilo` (marca leídos los recibidos), `responder` (valida participación, fija remitente desde JWT, destinatario = otro participante, hereda asunto)

## 7. Mensajería interna — schemas y router

- [x] 7.1 Crear `app/schemas/mensaje.py`: `MensajeCreate`, `MensajeResponse`, `ThreadResponse`, `RespuestaCreate` (sin `asunto` ni `remitente_id`); `extra='forbid'`
- [x] 7.2 Crear `app/api/v1/routers/inbox.py`: `GET /api/inbox`, `GET /api/inbox/{thread_id}`, `POST /api/inbox/{thread_id}/responder` (y, si aplica, endpoint de envío inicial), usando `get_current_user`; sin lógica de negocio en el router
- [x] 7.3 Registrar el router de inbox en `app/api/v1/__init__.py`

## 8. Mensajería interna — tests de integración y aislamiento

- [x] 8.1 Test: `GET /api/inbox` lista solo hilos donde el usuario es destinatario; no muestra hilos ajenos
- [x] 8.2 Test: `GET /api/inbox/{thread_id}` de participante → 200 con mensajes ordenados; abrir marca `leido_at` en los recibidos
- [x] 8.3 Test: `GET /api/inbox/{thread_id}` de no participante → 404; hilo de otro tenant → 404
- [x] 8.4 Test: `POST /api/inbox/{thread_id}/responder` de participante → 201, respuesta en el mismo hilo con asunto heredado
- [x] 8.5 Test: responder a hilo ajeno o de otro tenant → 404, sin crear mensaje
- [x] 8.6 Test: `GET /api/inbox` sin token → 401

## 9. Cierre

- [x] 9.1 Verificar cobertura ≥80% líneas y ≥90% en reglas de negocio (CUIL inmutable, aislamiento de hilos, remitente desde JWT)
- [x] 9.2 Marcar `[x]` C-20 en `CHANGES.md`
