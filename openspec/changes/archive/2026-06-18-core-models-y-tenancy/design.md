## Context

activia-trace requiere multi-tenancy desde el día 0 (ADR-002, cerrada). El foundation (C-01) dejó el esqueleto de la aplicación con FastAPI, conexión async a PostgreSQL, health check e infraestructura base (Docker, OTel). Sin embargo, no existe todavía el modelo `Tenant`, no hay un mecanismo de aislamiento entre instituciones, no hay mixins base que estandaricen las columnas comunes (UUID PK, timestamps, soft delete), no hay una capa de acceso a datos que aplique tenant-scope automáticamente, y no hay cifrado en reposo para atributos PII.

Este change construye esos cimientos que son **requisito de todos los módulos de dominio posteriores** (C-03 en adelante).

### Current state
- `backend/app/main.py`: FastAPI app bootstrap
- `backend/app/core/config.py`: Settings Pydantic v2 desde env vars
- `backend/app/core/database.py`: SQLAlchemy async engine + session factory
- `backend/app/core/dependencies.py`: Dependency injection (get_db, get_current_tenant — placeholder)
- `backend/app/api/v1/routers/health.py`: Health check endpoint
- No hay modelos, no hay repositorios, no hay cifrado, no hay Alembic configurado

### Constraints
- **ADR-002 (cerrada)**: Multi-tenancy row-level. Columna `tenant_id` en toda tabla. Una sola base de datos.
- **Regla de oro**: Identidad y tenant desde el JWT (resuelto vía dependency, aunque JWT se implementa en C-03).
- **Clean Architecture**: Models (ORM) → Repositories (queries) → Services (lógica) → Routers (HTTP). Sin saltos.
- **Soft delete siempre**: nunca borrado físico.
- **PII cifrada en reposo**: AES-256 para atributos `[cifrado]`.
- **≤500 LOC por archivo backend**.

## Goals / Non-Goals

**Goals:**
- Modelo `Tenant` como entidad raíz con su ciclo de vida (activo/inactivo).
- Mixin `BaseModel` que todo modelo del dominio hereda: UUID PK, `tenant_id`, `created_at`, `updated_at`, `deleted_at` (soft delete).
- Repository genérico `BaseRepository` con scope de tenant siempre activo en todas las queries.
- Utilidad `AESCipher` para cifrado/descifrado AES-256-GCM de atributos PII.
- Setup completo de Alembic (entorno, `env.py` dinámico, primera migración `001_tenant`).
- Tests de aislamiento multi-tenant, soft delete, timestamps y cifrado round-trip.

**Non-Goals:**
- **No implementar autenticación JWT** — eso es C-03. El tenant se resuelve de una dependency placeholder que C-03 conectará al JWT real.
- **No construir el catálogo de roles ni permisos** — eso es C-04.
- **No crear ningún modelo de dominio de negocio** (Usuario, Materia, etc.) — eso son changes posteriores.
- **No implementar encriptación de secretos externos** (API keys) — se hace cuando se necesiten integraciones.
- **No configurar migraciones para nada más que `tenant`** — cada change agrega su propia migración.

## Decisions

### D1. UUID v4 como PK de todas las tablas

- **Opción considerada**: `BIGSERIAL` auto-incremental
- **Decisión**: UUID v4 generado por la app (`uuid.uuid4()`) con columna SQLAlchemy `type: UUID`
- **Por qué**:
  - El modelo de datos de activia-trace ya define `id: UUID` en todas las entidades (KB §04).
  - UUIDs eliminan el riesgo de enumeración/guessabilidad de IDs secuenciales (relevante en multi-tenant).
  - No hay contención de secuencias en escritura concurrente.
  - El costo de performance versus `BIGSERIAL` en tablas con <1M filas es despreciable con PostgreSQL.
- **Implementación**: Columna `id = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)` en el mixin base. No usar `server_default=gen_random_uuid()` para mantener el control en la app y facilitar tests.

### D2. Soft delete con `deleted_at` nullable

- **Opción considerada**: columna `deleted` booleana, columna `deleted_at` timestamp
- **Decisión**: `deleted_at = mapped_column(DateTime(timezone=True), nullable=True, index=True)`. Nulo = vigente. No nulo = eliminado.
- **Por qué**:
  - Permite saber CUÁNDO se eliminó sin joins adicionales.
  - El filtro `WHERE deleted_at IS NULL` es expresivo y estándar.
  - El index permite barridos eficientes sobre registros vigentes.
  - Coincide con la práctica recomendada en sistemas auditables.
- **Scope**: El mixin base aplica el filtro automáticamente en `get()`, `list()`, `update()`. Se puede levantar explícitamente con `include_deleted=True`.

### D3. Repository genérico con tenant-scope automático

- **Opción considerada**: Query property en cada repositorio manual, middleware a nivel de sesión SQLAlchemy
- **Decisión**: Clase genérica `BaseRepository[T: BaseModel]` que recibe el `tenant_id` en el constructor y lo inyecta en todas las queries CRUD.
- **Por qué**:
  - El tenant-scope automático es un **requisito no negociable** (ADR-002, "un query sin scope de tenant es un bug").
  - Si el filtro es implícito en el repository base, ningún desarrollador puede olvidarse de agregarlo.
  - Tipado genérico (`Generic[T]`) permite que cada repositorio especializado herede con su modelo concreto.
  - Un método explícito `get_by_id_without_tenant()` permite casos controlados de administración cross-tenant.
- **Estructura**:
  ```python
  class BaseRepository(Generic[ModelT]):
      def __init__(self, db: AsyncSession, tenant_id: UUID): ...
      async def create(self, data: dict) -> ModelT: ...
      async def get(self, id: UUID) -> ModelT | None: ...
      async def list(self, **filters) -> list[ModelT]: ...
      async def update(self, id: UUID, data: dict) -> ModelT: ...
      async def delete(self, id: UUID) -> None: ...  # soft delete
  ```
- El método `get()` siempre aplica `WHERE tenant_id = :tenant_id AND deleted_at IS NULL`. El método `list()` agrega filtros adicionales a la base. `delete()` hace `UPDATE deleted_at = now()`.

### D4. AES-256-GCM para cifrado en reposo

- **Opción considerada**: `cryptography.fernet.Fernet` (AES-128-CBC + HMAC), AES-256-CBC con HMAC separado
- **Decisión**: AES-256-GCM usando la biblioteca `cryptography` directamente.
- **Por qué**:
  - GCM es **authenticated encryption**: provee confidencialidad E integridad en un solo paso. No requiere HMAC adicional.
  - AES-256 cumple con el requisito de seguridad del producto (KB §04, ARQUITECTURA.md §5.4).
  - GCM es el modo recomendado por NIST para cifrado simétrico.
  - Cada ciphertext incluye nonce + tag + datos cifrados; el decriptado verifica integridad antes de devolver datos.
  - La clave se lee de `ENCRYPTION_KEY` (exactamente 32 bytes).
- **API**:
  ```python
  class AESCipher:
      @staticmethod
      def encrypt(plaintext: str) -> str: ...   # base64(nonce + ciphertext + tag)
      @staticmethod
      def decrypt(ciphertext_b64: str) -> str: ...  # devuelve plaintext o raise
  ```
  El output es base64 para almacenamiento en columna TEXT.

### D5. Alembic con `env.py` dinámico

- **Decisión**: Configuración Alembic estándar con `env.py` que importa los modelos desde `app.models` para autogenerate.
- **Por qué**:
  - `--autogenerate` detecta cambios en los modelos SQLAlchemy y genera la migración.
  - Un solo directorio `alembic/` en `backend/`.
  - Primera migración: `001_tenant` que crea la tabla `tenant`.
  - Cada change subsiguiente agrega su propia migración (una por cambio de schema).
- **Convención**: Las migraciones se nombran `{NNN}_{descripción}.py` con `down_revision` encadenado. `001_tenant` no tiene `down_revision` (es la raíz).

### D6. Inyección de `tenant_id` vía dependency

- **Decisión**: El `tenant_id` se resuelve de una dependency `get_current_tenant()` que en C-02 es un placeholder simple (tenant por defecto para desarrollo). C-03 la reemplazará con la resolución real desde el JWT.
- **Por qué**: C-02 necesita que el tenant-scope funcione para tests; pero JWT se implementa en C-03. Un placeholder permite avanzar sin bloqueo.
- **Implementación**: En `app/core/tenancy.py`, una función `get_tenant_context()` que lee de un header `X-Tenant-ID` en desarrollo, o de un tenant por defecto. En test, se sobreescribe con fixtures.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| **R1 — Tenant-scope automático puede ser demasiado restrictivo**: algún caso legítimo (admin global, migración de datos) necesita operar sin tenant scope. | El método `get_by_id_without_tenant()` es explícito, difícil de llamar por accidente, y su uso debe justificarse en code review. |
| **R2 — AES-256-GCM sin rotación de claves**: la clave maestra no se rota automáticamente. | En MVP no es requisito. Si se necesita en el futuro, se puede versionar el ciphertext con un prefix de key ID. |
| **R3 — UUID vs BIGSERIAL en tablas muy grandes (>10M rows)**: el índice UUID puede fragmentarse más que un entero secuencial. | PostgreSQL maneja UUIDs eficientemente con `uuid-ossp`. Si una tabla específica escala, se evalúa `BIGSERIAL` como excepción puntual. |
| **R4 — El placeholder de tenant en C-02 puede generar datos huérfanos**: si alguien crea datos sin tenant real. | En C-03 el placeholder se reemplaza por JWT obligatorio; C-02 solo lo usa para tests y desarrollo local. Los tests verifican que el tenant-scope no permite acceder a datos de otro tenant. |
