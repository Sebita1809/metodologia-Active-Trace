## Context

C-01 entregó el scaffold FastAPI con engine async, `Base` declarativa y Alembic inicializado pero sin migraciones de dominio. C-02 construye sobre ese scaffold el cimiento de persistencia multi-tenant que todos los demás changes requieren: el modelo `Tenant`, el mixin que hereda cada tabla del dominio, el repositorio genérico con scope de tenant, el helper de cifrado en reposo, y la primera migración Alembic. Sin este change, ningún modelo de dominio puede escribirse de forma segura ni conforme al ADR-002 (row-level tenant isolation).

## Goals / Non-Goals

**Goals:**
- Definir `Tenant` como entidad raíz con su migración Alembic 001.
- Proveer `BaseTenantModel`: mixin SQLAlchemy con UUID PK, `tenant_id`, `created_at`, `updated_at`, `deleted_at`.
- Proveer `BaseRepository[T]`: repositorio genérico async que aplica scope de tenant en TODA operación; imposible de usar sin tenant por diseño.
- Proveer `CryptoService`: cifrado AES-256-GCM de strings PII; IV aleatorio por operación, resultado base64url.
- Establecer la convención de migraciones Alembic (async, una migración por schema change).
- Tests: aislamiento tenant, soft delete transparente, cifrado round-trip, timestamps automáticos.

**Non-Goals:**
- Modelos de dominio concretos (Usuario, Materia, etc.) — pertenecen a C-06/C-07.
- Endpoints HTTP — este change no expone API.
- Lógica de auth o RBAC — pertenece a C-03/C-04.
- Cifrado de columnas completas a nivel de tipo SQLAlchemy (TypeDecorator) — se aplica explícitamente en services/repositories donde sea necesario; un TypeDecorator automático es magic que dificulta el debugging.

## Decisions

### D1 — Mixin via `MappedColumn` con SQLAlchemy 2.0 declarativo

**Decisión**: `BaseTenantModel` es una clase Python pura que hereda de la `Base` declarativa de C-01, con columnas definidas como `Mapped[T]` / `mapped_column()`. No se usa `declared_attr` ni metaclass personalizada.

**Alternativa descartada**: Mixin con `declared_attr` (SQLAlchemy 1.x style) — incompatible con la API tipada de SQLAlchemy 2.0 y pierde el autocompletado de mypy.

**Rationale**: La API `Mapped[T]` de SQLAlchemy 2.0 da type-safety real en los atributos sin boilerplate adicional. El mixin hereda `Base` → evita doble registro de metadata.

---

### D2 — `BaseRepository[T]` con Generic typing

**Decisión**: `BaseRepository` es una clase genérica `Generic[T]` con `T = TypeVar("T", bound=BaseTenantModel)`. Recibe `tenant_id: UUID` en el constructor y lo inyecta en cada query. El método `_base_query()` es el único punto donde se aplica el filter de tenant; toda operación pública lo llama.

**Alternativa descartada**: Pasar `tenant_id` en cada método individualmente — fácil de olvidar en nuevos métodos, auditable solo por convención. Con el constructor, es imposible instanciar un repositorio sin tenant.

**Rationale**: Hace el scope de tenant imposible de omitir por accidente. El code review solo necesita verificar que el repositorio fue construido con el tenant correcto, no que cada query lo incluya.

---

### D3 — Soft delete via `deleted_at: datetime | None`

**Decisión**: El campo `deleted_at` en `BaseTenantModel` es `Mapped[datetime | None]`, default `None`. Un registro con `deleted_at IS NOT NULL` está "eliminado". `BaseRepository._base_query()` filtra `deleted_at IS NULL` por defecto; existe `_base_query_including_deleted()` para casos de auditoría.

**Alternativa descartada**: Campo booleano `is_deleted` — no guarda cuándo fue eliminado; peor para auditoría.

**Rationale**: El timestamp de eliminación es dato de auditoría requerido. El filtro en `_base_query` garantiza que el soft delete es transparente para todos los métodos del repositorio sin repetición.

---

### D4 — Cifrado AES-256-GCM con IV aleatorio por operación

**Decisión**: `CryptoService.encrypt(plaintext: str) -> str` genera un IV de 12 bytes aleatorios, cifra con AES-256-GCM (tag de 16 bytes), y devuelve `base64url(iv || ciphertext || tag)`. `decrypt` revierte el proceso. La clave (`ENCRYPTION_KEY`) llega desde `Settings` (pydantic-settings, env var, 32 bytes hex).

**Alternativa descartada**: AES-256-CBC — no provee autenticación del ciphertext; un atacante que puede modificar el ciphertext puede hacer padding oracle. GCM detecta cualquier tampering.

**Alternativa descartada**: IV fijo por registro — rompe la seguridad semántica; dos textos iguales producen el mismo ciphertext.

**Rationale**: AES-256-GCM es el estándar moderno de cifrado autenticado. IV aleatorio por operación garantiza que cifrar el mismo valor dos veces produce resultados distintos.

**Librería**: `cryptography` (PyCA). Si no está como dependencia directa, se agrega a `pyproject.toml`.

---

### D5 — Alembic async con `run_sync` para `create_all` en tests

**Decisión**: `alembic/env.py` usa `run_async_migrations()` con el engine async de `core/database.py`. En tests, los fixtures crean las tablas con `Base.metadata.create_all` vía `conn.run_sync(...)` sobre el engine async de test (no se corren migraciones en tests — las migraciones son para producción).

**Rationale**: Separar schema de test (create_all directo) de schema de producción (Alembic migrations) evita dependencia circular entre test fixtures y el estado de las migraciones. Los tests prueban el modelo, no el script de migración.

## Risks / Trade-offs

- **[Riesgo] Repositorios instanciados sin `tenant_id` correcto** → Mitigation: el constructor lo requiere y es de tipo `UUID` (no `str`); un `tenant_id` hardcodeado es visible en code review.
- **[Riesgo] `CryptoService` con clave débil en desarrollo** → Mitigation: `Settings` valida longitud mínima de `ENCRYPTION_KEY` (32 bytes = 64 hex chars); el arranque falla si no se cumple.
- **[Trade-off] Cifrado en capa de aplicación vs. cifrado a nivel de columna de BD** → Elegido: aplicación. Más portable, auditable en código, compatible con Alembic sin plugins de BD.
- **[Trade-off] GCM produce ciphertexts distintos por cada encrypt de la misma PII** → Consecuencia: no se puede hacer `WHERE email = encrypt(?)` en SQL. Los lookups por email deben traer el registro y descifrar en aplicación, o usar un índice de hash separado (decisión diferida a C-07 cuando se implementa Usuario).

## Migration Plan

1. Aplicar `alembic upgrade head` en el entorno de desarrollo para crear la tabla `tenants`.
2. La migración 001 es el baseline; C-02 no requiere datos de seed (los tenants se crean por API en C-03+).
3. Rollback: `alembic downgrade -1` ejecuta el `drop_table('tenants')` del downgrade definido en la migración.

## Open Questions

- **OQ-1**: ¿`Tenant` lleva campos de configuración (`slug`, `nombre`, `activo`) en esta migración o en una migración separada de C-03? — Por ahora: incluir `slug`, `nombre`, `activo` en 001 para que C-03 pueda validar el tenant en el login sin migración adicional.
- **OQ-2**: ¿El índice de hash para lookup de email cifrado se maneja en C-02 o se difiere? — Diferido a C-07 (implementación de Usuario). C-02 provee solo la utilidad de cifrado.
