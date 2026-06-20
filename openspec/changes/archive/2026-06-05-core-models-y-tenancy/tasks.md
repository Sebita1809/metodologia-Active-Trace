## 1. Dependencia de cifrado

- [x] 1.1 Verificar que `cryptography` está en `backend/pyproject.toml`; si no, agregarlo como dependencia directa

## 2. Modelo Tenant y BaseTenantModel

- [x] 2.1 (RED) Escribir `tests/test_tenant_model.py`: test que instancia un `Tenant` con `slug`, `nombre`, `activo=True` y verifica que persiste con UUID autogenerado, `created_at` y `updated_at`
- [x] 2.2 (GREEN) Implementar `app/models/base.py` con `BaseTenantModel`: columnas `id` (UUID, server_default=gen_random_uuid()), `tenant_id` (UUID, FK → tenants, NOT NULL), `created_at` (timestamptz, server_default=now()), `updated_at` (timestamptz, onupdate), `deleted_at` (timestamptz, nullable)
- [x] 2.3 (GREEN) Implementar `app/models/tenant.py` con clase `Tenant(Base)` (no hereda `BaseTenantModel`): columnas `id`, `slug` (unique), `nombre`, `activo` (default True), `created_at`, `updated_at`, `deleted_at`
- [x] 2.4 (TRIANGULATE) Agregar test de unicidad de slug: intentar crear dos tenants con el mismo slug debe lanzar error de integridad; agregar test de `activo=False` persistiendo correctamente

## 3. Migración Alembic 001

- [x] 3.1 Crear `alembic/versions/001_create_tenants.py` con `upgrade()` que crea la tabla `tenants` (todas las columnas del modelo, índice único en `slug`) y `downgrade()` que la elimina con `drop_table`
- [x] 3.2 (RED) Escribir `tests/test_alembic.py`: test que verifica que la tabla `tenants` existe después de que el fixture de test aplica el schema; usa `inspect(engine)` async
- [x] 3.3 (GREEN) Ajustar `alembic/env.py` para usar engine async de `core/database.py`; confirmar que `alembic upgrade head` en entorno de dev corre sin error

## 4. BaseRepository genérico

- [x] 4.1 (RED) Escribir `tests/test_repository_base.py`: crear un modelo de test concreto que herede `BaseTenantModel`, instanciar `BaseRepository` con `tenant_id=T1`, verificar que `list()` con datos de T1 y T2 solo devuelve T1
- [x] 4.2 (GREEN) Implementar `app/repositories/base.py` con `BaseRepository[T]`: constructor recibe `session: AsyncSession` y `tenant_id: UUID`; método `_base_query()` aplica `filter(tenant_id == ..., deleted_at IS NULL)`; métodos `get(id)`, `list(**filters)`, `create(obj)`, `update(id, data)`, `soft_delete(id)`
- [x] 4.3 (TRIANGULATE) Agregar tests: (a) `get` de registro de otro tenant retorna `None`; (b) `soft_delete` de registro propio marca `deleted_at`; (c) `soft_delete` de registro ajeno no afecta nada; (d) `list()` excluye registros soft-deleted

## 5. CryptoService

- [x] 5.1 (RED) Escribir `tests/test_crypto.py`: test de round-trip `decrypt(encrypt(texto)) == texto`; test de dos encrypts del mismo texto producen resultados distintos; test de ciphertext alterado lanza excepción
- [x] 5.2 (GREEN) Implementar `app/core/crypto.py` con `CryptoService`: `encrypt(plaintext: str) -> str` (AES-256-GCM, IV 12 bytes aleatorio, resultado `base64url(iv || ciphertext || tag)`); `decrypt(ciphertext: str) -> str`; la clave proviene de `settings.ENCRYPTION_KEY` (32 bytes decodificados de hex)
- [x] 5.3 (GREEN) Actualizar `core/config.py`: agregar campo `ENCRYPTION_KEY: str` con validador que verifica que tiene exactamente 64 caracteres hex (= 32 bytes)
- [x] 5.4 (TRIANGULATE) Agregar test: clave de longitud incorrecta en `Settings` lanza `ValidationError` antes de llegar al código de cifrado

## 6. Verificación final

- [x] 6.1 Ejecutar suite completa de tests (`pytest`) y confirmar verde: tenant model, migración, repository aislamiento, crypto round-trip
- [x] 6.2 Confirmar que ningún archivo `.py` nuevo supera 500 LOC
- [x] 6.3 Verificar que `tests/conftest.py` tiene fixture de `tenant_id` de test y fixture de sesión de DB de test reutilizable por C-03/C-04
