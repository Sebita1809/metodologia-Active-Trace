## 1. Setup de infraestructura

- [x] 1.1 Agregar dependencia `cryptography` a `backend/pyproject.toml` (AES-256-GCM)
- [x] 1.2 Configurar Alembic: `alembic init` en `backend/`, `alembic.ini`, `env.py` dinámico con auto-detección de modelos desde `app.models`
- [x] 1.3 Crear archivo `app/models/__init__.py` que exponga todos los modelos para Alembic autogenerate

## 2. BaseModel mixin (core-models)

- [x] 2.1 Crear `app/models/base.py` con `BaseModel` declarative base que incluya:
  - `id`: UUID v4 como PK con `default=uuid.uuid4`
  - `tenant_id`: UUID, FK → Tenant, NOT NULL
  - `created_at`: DateTime with timezone, server_default=now()
  - `updated_at`: DateTime with timezone, onupdate=now()
  - `deleted_at`: DateTime with timezone, nullable=True (soft delete marker)
- [x] 2.2 Configurar `__tablename__` automático desde el nombre de la clase (snake_case)
- [x] 2.3 Agregar `__mapper_args__` con `polymorphic_identity` para soporte futuro si es necesario

## 3. Modelo Tenant (tenant-model)

- [x] 3.1 Crear `app/models/tenant.py` con:
  - `id`, `tenant_id` (auto-referencia: el tenant es su propio tenant)
  - `nombre`: string, NOT NULL
  - `codigo`: string, unique, NOT NULL
  - `estado`: enum `TenantEstado (Activo | Inactivo)`
  - `config`: JSONB, nullable (configuración específica del tenant)
  - Unique constraint en `codigo`
- [x] 3.2 Crear `app/schemas/tenant.py` con Pydantic schemas:
  - `TenantCreate`, `TenantResponse`, `TenantUpdate`
  - Config `extra='forbid'` en todos
- [x] 3.3 Generar migración Alembic `001_tenant` con autogenerate

## 4. Utilidad AESCipher (encryption-at-rest)

- [x] 4.1 Crear `app/core/security.py` con clase `AESCipher`:
  - `encrypt(plaintext: str) -> str`: cifra con AES-256-GCM, output base64(nonce + ciphertext + tag)
  - `decrypt(ciphertext_b64: str) -> str`: descifra y verifica integridad, raise en error
  - Clave leída de `settings.ENCRYPTION_KEY` (32 bytes exactos)
- [x] 4.2 Agregar `ENCRYPTION_KEY` a `app/core/config.py` (Settings)

## 5. Tenant context resolution (tenancy)

- [x] 5.1 Crear `app/core/tenancy.py` con función `get_tenant_context(request) -> UUID`:
  - En desarrollo: leer de header `X-Tenant-ID`; si no existe, usar tenant por defecto
  - Es placeholder hasta C-03 (JWT real reemplazará esto)
- [x] 5.2 Crear dependency `get_current_tenant` en `app/core/dependencies.py`

## 6. BaseRepository con tenant scoping (data-access-layer)

- [x] 6.1 Crear `app/repositories/__init__.py`
- [x] 6.2 Crear `app/repositories/base.py` con clase genérica `BaseRepository[T]`:
  - `__init__(self, db: AsyncSession, tenant_id: UUID)`
  - `async create(self, data: dict) -> T`
  - `async get(self, id: UUID, *, include_deleted: bool = False) -> T | None`
  - `async list(self, **filters) -> list[T]`
  - `async update(self, id: UUID, data: dict) -> T`
  - `async delete(self, id: UUID) -> None` (soft delete: UPDATE deleted_at=now())
  - `async get_by_id_without_tenant(self, id: UUID) -> T | None` (método explícito sin scope de tenant)
  - Todos los métodos CRUD aplican `WHERE tenant_id = :tenant_id AND deleted_at IS NULL`

## 7. Tests

- [x] 7.1 Configurar fixtures de test: dos tenants distintos (`tenant_a`, `tenant_b`), sesión async de test
- [x] 7.2 Test: BaseModel mixin (columnas existen, UUID se genera, timestamps se actualizan)
- [x] 7.3 Test: Tenant model (creación, unique code, deactivate)
- [x] 7.4 Test: Aislamiento multi-tenant (tenant A no ve datos de tenant B vía repository)
- [x] 7.5 Test: Soft delete (get/list no retornan eliminados, delete lógico funciona)
- [x] 7.6 Test: AESCipher round-trip (encrypt → decrypt devuelve original)
- [x] 7.7 Test: AESCipher con datos vacíos y valores nulos (empty string, None raise ValueError)
- [x] 7.8 Test: AESCipher con ciphertext alterado (debe fallar con error de integridad)
- [x] 7.9 Test: BaseRepository create, get, list, update, delete (happy path)
- [x] 7.10 Test: BaseRepository cross-tenant isolation (get de otro tenant retorna None)
- [x] 7.11 Test: BaseRepository `get_by_id_without_tenant` funciona para admin
