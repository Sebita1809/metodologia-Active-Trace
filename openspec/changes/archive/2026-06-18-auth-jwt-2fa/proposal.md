## Why

activia-trace requiere autenticación propia desde el día 0 (ADR-001, cerrada). Sin login, refresh rotation, 2FA ni recuperación de contraseña, ningún módulo posterior (RBAC, usuarios, equipos docentes, comunicaciones) puede operar en un entorno multi-tenant seguro. C-02 dejó la infraestructura de base (modelos, repositorios, tenancy placeholder, cifrado AES-256); este change construye el sistema de autenticación que reemplaza el placeholder de tenancy y establece la identidad del usuario desde el JWT verificado.

## What Changes

- `POST /api/auth/login` — autenticación con email + password (Argon2id), emite access token (JWT 15 min) + refresh token con rotación
- `POST /api/auth/refresh` — rota refresh token, emite nuevo par; refresh usado queda invalidado
- `POST /api/auth/logout` — revoca la sesión activa
- `POST /api/auth/2fa/enroll` — genera secreto TOTP para el usuario (opcional por usuario)
- `POST /api/auth/2fa/verify` — verifica código TOTP y habilita 2FA
- `POST /api/auth/forgot` — genera token de un solo uso y lo envía por email (placeholder de email service)
- `POST /api/auth/reset` — valida token y permite establecer nueva contraseña
- Dependency `get_current_user` — resuelve identidad + tenant desde JWT verificado; reemplaza el placeholder de C-02
- Rate limiting 5/60s por IP+email en login
- Modelo `RefreshToken` en DB para tracking de rotación y revocación
- **BREAKING**: `get_current_tenant` ahora se resuelve del JWT, no del header `X-Tenant-ID` — el placeholder de C-02 queda reemplazado

## Capabilities

### New Capabilities
- `user-auth`: autenticación con email+password, JWT access token (15 min), refresh token con rotación, logout, dependency `get_current_user` que reemplaza el placeholder de tenancy
- `totp-2fa`: enrolamiento TOTP opcional por usuario, verificación de código, gate entre login y emisión de sesión
- `password-recovery`: flujo forgot/reset con token de un solo uso, expiración corta, invalidación post-uso
- `api-rate-limiting`: rate limiting 5 intentos/60s por IP+email en endpoint login

### Modified Capabilities
- `tenant-model`: el contexto de tenant se resuelve ahora del JWT verificado (no del header `X-Tenant-ID`); se actualiza la implementación de `get_tenant_context` en `core/tenancy.py`
- `data-access-layer`: el repository base sigue siendo válido; se agrega el modelo `RefreshToken` como nueva entidad

## Impact

- **Backend**: nuevo módulo `app/services/auth/` (login, 2FA, recovery), nuevo modelo `RefreshToken` en `app/models/`, nuevos schemas Pydantic en `app/schemas/auth/`, nuevas rutas en `app/api/v1/routers/auth.py`, modificaciones en `app/core/dependencies.py` y `app/core/tenancy.py`, nuevas config env vars en `app/core/config.py` (`REFRESH_TOKEN_EXPIRE_DAYS`, `TOTP_ISSUER`)
- **Dependencias nuevas**: `pyotp` (TOTP), `python-jose[cryptography]` (JWT) — ya declaradas en `pyproject.toml` desde C-01
- **Migración nueva**: `002_refresh_token` (tabla `refresh_token`)
- **Tests**: unitarios de cada endpoint + integración (base de datos real), flujo completo login→refresh→logout, 2FA enroll→verify→login, forgot→reset, rate limit
