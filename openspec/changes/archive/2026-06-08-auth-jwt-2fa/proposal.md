## Why

El sistema tiene cimientos (C-01: scaffold, C-02: multi-tenancy + modelos base) pero ninguna capa de identidad: cualquier endpoint puede llamarse sin autenticar. C-03 cierra esa brecha estableciendo la sesión autenticada como fuente única e inmutable de identidad — pre-requisito de C-04 (RBAC) y de todo módulo de negocio posterior.

## What Changes

- `POST /api/auth/login` — valida email + password (Argon2id), emite par JWT (access 15 min) + refresh token con rotación. Claims: `sub` (user_id), `tenant_id`, `roles`, `exp`.
- `POST /api/auth/refresh` — rota el refresh token; el token usado queda inmediatamente invalidado.
- `POST /api/auth/logout` — revoca la sesión (invalida el refresh token activo).
- **2FA TOTP opcional por usuario**: `POST /api/auth/2fa/enroll` (genera secret + QR), `POST /api/auth/2fa/verify` (confirma el enrolamiento), gate entre validación de credenciales y emisión de sesión cuando 2FA está activo.
- `POST /api/auth/forgot` — genera token de un solo uso, expiración corta (15 min), notificación por email.
- `POST /api/auth/reset` — consume el token único y actualiza la contraseña (Argon2id).
- Rate limiting: 5 intentos / 60 s por combinación IP + email en `/api/auth/login`.
- Dependency `get_current_user` — extrae y verifica el JWT de cada request; resuelve `user_id`, `tenant_id` y `roles` para inyectar en los handlers. Esta dependency es el único punto de entrada válido para conocer la identidad del usuario.
- Migración Alembic 003: tabla `refresh_tokens` (id, user_id, tenant_id, token_hash, expires_at, revoked_at, created_at) + tabla `password_reset_tokens` (id, user_id, token_hash, expires_at, used_at). Las dos con `tenant_id` y soft-delete.
- Migración Alembic 004: tabla `totp_secrets` (id, user_id, encrypted_secret, confirmed, created_at) — el secret se almacena AES-256.

## Capabilities

### New Capabilities

- `auth-session`: Flujo completo de sesión — login con Argon2id, emisión de JWT + refresh token, rotación del refresh, logout y revocación. Incluye rate limiting y el modelo de datos de tokens.
- `auth-2fa`: Enrolamiento TOTP (secret generado + QR URI), confirmación del enrolamiento, gate de 2FA entre verificación de credenciales y emisión de sesión. Secret almacenado cifrado AES-256.
- `auth-password-recovery`: Solicitud de recuperación (token de un solo uso, TTL 15 min), reset de contraseña con consumo del token. Token hasheado en BD, nunca en texto plano.
- `auth-dependency`: Dependency FastAPI `get_current_user` que verifica el JWT, resuelve identidad y tenant, y lo pone disponible para todos los handlers protegidos. Fail-closed: token inválido o ausente → 401.

### Modified Capabilities

_(ninguna — no hay specs de auth previas)_

## Impact

- **Nuevos archivos**: `backend/app/api/v1/routers/auth.py`, `backend/app/features/auth/` (service, repository, schemas, models), `backend/app/core/dependencies.py` (ampliado), `backend/app/core/security.py` (ampliado con TOTP helpers), migraciones `003_refresh_tokens.py` y `004_totp_secrets.py`.
- **Archivos modificados**: `backend/app/core/security.py` (ya creado en C-01 con helpers JWT/Argon2), `backend/app/core/config.py` (vars: `SECRET_KEY`, `REFRESH_TOKEN_EXPIRE_DAYS`, `ACCESS_TOKEN_EXPIRE_MINUTES`), `backend/app/api/v1/router.py` (registrar router auth).
- **Dependencias nuevas**: `pyotp` (TOTP), `qrcode` (QR URI / imagen), `slowapi` (rate limiting sobre FastAPI).
- **Sin cambios de contrato** con cambios posteriores: `get_current_user` es la interfaz que C-04 (RBAC) y todos los módulos de negocio consumirán.
