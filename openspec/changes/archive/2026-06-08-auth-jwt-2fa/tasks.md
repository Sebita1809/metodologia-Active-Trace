## 1. Dependencias y migraciones

- [x] 1.1 Agregar `pyotp`, `qrcode[pil]` y `slowapi` a `pyproject.toml` / `requirements`
- [x] 1.2 Crear migración Alembic 003: tablas `refresh_tokens` (id UUID PK, user_id UUID, tenant_id UUID, token_hash VARCHAR, expires_at TIMESTAMPTZ, revoked_at TIMESTAMPTZ NULL, created_at TIMESTAMPTZ) y `password_reset_tokens` (id UUID PK, user_id UUID, tenant_id UUID, token_hash VARCHAR, expires_at TIMESTAMPTZ, used_at TIMESTAMPTZ NULL, created_at TIMESTAMPTZ) — ambas con índice en `(tenant_id, token_hash)` y `(tenant_id, user_id)`
- [x] 1.3 Crear migración Alembic 004: tabla `totp_secrets` (id UUID PK, user_id UUID, tenant_id UUID, encrypted_secret TEXT, confirmed BOOLEAN DEFAULT false, created_at TIMESTAMPTZ) — índice en `(tenant_id, user_id)`
- [x] 1.4 Verificar que `alembic upgrade head` aplica las dos migraciones sin errores

## 2. Modelos SQLAlchemy

- [x] 2.1 [RED] Escribir `test_auth_models.py` que verifique instanciación y columnas de `RefreshToken`, `PasswordResetToken` y `TotpSecret`
- [x] 2.2 [GREEN] Crear `backend/app/features/auth/models.py`: `RefreshToken`, `PasswordResetToken`, `TotpSecret` heredando de `Base` (sin `BaseTenantModel` — estos son modelos de infraestructura con `tenant_id` explícito)
- [x] 2.3 [TRIANGULATE] Agregar test que verifique que `tenant_id` es NOT NULL y que `token_hash` no acepta nulos
- [x] 2.4 [REFACTOR] Extraer campos comunes (id, tenant_id, created_at) si hay duplicación

## 3. Schemas Pydantic

- [x] 3.1 [RED] Escribir tests de schemas: `LoginRequest` rechaza campos extra, `ResetRequest` valida longitud mínima de contraseña, `TokenResponse` tiene todos los campos esperados
- [x] 3.2 [GREEN] Crear `backend/app/features/auth/schemas.py`: `LoginRequest`, `RefreshRequest`, `LogoutRequest`, `ForgotRequest`, `ResetRequest`, `TotpVerifyRequest`, `TokenResponse`, `PartialTokenResponse`, `TotpEnrollResponse` — todos con `model_config = ConfigDict(extra='forbid')`
- [x] 3.3 [GREEN] Crear `backend/app/core/auth_context.py`: dataclass `CurrentUser(user_id: UUID, tenant_id: UUID, roles: list[str])` — inmutable (frozen=True)
- [x] 3.4 [TRIANGULATE] Agregar test que intente construir `LoginRequest` con campo desconocido → debe fallar con ValidationError

## 4. Repositorios

- [x] 4.1 [RED] Escribir tests TDD para `RefreshTokenRepository`: create, get_by_hash (token existente / inexistente), revoke, revoke_all_for_user
- [x] 4.2 [GREEN] Implementar `RefreshTokenRepository` en `backend/app/features/auth/repository.py` extendiendo `BaseRepository[RefreshToken]`; `get_by_hash` filtra por `tenant_id` y `token_hash`
- [x] 4.3 [RED] Escribir tests TDD para `PasswordResetTokenRepository`: create, get_valid_by_hash (excluye usados y expirados), mark_used, invalidate_previous_for_user
- [x] 4.4 [GREEN] Implementar `PasswordResetTokenRepository`
- [x] 4.5 [RED] Escribir tests TDD para `TotpSecretRepository`: create_pending, get_for_user (solo confirmed=true), confirm, get_pending_for_user
- [x] 4.6 [GREEN] Implementar `TotpSecretRepository`
- [x] 4.7 [TRIANGULATE] Agregar tests de aislamiento de tenant: tokens de tenant A no son visibles desde tenant B

## 5. Helpers de seguridad

- [x] 5.1 [RED] Escribir tests para helpers JWT: `create_access_token` produce token con claims correctos, `verify_token` rechaza token expirado y firma inválida, `create_partial_token` produce scope `"2fa_pending"`
- [x] 5.2 [GREEN] Ampliar `backend/app/core/security.py`: `create_access_token(user_id, tenant_id, roles)`, `create_refresh_token()`, `create_partial_token(user_id, tenant_id)`, `verify_token(token, expected_scope=None)`
- [x] 5.3 [RED] Escribir tests para helpers TOTP: `generate_totp_secret()` produce secret de entropía suficiente, `get_totp_uri()` produce URI válida, `verify_totp_code(secret, code)` acepta código actual y rechaza código viejo
- [x] 5.4 [GREEN] Agregar helpers TOTP a `security.py` usando `pyotp`
- [x] 5.5 [TRIANGULATE] Test: `verify_token` con scope `"2fa_pending"` es rechazado por `verify_token(expected_scope="access")`

## 6. AuthService

- [x] 6.1 [RED] Test: `login()` con credenciales válidas retorna `TokenResponse`; con contraseña incorrecta lanza `AuthenticationError`
- [x] 6.2 [GREEN] Implementar `AuthService.login()` en `backend/app/features/auth/service.py`: verifica email, verifica Argon2id, detecta 2FA activo, emite tokens o partial_token
- [x] 6.3 [RED] Test: `refresh()` rota el token; reuso de token revocado revoca todos los tokens del usuario
- [x] 6.4 [GREEN] Implementar `AuthService.refresh()`: `SELECT FOR UPDATE` en verificación, revocación atómica, emisión de nuevo par
- [x] 6.5 [GREEN] Implementar `AuthService.logout()`: revocar refresh token (idempotente)
- [x] 6.6 [RED] Test: `enroll_2fa()` genera URI TOTP; `confirm_2fa()` con código válido activa 2FA; `confirm_2fa()` con código inválido deja el enrolamiento pendiente
- [x] 6.7 [GREEN] Implementar `AuthService.enroll_2fa()`, `confirm_2fa()`, `verify_2fa_gate()`
- [x] 6.8 [RED] Test: `forgot_password()` crea token nuevo e invalida el anterior; `reset_password()` con token válido actualiza contraseña y revoca sesiones; con token usado lanza error
- [x] 6.9 [GREEN] Implementar `AuthService.forgot_password()` y `AuthService.reset_password()`
- [x] 6.10 [TRIANGULATE] Test: `login()` cuando el usuario tiene 2FA activo retorna `PartialTokenResponse` con `requires_2fa=True`

## 7. Rate limiting

- [x] 7.1 Configurar `slowapi` con limiter in-process en `backend/app/main.py` (lifespan o middleware); registrar handler de error 429
- [x] 7.2 Aplicar decorador `@limiter.limit("5/minute")` al endpoint `POST /api/auth/login` con key `ip+email`
- [x] 7.3 [RED] Test: 5 requests seguidos pasan; el 6° recibe 429 con header `Retry-After`
- [x] 7.4 [GREEN] Verificar que el test de rate limit pasa; ajustar configuración de slowapi si es necesario

## 8. Router y Dependency `get_current_user`

- [x] 8.1 [RED] Test de integración: `POST /api/auth/login` con credenciales válidas retorna 200 con tokens; con credenciales inválidas retorna 401
- [x] 8.2 [GREEN] Crear `backend/app/api/v1/routers/auth.py`: `POST /login`, `POST /refresh`, `POST /logout`, `POST /forgot`, `POST /reset`; registrar en `backend/app/api/v1/router.py`
- [x] 8.3 [GREEN] Agregar endpoints 2FA al router: `POST /2fa/enroll`, `POST /2fa/verify`, `POST /2fa/login-verify`
- [x] 8.4 [RED] Test de dependency: handler protegido sin token → 401; con token válido → handler ejecuta; con `partial_token` → 401
- [x] 8.5 [GREEN] Implementar `get_current_user` en `backend/app/core/dependencies.py`: extrae Bearer token, llama `verify_token(expected_scope="access")`, retorna `CurrentUser`
- [x] 8.6 [TRIANGULATE] Test: handler protegido con token de otro tenant → la dependency retorna el tenant del token, no del parámetro

## 9. Tests de integración end-to-end

- [x] 9.1 Flujo completo: login → usar endpoint protegido → refresh → usar con nuevo token → logout → refresh revocado → 401
- [x] 9.2 Flujo 2FA completo: login → recibe partial_token → verify_2fa_gate → recibe access+refresh → usar endpoint protegido
- [x] 9.3 Flujo recuperación: forgot → obtener token del log/stub → reset con nueva contraseña → login con nueva contraseña OK → login con contraseña anterior KO
- [x] 9.4 Aislamiento de tenant: refresh token de usuario A no es aceptado para usuario B (mismo hash, distinto tenant)
- [x] 9.5 Identidad inmutable: endpoint que acepta `user_id` en query string opera sobre el `user_id` del JWT, no el del parámetro
