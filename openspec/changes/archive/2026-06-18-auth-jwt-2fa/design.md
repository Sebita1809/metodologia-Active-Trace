## Context

activia-trace necesita un sistema de autenticación propio desde el día 0 (ADR-001). C-01 dejó el esqueleto FastAPI con slots reservados en `core/security.py`, `core/tenancy.py` y `core/dependencies.py`. C-02 implementó la infraestructura multi-tenant (modelo `Tenant`, `BaseModel` con `tenant_id`, `BaseRepository` con tenant-scope automático, `AESCipher` para cifrado de PII) con un placeholder de tenancy que lee el tenant desde el header `X-Tenant-ID`.

Este change reemplaza ese placeholder con autenticación real basada en JWT, estableciendo que:
- La **identidad** del usuario se resuelve exclusivamente del JWT verificado
- El **tenant** se resuelve del JWT, no de headers de request
- El acceso anónimo solo permite `POST /api/auth/login` y `POST /api/auth/forgot` + `POST /api/auth/reset`
- **No hay usuarios persistentes todavía** — C-07 implementa `Usuario` con PII cifrada; este change usa datos semilla o dependencias futuras

### Current state
- `backend/app/core/dependencies.py`: `get_db()` y `get_current_tenant()` (placeholders)
- `backend/app/core/tenancy.py`: resuelve tenant de header `X-Tenant-ID` o default UUID
- `backend/app/core/config.py`: `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES=15`, `ENCRYPTION_KEY`
- `backend/app/models/base.py`: `BaseModel` con UUID PK, tenant_id, timestamps, soft delete
- `backend/app/repositories/base.py`: `BaseRepository` genérico con tenant-scope
- `backend/app/core/security.py`: `AESCipher` (AES-256-GCM) — se reutiliza para recovery tokens

### Constraints
- **ADR-001 (cerrada)**: Auth propio, email+password+2FA TOTP, JWT access 15min + refresh rotation
- **Regla de oro**: identidad y tenant SOLO del JWT verificado, nunca de la request
- **Fail-closed**: sin JWT válido → 401; sin permiso explícito (C-04) → 403
- **≤500 LOC por archivo backend**
- **Strict TDD**: test que falla → código mínimo → triangulación → refactor
- **No mock de DB**: tests con base de datos real

## Goals / Non-Goals

**Goals:**
- Login con email + password, password hasheado con Argon2id
- JWT access token (15 min) + refresh token con rotación (refresh usado se invalida)
- Logout que revoca la sesión activa
- 2FA TOTP opcional por usuario: enrolar, verificar, gate en login
- Recuperación de contraseña: forgot (token único por email) + reset
- Dependency `get_current_user` que reemplaza `get_current_tenant` — resuelve identidad + tenant del JWT
- Rate limiting 5 intentos/60s por IP+email en login
- Modelo `RefreshToken` en DB para tracking de rotación
- Migración Alembic `002_refresh_token`

**Non-Goals:**
- **No crear el modelo `Usuario`** — eso es C-07. Este change usa un modelo mínimo `UserBase` (o datos semilla inline) para poder testear auth. C-07 conecta la tabla real.
- **No implementar RBAC ni permisos** — eso es C-04. `get_current_user` devuelve identidad+roles; la validación de permisos es C-04.
- **No enviar emails reales** — el recovery token se genera y almacena; el envío usa un placeholder/mock hasta C-12 (comunicaciones).
- **No CSRF protection** — se implementa en un change posterior (RNF-10 cubierto por C-05 o cross-cutting).
- **No refresh token rotation en múltiples dispositivos simultáneos** — un refresh invalida el anterior; el modelo es single-session por refresh.

## Decisions

### D1. Modelo de usuario mínimo para auth (antes de C-07)

- **Opción considerada**: esperar a C-07 para tener el modelo `Usuario` completo
- **Decisión**: crear un modelo temporal `AuthUser` en `models/auth.py` con solo `id`, `email`, `password_hash`, `totp_secret` (nullable), `totp_enabled`. C-07 lo reemplazará.
- **Por qué**:
  - C-07 depende de C-06 (estructura académica), que depende de C-04 (RBAC). Esperar a C-07 bloquearía todo el camino crítico.
  - `AuthUser` es mínimo: 4 columnas + heredadas de BaseModel. Migrar a `Usuario` en C-07 es un refactor acotado.
  - Permite testear auth real (login, 2FA, recovery) desde C-03 sin esperar C-06/C-07.
- **Consecuencia**: en C-07, se migran los datos de `auth_user` a `usuario` y se elimina la tabla temporal.

### D2. Refresh token con rotación y tracking en DB

- **Opción considerada**: refresh token stateless (JWT de larga duración), refresh token almacenado en DB con familia de rotación
- **Decisión**: refresh token almacenado en tabla `refresh_token` con `id`, `user_id`, `token_hash` (SHA-256 del token), `expires_at`, `revoked_at`, `replaced_by`. Rotación: al usar un refresh se revoca y se crea uno nuevo.
- **Por qué**:
  - Un refresh JWT stateless no se puede revocar individualmente (solo por expiración o cambio de secret key).
  - La tabla permite revocación selectiva (logout) y detección de reuso (si un refresh revocado se presenta, se invalida toda la "familia" — el usuario debe re-autenticarse).
  - `token_hash` evita almacenar el token en texto plano; si la DB se filtra, los refresh no son utilizables.
- **API del modelo**: `created_by_refresh_id` (nullable) permite rastrear la cadena de rotación.

### D3. Argon2id para hashing de passwords

- **Opción considerada**: bcrypt, scrypt
- **Decisión**: Argon2id (tiempo=2, memoria=19456KB, paralelismo=1) usando `argon2-cffi` (ya declarado en pyproject.toml desde C-01).
- **Por qué**:
  - Argon2id es el ganador del PHC (Password Hashing Competition) y el estándar recomendado por OWASP.
  - Resistente a ataques de GPU/ASIC por su configuración de memoria y tiempo.
  - `argon2-cffi` es la biblioteca Python más madura para Argon2.
  - Parámetros conservadores para un MVP; se pueden endurecer si el hardware lo permite.

### D4. 2FA TOTP con pyotp

- **Opción considerada**: `google-auth` + TOTP propio, servicio externo (Authy, Duo)
- **Decisión**: biblioteca `pyotp` para generación y verificación de códigos TOTP. El secreto se cifra con `AESCipher` antes de almacenarse en `auth_user.totp_secret`.
- **Por qué**:
  - `pyotp` es liviana, madura, sin dependencias externas. Implementa RFC 6238 (TOTP).
  - No requiere conexión externa ni servicio de terceros.
  - El secreto cifrado en reposo cumple con la política de PII del proyecto (KB §04).
  - El QR de enrolamiento se genera como URI `otpauth://` estándar, compatible con Google Authenticator, Authy, 1Password, etc.

### D5. Flujo de login con 2FA gate

- **Decisión**: el login tiene dos fases:
  1. Validar email+password → si OK y 2FA deshabilitado → emitir sesión directamente
  2. Si 2FA habilitado → devolver `{ "requires_2fa": true, "session_token": "<temp_token>" }` → cliente debe llamar `POST /api/auth/2fa/verify` con código TOTP + session_token → si OK → emite sesión real
- **Por qué**:
  - El `session_token` es un JWT de vida ultra-corta (2 min) que prueba que el paso 1 fue exitoso.
  - Evita emitir sesión completa sin 2FA, pero no obliga al cliente a re-enviar credenciales.
  - Alternativa considerada: session state en DB → más complejo, el JWT temporal es stateless.

### D6. Rate limiting con almacenamiento en memoria (por ahora)

- **Opción considerada**: Redis, base de datos, diccionario en memoria
- **Decisión**: diccionario en memoria con ventana deslizante (`collections.defaultdict` + timestamp cleanup periódico). Fácil de reemplazar por Redis cuando exista.
- **Por qué**:
  - Redis no existe aún en el stack. Añadirlo solo para rate limiting es premature.
  - 5 intentos/60s por IP+email ≈ pocos miles de entradas en memoria.
  - La función de rate limiting se abstrae detrás de una interfaz (`RateLimiter`) que se puede reemplazar por Redis sin cambiar los endpoints.
- **Riesgo**: al reiniciar el servidor se pierde el estado de rate limiting. Aceptable para MVP.

### D7. Recovery token cifrado con AESCipher

- **Decisión**: el token de recovery es un UUID aleatorio. Se almacena su hash SHA-256 en la tabla `password_recovery_token` (nueva) junto con `user_id`, `expires_at`, `used_at`. El token en sí (el UUID crudo) se devuelve en la respuesta del forgot (placeholder hasta C-12) y debe incluirse en el body del reset.
- **Por qué**:
  - UUID v4 aleatorio = 122 bits de entropía. Imposible de adivinar.
  - Hash en DB: mismo principio que refresh token — si la DB se filtra, los tokens no son utilizables.
  - Expiración corta (15 min por defecto). `used_at` asegura single-use.
  - No requiere JWT ni cifrado extra — el UUID es el bearer token.

### D8. Reemplazo del placeholder de tenancy

- **Decisión**: `get_current_tenant()` ahora es un alias para extraer `tenant_id` del JWT verificado. Se elimina la lógica de header `X-Tenant-ID`. Nueva dependency `get_current_user` devuelve un objeto `UserContext(user_id, tenant_id, roles, email)`.
- **Por qué**:
  - Cumple la regla de oro: identidad y tenant SOLO del JWT.
  - Los repositories siguen usando `tenant_id`; simplemente ahora viene del JWT en lugar del header.
  - El placeholder de C-02 era explícitamente temporal (ver design.md de C-02 D6).
- **Backward compatibility**: en desarrollo, se puede inyectar un token de test via header `Authorization: Bearer <test_token>`.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| **R1 — AuthUser temporal puede generar datos huérfanos**: si C-07 se retrasa, los auth_users creados en C-03 podrían quedar sin migrar. | C-07 está en el camino crítico inmediato después de C-06. El timeline es de días, no meses. La migración en C-07 será agregar la tabla `usuario` y copiar datos + eliminar `auth_user`. |
| **R2 — Rate limiting en memoria no persiste entre reinicios**: si la app se reinicia, el contador de intentos se pierde. Un atacante podría reiniciar el contador forzando un restart. | El restart no da acceso — las credenciales siguen siendo necesarias. El rate limit es una defensa de capa 7, no la única. En MVP, asumimos entorno controlado. Redis se agrega cuando haya más endpoints sensibles. |
| **R3 — Refresh token family invalidation puede confundir al cliente**: si un refresh token se usa dos veces (ej. race condition del cliente), se invalida toda la cadena y el usuario debe re-autenticarse. | El cliente debe implementar locking local para evitar race conditions. Documentar este comportamiento en la API. Es una trade-off aceptable por la seguridad de detección de robo de tokens. |
| **R4 — Sin usuario persistente real, los tests usan seeds inline**: los datos de auth (email, hash) se crean en fixtures de test, no en migraciones. | Es intencional: C-07 traerá los seeds reales. Los tests de C-03 crean su propio set de datos. |
| **R5 — JWT sin revocation list**: un access token robado no se puede revocar individualmente hasta su expiración (15 min). | La ventana de 15 min es el estándar de industria. Refresh rotation minimiza el riesgo. Una blacklist de JWT (Redis) se puede agregar post-MVP. |

## Migration Plan

1. Agregar modelo `AuthUser` y `RefreshToken`, `PasswordRecoveryToken`
2. Generar migración Alembic `002_auth_tables`
3. Implementar servicios de auth (login, refresh, logout, 2FA, recovery)
4. Actualizar `get_current_tenant` → `get_current_user` en dependencies
5. Agregar rate limiter
6. Tests de cada flujo (TDD)
7. Verificar que los tests de C-02 (tenant scope) sigan pasando con la nueva dependencia
