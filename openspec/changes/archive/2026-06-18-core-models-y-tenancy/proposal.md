## Why

activia-trace es una plataforma multi-tenant desde el día 0: cada institución es un tenant aislado. Sin embargo, el foundation (C-01) solo dejó el esqueleto de la app, la conexión a DB y el health check. No existe aún el concepto de **Tenant** como entidad, no hay un mecanismo de aislamiento row-level, no hay mixins base para los modelos del dominio, no hay un repository genérico que filtre por tenant automáticamente, y no hay utilidad de cifrado en reposo para PII.

Este change construye la **base estructural** sobre la que se apoyan todos los demás módulos del dominio. Sin esto, ningún modelo de negocio (C-03 en adelante) puede existir con las garantías de seguridad y aislamiento que el producto exige.

## What Changes

- **Modelo `Tenant`**: entidad raíz que representa una institución. Primer modelo del sistema, primera migración Alembic.
- **Mixin base (`BaseModel`)**: todo modelo del dominio hereda de este mixin que aporta:
  - `id`: UUID v4 como PK
  - `tenant_id`: FK → Tenant, obligatorio en todas las tablas de datos
  - `created_at`, `updated_at`: timestamps automáticos
  - `deleted_at`: soft delete (nulo = vigente, no nulo = eliminado lógicamente)
- **Repository genérico `BaseRepository`**: wrapping de SQLAlchemy con:
  - `tenant_id` inyectado automáticamente en cada query (scope de tenant siempre activo)
  - CRUD básico con soft delete (`create`, `get`, `list`, `update`, `delete` lógico)
  - Filtro por tenant implícito: el desarrollador no puede olvidarse de scoping
  - Método `list_all_without_tenant()` explícito para cruces controlados (uso muy restringido, solo para tenant-scope administrativo)
- **Utilidad `AESCipher`**: cifrado/descifrado AES-256-GCM para atributos marcados como `[cifrado]` (DNI, CUIL, CBU, email, etc.)
- **Setup Alembic**: `alembic.ini`, `env.py` dinámico con detección automática de modelos, y primera migración `001_tenant`
- **Tests**:
  - Aislamiento multi-tenant (tenant A no ve datos de tenant B)
  - Soft delete: `get` no retorna eliminados, `list` no los incluye, `delete` lógico funciona
  - Mixin timestamps se actualizan correctamente
  - Cifrado round-trip (encriptar → desencriptar devuelve el original)
  - `AESCipher` con datos vacíos, valores nulos y binary

## Capabilities

### New Capabilities
- `tenant-model`: Entidad Tenant como raíz del modelo. Representa una institución/tenant en el sistema, con su configuración básica y ciclo de vida.
- `core-models`: Mixin base (`BaseModel`) que provee UUID PK, `tenant_id`, timestamps y soft delete. Todos los modelos del dominio lo heredan. Contrato estructural del modelo de datos.
- `data-access-layer`: Repository genérico (`BaseRepository`) con scope de tenant siempre activo, CRUD con soft delete, y método explícito para consultas sin tenant. Es la capa de acceso a datos que todos los demás módulos usan.
- `encryption-at-rest`: Utilidad AES-256-GCM para cifrado simétrico de PII en reposo. Provee cifrado/descifrado con clave gestionada vía variable de entorno `ENCRYPTION_KEY`.

### Modified Capabilities
- *(Ninguna — los specs existentes de C-01 son infraestructura base que no cambian)*

## Impact

- **Backend**: se crean `app/models/tenant.py`, `app/models/base.py`, `app/repositories/base.py`, `app/core/security.py` (con AESCipher), `app/core/tenancy.py`
- **Infra**: nueva variable de entorno `ENCRYPTION_KEY` (exactamente 32 chars para AES-256). Setup completo de Alembic (`alembic/`, `alembic.ini`).
- **Dependencias**: `cryptography` library (AES-256-GCM) se agrega a `pyproject.toml` si no está ya.
- **Test DB**: se necesita fixture de dos tenants para probar aislamiento multi-tenant.
