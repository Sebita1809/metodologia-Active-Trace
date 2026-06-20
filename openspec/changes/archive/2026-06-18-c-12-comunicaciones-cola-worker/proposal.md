## Why

Con C-11 el sistema ya identifica quién está atrasado, pero no puede actuar sobre esa información: no hay forma de comunicarse con los alumnos. Este change cierra el lazo importar → analizar → **comunicar**, que es el flujo de mayor valor del producto. Introduce la cola de comunicaciones con worker asíncrono, preview obligatorio (RN-16), aprobación administrativa de envíos masivos (RN-17) y el ciclo de vida de estados de cada mensaje (RN-15), todo multi-tenant y auditado.

## What Changes

- Nuevo modelo `Comunicacion` (E21) con máquina de estados `Pendiente → Enviando → Enviado | Error | Cancelado`, agrupación por `lote_id` y `destinatario` (email) cifrado AES-256
- Nueva migración Alembic para la tabla `comunicacion` (índices `(tenant_id, lote_id)` y `(tenant_id, estado)`)
- Nuevo `ComunicacionRepository` con scope de tenant por defecto y transiciones de estado
- Nuevo `ComunicacionService` con: preview con sustitución de variables (RN-16), encolado de lote, transiciones de estado válidas (RN-15), aprobación/cancelación de lote o por destinatario (RN-17)
- Nuevo worker asíncrono independiente en `workers/` que procesa la cola `Pendiente → Enviando → Enviado/Error`; respeta la aprobación humana configurable por tenant; sus errores no rompen el flujo principal
- Nuevos endpoints bajo `/api/v1/comunicaciones`: preview, encolar lote, listar cola, aprobar lote/destinatario, cancelar, tracking de estado
- Permisos `comunicacion:enviar` (PROFESOR, COORDINADOR, ADMIN) y `comunicacion:aprobar` (COORDINADOR, ADMIN)
- Código de auditoría `COMUNICACION_ENVIAR` emitido al confirmar un envío

## Capabilities

### New Capabilities

- `comunicaciones`: Modelo `Comunicacion`, repository, servicio de preview/encolado/aprobación y los endpoints REST. Cubre el ciclo de vida de estados (RN-15), preview obligatorio con variables de sustitución (RN-16), aprobación administrativa de envíos masivos (RN-17) y el tracking de estado por mensaje y por lote.
- `comunicaciones-worker`: Worker asíncrono independiente que consume la cola de comunicaciones `Pendiente`, las transiciona a `Enviando` y despacha al canal de envío externo resolviendo a `Enviado` o `Error`. Respeta la aprobación humana configurable por tenant y aísla sus fallos del flujo HTTP principal.

### Modified Capabilities

<!-- Ninguna: C-12 no modifica requisitos de specs existentes. -->

## Impact

- **Archivos nuevos**: `backend/app/models/comunicacion.py`, `backend/alembic/versions/0XX_comunicacion.py`, `backend/app/repositories/comunicacion_repository.py`, `backend/app/services/comunicacion_service.py`, `backend/app/schemas/comunicacion.py`, `backend/app/api/v1/routers/comunicaciones.py`, `backend/app/workers/comunicacion_worker.py`, `backend/app/workers/__init__.py`
- **Archivos modificados**: `backend/app/services/audit_codes.py` (`COMUNICACION_ENVIAR`), `backend/app/services/rbac_seed.py` (permisos `comunicacion:enviar`, `comunicacion:aprobar`), `backend/app/models/__init__.py` (registro del modelo), `backend/app/main.py` (registro del router)
- **Dependencias usadas**: `BaseRepository` + tenant scope (C-02), `CryptoService` AES-256-GCM (C-02), `require_permission` (C-04), `get_current_user` (C-03), `AuditLog` helper (C-05), FKs a `Materia` (C-06) y `Usuario` (C-07)
- **Canal de envío externo**: el despacho real (SMTP / API N8N) se abstrae detrás de una interfaz de canal; el worker mockea ese canal en tests (nunca la DB)
- **Cierra**: el camino crítico importar → analizar → comunicar en producción multi-tenant
