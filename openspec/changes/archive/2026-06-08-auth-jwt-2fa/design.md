## Context

C-01 estableció el scaffold FastAPI con helpers JWT y Argon2id en `backend/app/core/security.py` pero sin ningún endpoint expuesto. C-02 creó `BaseTenantModel`, `BaseRepository[T]` con scope de tenant y `CryptoService` AES-256. C-03 construye sobre ambos: implementa la capa de identidad completa — sesión, 2FA y recuperación — y expone la dependency `get_current_user` que todos los módulos posteriores (C-04 en adelante) consumirán.

Governance: **CRÍTICO**. Autenticación y gestión de sesiones; cada decisión de este change tiene impacto de seguridad transversal.

## Goals / Non-Goals

**Goals:**
- Endpoint de login que valide credenciales y emita JWT + refresh token con rotación.
- Endpoint de refresh que rote el token y revoque el anterior en la misma transacción.
- Endpoint de logout que invalide la sesión activa.
- Flujo de 2FA TOTP como gate opcional por usuario (entre credenciales válidas y emisión de tokens).
- Flujo de recuperación de contraseña con token de un solo uso y TTL corto.
- Rate limiting en login (5 req/60 s por IP+email).
- Dependency `get_current_user` que resuelva identidad + tenant desde el JWT para todos los handlers.
- Cobertura de tests ≥90% para todas las reglas de negocio del módulo.

**Non-Goals:**
- SSO con Moodle (ADR-001: Fase 2).
- Impersonación (ADR-004: pendiente, se decide al construir esa feature).
- RBAC / permisos finos (C-04).
- UI de login (C-21).
- Envío real de emails de recuperación (stub o log en este change; el worker real llega en C-12).

## Decisions

### D-01: Refresh tokens hasheados en BD

**Decisión:** el refresh token se almacena como `SHA-256(token)` en la tabla `refresh_tokens`. El valor en claro nunca persiste.

**Alternativa considerada:** token opaco generado por `secrets.token_urlsafe(64)` almacenado en texto plano. Descartado: si la BD se filtra, todos los refresh tokens quedan expuestos.

**Rationale:** SHA-256 es suficiente para un token aleatorio de alta entropía (no hay ataques de diccionario viables contra 64 bytes de aleatoriedad). El costo de verificar es O(1) con una consulta indexada sobre `token_hash`.

### D-02: Rotación atómica del refresh token

**Decisión:** refresh y revocación del token anterior ocurren en la misma transacción de BD. Si el emisión del nuevo token falla, el token viejo NO se revoca.

**Rationale:** evita que un cliente quede bloqueado por un fallo en medio del flujo. El riesgo inverso (doble uso de un refresh token si la red cae después de emitir) se mitiga con TTL corto (7 días por defecto) y detección de reuso (ver D-03).

### D-03: Detección de reuso de refresh token (token rotation leak detection)

**Decisión:** si un refresh token ya revocado es presentado, se invalidan TODOS los refresh tokens activos del usuario en ese tenant.

**Rationale:** un token revocado presentado de nuevo indica posible filtración de sesión. La respuesta conservadora es matar todas las sesiones activas del usuario afectado.

### D-04: TOTP secret cifrado AES-256

**Decisión:** el TOTP secret se cifra con `CryptoService.encrypt()` (AES-256-GCM, ya implementado en C-02) antes de persistir en `totp_secrets`.

**Alternativa considerada:** almacenar el secret en texto plano. Descartado: es PII de seguridad y la regla dura 12 del proyecto exige cifrado de secretos en reposo.

### D-05: Gate de 2FA — respuesta intermedia con `partial_token`

**Decisión:** cuando el usuario tiene 2FA activo, el login exitoso de credenciales responde con `HTTP 200` y un `partial_token` JWT de vida muy corta (5 min, scope `"2fa_pending"`). El cliente usa ese token en `POST /api/auth/2fa/verify` para completar la sesión. Si el `partial_token` expira, el usuario debe relanzar el login.

**Alternativa considerada:** sesión de servidor con estado en Redis. Descartado: agrega dependencia de infraestructura (Redis) no aún instalada. El `partial_token` mantiene el patrón stateless y la vida corta limita el riesgo.

### D-06: Rate limiting con slowapi (in-process)

**Decisión:** usar `slowapi` (wrapper de `limits` para FastAPI) con backend in-process (memoria) para el MVP.

**Alternativa considerada:** Redis-backed rate limiting. Preferido para producción multi-proceso pero agrega dependencia. El in-process es suficiente para un proceso único (Docker single container). Se puede migrar a Redis sin cambiar el contrato del endpoint.

### D-07: Password reset token — SHA-256 en BD, entrega por log/evento

**Decisión:** el reset token es `secrets.token_urlsafe(32)`, se almacena como `SHA-256(token)` en `password_reset_tokens`. En este change el "envío por email" es un evento logeado (INFO log con el token en claro) o un stub; el worker real de email llega en C-12.

**Rationale:** separar la persistencia del mecanismo de entrega permite testear el flujo completo sin un servidor SMTP. La interfaz del service quedará estable cuando C-12 conecte el worker.

### D-08: `get_current_user` como FastAPI Dependency con DI

**Decisión:** `get_current_user` es una función async que recibe `token: str = Depends(oauth2_scheme)` y retorna un `CurrentUser` dataclass con `user_id`, `tenant_id`, `roles`. Se inyecta vía `Depends()` en cada handler protegido. No tiene estado global.

**Rationale:** el patrón estándar de FastAPI. Permite sobrescribir en tests sin monkey-patching. `CurrentUser` es un DTO inmutable — no un modelo ORM — para evitar lazy loading accidental en el request context.

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|------------|
| Race condition en detección de reuso (D-03) si dos requests con el mismo token llegan simultáneamente | Usar `SELECT ... FOR UPDATE` en la verificación del token para serializar accesos. |
| `partial_token` (D-05) podría reutilizarse si el cliente lo guarda | El `partial_token` tiene scope `"2fa_pending"` validado en el endpoint de verify; no acepta ningún otro endpoint. TTL 5 min. |
| In-process rate limiting (D-06) no sobrevive restart ni escala a multi-proceso | Documentado como limitación MVP. La interfaz de `slowapi` es compatible con Redis backend — migración no rompe la API. |
| Email de recuperación por log en este change | Controlado: la función `send_password_reset_email` es un stub con firma definida que C-12 implementará. No hay comportamiento de producción bloqueado. |

## Migration Plan

1. Correr `alembic upgrade head` → aplica migración 003 (`refresh_tokens`, `password_reset_tokens`) y migración 004 (`totp_secrets`).
2. No hay datos de sesión previos que migrar (C-01/C-02 no tenían usuarios reales).
3. Rollback: `alembic downgrade -2` revierte las dos migraciones. Sin pérdida de datos de negocio (tablas nuevas, vacías).

## Open Questions

- **OQ-C03-01**: ¿El `partial_token` de 2FA debe ser revocable (lista negra) o basta con el TTL de 5 min? → Para MVP: TTL basta. Revisar si aparecen casos de logout durante el gate.
- **OQ-C03-02**: ¿`REFRESH_TOKEN_EXPIRE_DAYS` configurable por tenant o global? → Global para MVP (env var). Por-tenant si un tenant exige sesiones más cortas — posponer a cuando haya un tenant real con ese requerimiento.
