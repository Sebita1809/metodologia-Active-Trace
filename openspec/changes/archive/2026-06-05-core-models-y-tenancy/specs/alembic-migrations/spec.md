## ADDED Requirements

### Requirement: Migración 001 crea la tabla tenants
El sistema SHALL incluir una migración Alembic (`001_create_tenants`) que crea la tabla `tenants` con las columnas: `id` (UUID, PK), `slug` (text, unique, NOT NULL), `nombre` (text, NOT NULL), `activo` (boolean, NOT NULL, default True), `created_at` (timestamptz, NOT NULL), `updated_at` (timestamptz, NOT NULL), `deleted_at` (timestamptz, nullable). La migración SHALL incluir función `downgrade` que elimina la tabla.

#### Scenario: upgrade crea la tabla tenants
- **WHEN** se ejecuta `alembic upgrade head` en una base de datos vacía
- **THEN** la tabla `tenants` existe con todas las columnas y constraints definidos

#### Scenario: downgrade elimina la tabla tenants
- **WHEN** se ejecuta `alembic downgrade -1` después del upgrade
- **THEN** la tabla `tenants` ya no existe en la base de datos

### Requirement: Migraciones Alembic son async
El sistema SHALL configurar Alembic para usar el engine async de `core/database.py`. El script `env.py` SHALL correr las migraciones via `asyncio.run(run_async_migrations())` usando `AsyncConnection`.

#### Scenario: alembic upgrade corre sin errores en entorno async
- **WHEN** se ejecuta `alembic upgrade head` con el engine async configurado
- **THEN** la migración completa sin errores de event loop ni de driver

### Requirement: Una migración por cambio de schema
El sistema SHALL establecer la convención de que cada cambio de schema del dominio genera una migración separada con nombre descriptivo (`NNN_descripcion.py`). NUNCA se acumulan cambios no relacionados en una sola migración.

#### Scenario: migración tiene número secuencial y descripción
- **WHEN** se lista el historial de Alembic
- **THEN** cada migración tiene un identificador único y un mensaje descriptivo del cambio de schema
