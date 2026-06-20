## Why

Sin un cimiento multi-tenant sólido ningún otro change del sistema puede arrancar: toda entidad del dominio lleva `tenant_id`, todo repositorio debe filtrar por tenant por defecto, y los datos PII deben estar cifrados en reposo desde el primer registro. Este change establece ese cimiento antes de que cualquier lógica de negocio o endpoint se construya sobre él.

## What Changes

- Introduce el modelo `Tenant` (raíz de todo el aislamiento) con migración Alembic 001.
- Introduce el mixin `BaseTenantModel` que aporta a todas las entidades del dominio: `id` (UUID, PK), `tenant_id` (FK → Tenant), `created_at`, `updated_at`, `deleted_at` (soft delete).
- Introduce `BaseRepository[T]`, repositorio genérico async con scope de tenant **siempre activo**: ningún query puede cruzar datos entre tenants; queries sin scope de tenant fallan en review.
- Introduce `CryptoService` (helper AES-256-GCM) para cifrar/descifrar atributos `[cifrado]` (DNI, CUIL, CBU, email PII) en reposo; nunca en logs.
- Establece la convención de migraciones Alembic: una migración por cambio de schema, script async, sin cambios manuales en producción.

## Capabilities

### New Capabilities

- `tenant-model`: Entidad `Tenant` con atributos de identificación institucional y lifecycle (activo/inactivo); raíz del aislamiento row-level.
- `base-model-mixin`: Mixin `BaseTenantModel` (UUID PK, tenant_id, timestamps, soft delete) que heredan todas las tablas del dominio.
- `repository-base`: `BaseRepository[T]` genérico con scope de tenant implícito, operaciones CRUD async, y soft delete transparente.
- `encryption-util`: `CryptoService` AES-256-GCM para cifrado/descifrado de campos PII; sin overhead de IV fijo.
- `alembic-migrations`: Convención de migraciones versionadas; migración `001_create_tenants` como primera migración del dominio.

### Modified Capabilities

<!-- Sin cambios sobre specs existentes; este change crea la base desde cero. -->

## Impact

- **Backend**: `backend/app/models/` (nuevo `tenant.py`, `base.py`), `backend/app/repositories/` (nuevo `base.py`), `backend/app/core/` (nuevo `crypto.py`), `backend/alembic/versions/` (nueva `001_create_tenants.py`).
- **Tests**: nuevos en `backend/tests/` — aislamiento multi-tenant, soft delete, cifrado round-trip, timestamps automáticos.
- **Dependencias**: no se agregan librerías nuevas (cryptography ya es una dependencia transitiva de python-jose; si no, se agrega explícitamente).
- **Sin cambios de API pública**: este change no expone endpoints; es infraestructura de persistencia pura.
- **Governance**: CRÍTICO — toda la cadena de permisos, tenancy y RBAC se apoya en este cimiento.
