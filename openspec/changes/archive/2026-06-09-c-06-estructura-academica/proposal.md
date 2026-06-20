## Why

El sistema necesita un catálogo académico base (carreras, cohortes, materias) antes de poder modelar equipos docentes, importar padrones o registrar calificaciones. Sin estas entidades raíz, ningún otro módulo del dominio puede operar: son el contexto que da sentido a cada asignación, padrón y evaluación del tenant.

## What Changes

- **Nuevo modelo `Carrera`**: programa académico del tenant, con código único por tenant, nombre y estado activa/inactiva.
- **Nuevo modelo `Cohorte`**: camada de alumnos dentro de una carrera, con nombre único por `(tenant, carrera)`, año, vigencia y estado.
- **Nuevo modelo `Materia`**: catálogo único de materias del tenant (ADR-006), con código único por tenant, nombre y estado activa/inactiva.
- **ABM de estructura académica**: endpoints REST bajo `/api/admin/carreras`, `/api/admin/cohortes`, `/api/admin/materias`, protegidos con guard `estructura:gestionar` (solo ADMIN).
- **Migración 004**: tablas `carrera`, `cohorte`, `materia` con sus índices de unicidad y FKs.
- **Regla de negocio**: una carrera inactiva no puede tener cohortes abiertas (estado Activa).

## Capabilities

### New Capabilities

- `carrera`: Modelo de Carrera y su ABM (CRUD + cambio de estado activa/inactiva) con unicidad `(tenant_id, codigo)`.
- `cohorte`: Modelo de Cohorte y su ABM con vigencia temporal, unicidad `(tenant_id, carrera_id, nombre)` y regla de bloqueo ante carrera inactiva.
- `materia`: Catálogo único de Materia por tenant y su ABM con unicidad `(tenant_id, codigo)` (ADR-006).

### Modified Capabilities

*(ninguna — este change no modifica requisitos de specs existentes)*

## Impact

- **Backend**: nuevos modelos SQLAlchemy, repositories con scope tenant, services con validaciones de unicidad, routers `POST/GET/PATCH/DELETE` bajo `/api/admin/`.
- **Migración**: `Migración 004: carrera, cohorte, materia` — debe ejecutarse sobre la DB que ya tiene las migraciones 001-003 (Tenant, RBAC, AuditLog) de C-01–C-05.
- **RBAC**: el permiso `estructura:gestionar` debe existir en el seed de roles de C-04; si aún no está, se agrega en el seed de esta migración.
- **Dependientes**: C-07 (usuarios/asignaciones), C-08 (equipos), C-09 (padrón), C-15 (avisos), C-17 (programas) y todos los módulos posteriores necesitan estas tablas.
- **No impacta**: auth, audit-log, permisos existentes.
