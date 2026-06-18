## 1. Models & Migration

- [x] 1.1 Create `AuthUser` model in `app/models/auth_user.py` with: id, email (unique per tenant), password_hash, totp_secret (encrypted, nullable), totp_enabled (bool, default false). Inherits BaseModel.
- [x] 1.2 Create `RefreshToken` model in `app/models/refresh_token.py` with: id, user_id (FK to auth_user), token_hash, expires_at, revoked_at (nullable), replaced_by (nullable self-ref FK). Inherits BaseModel.
- [x] 1.3 Create `PasswordRecoveryToken` model in `app/models/password_recovery_token.py` with: id, user_id (FK), token_hash, expires_at, used_at (nullable). Inherits BaseModel.
- [x] 1.4 Update `app/models/__init__.py` to export all new models.
- [x] 1.5 Generate Alembic migration `002_auth_tables` with autogenerate, verify up/down.
- [x] 1.6 Run migration and verify tables exist in DB.

## 2. JWT & Auth Service

- [x] 2.1 Implement JWT utility functions in `app/core/security.py`: `create_access_token(user_id, tenant_id, roles, expires_delta)`, `create_refresh_token()`, `verify_token(token)` returning payload or raising.
- [x] 2.2 Add env vars to `app/core/config.py`: `REFRESH_TOKEN_EXPIRE_DAYS` (default 7), `TOTP_ISSUER` (default "activia-trace"), `RECOVERY_TOKEN_EXPIRE_MINUTES` (default 15).
- [x] 2.3 Implement `AuthService` in `app/services/auth/auth_service.py`: `authenticate(email, password)` returning user or None, `create_session(user)` returning access+refresh pair, `refresh_session(refresh_token_str)` rotating tokens, `revoke_session(refresh_token_str)`.
- [x] 2.4 Implement `RefreshTokenRepository` in `app/repositories/refresh_token_repo.py` with: `create(token_data)`, `get_by_token_hash(hash)`, `revoke(token_id, replaced_by=None)`, `list_active_by_user_id(user_id)`, `revoke_all_for_user(user_id)`.
- [x] 2.5 Create `app/services/__init__.py`, `app/services/auth/__init__.py`, and `app/schemas/__init__.py`.
- [x] 2.6 Create auth schemas in `app/schemas/auth/`: `LoginRequest`, `LoginResponse`, `Login2FARequiredResponse`, `RefreshRequest`, `RefreshResponse`, `LogoutRequest`, `TokenResponse`, `ErrorResponse`.

## 3. Auth Router & Current User Dependency

- [x] 3.1 Implement `POST /api/v1/auth/login` in `app/api/v1/routers/auth.py`: validate email+password via AuthService, handle 2FA gate, return tokens.
- [x] 3.2 Implement `POST /api/v1/auth/refresh` in auth router: validate refresh token, rotate, return new pair.
- [x] 3.3 Implement `POST /api/v1/auth/logout` in auth router: revoke refresh token.
- [x] 3.4 Implement `get_current_user` dependency in `app/core/dependencies.py`: extract Bearer token from Authorization header, verify JWT, return `UserContext(user_id, tenant_id, email, roles)`.
- [x] 3.5 Update `get_tenant_context` in `app/core/tenancy.py`: now resolves tenant_id from JWT claims via `get_current_user` instead of X-Tenant-ID header.
- [x] 3.6 Register auth router in `app/main.py` under `/api/v1/auth`.

## 4. 2FA TOTP

- [x] 4.1 Implement TOTP service in `app/services/auth/totp_service.py`: `generate_secret(user_id)` returning otpauth URI and storing encrypted secret, `verify_code(user_id, code)` with window ±1.
- [x] 4.2 Implement `POST /api/v1/auth/2fa/enroll` in auth router: generate TOTP secret, return otpauth URI + secret (for backup).
- [x] 4.3 Implement `POST /api/v1/auth/2fa/verify` in auth router: accept temp session token + TOTP code, if valid emit full session (access+refresh).
- [x] 4.4 Add TOTP schemas: `EnrollResponse(uri, secret)`, `Verify2FARequest(code, session_token)`, `Login2FARequiredResponse(requires_2fa, session_token)`.

## 5. Password Recovery

- [x] 5.1 Implement recovery service in `app/services/auth/recovery_service.py`: `create_recovery_token(email)` returning UUID token, `verify_reset(token_str, new_password)` validating and applying.
- [x] 5.2 Implement `POST /api/v1/auth/forgot` in auth router: accept email, generate recovery token, return token (placeholder — real email sending is C-12).
- [x] 5.3 Implement `POST /api/v1/auth/reset` in auth router: accept token + new_password, validate token, update password hash.
- [x] 5.4 Add recovery schemas: `ForgotRequest(email)`, `ForgotResponse(message)`, `ResetRequest(token, new_password)`.

## 6. Rate Limiting

- [x] 6.1 Implement `RateLimiter` interface and `InMemoryRateLimiter` in `app/core/rate_limiter.py`: sliding window per key (IP+email), configurable max_attempts and window_seconds, cleanup of stale entries.
- [x] 6.2 Add rate limiter as dependency and apply to login endpoint: 5 attempts per 60 seconds per IP+email key.
- [x] 6.3 Return HTTP 429 with `Retry-After` header when rate limit exceeded.

## 7. Tests

- [x] 7.1 Test login: valid credentials → 200 with tokens, invalid email → 401, invalid password → 401, non-existent tenant → 401.
- [x] 7.2 Test refresh rotation: valid refresh → new pair + old revoked, reuse of revoked refresh → 401 + family invalidated.
- [x] 7.3 Test logout: valid refresh → 200 + token revoked, already revoked → 401.
- [x] 7.4 Test 2FA: enroll → 200 with URI, verify correct code → session emitted, verify wrong code → 401, login with 2FA enabled → requires_2fa response.
- [x] 7.5 Test password recovery: forgot → token returned, reset with valid token → password changed, reset with expired token → 410, reset with used token → 410.
- [x] 7.6 Test rate limiting: 5 failed logins within 60s → 6th returns 429, wait for window → resumes normal.
- [x] 7.7 Test `get_current_user`: valid JWT → correct user/tenant, expired JWT → 401, missing token → 401, invalid signature → 401.
- [x] 7.8 Test tenant isolation from C-02 still passes with new JWT-based tenancy.
