## Context

La plataforma ya cuenta con: tenant isolation (C-02), auth JWT (C-03), RBAC fino `modulo:accion` (C-04) y audit log append-only (C-05). El siguiente eslabón del camino crítico es el catálogo académico base: **Carrera**, **Cohorte** y **Materia** son las entidades raíz de las que cuelgan todos los módulos de dominio (equipos, padrón, calificaciones, comunicaciones, etc.). Sin ellas, ningún change posterior puede arrancar.

Arquitectura target: Clean Architecture — Router → Service → Repository → Model. El permiso `estructura:gestionar` existe en el seed de C-04; si falta, se siembra en la Migración 004.

## Goals / Non-Goals

**Goals:**
- Crear modelos SQLAlchemy `Carrera`, `Cohorte`, `Materia` con mixin base (UUID, tenant_id, timestamps, soft delete).
- Repositories con scope de tenant siempre activo.
- Services con validación de unicidad y regla carrera-inactiva → sin cohortes abiertas.
- Routers CRUD bajo `/api/admin/` con guard `require_permission("estructura:gestionar")`.
- Migración 004 con tablas, índices únicos y constraints.
- Tests: CRUD, unicidad por tenant, aislamiento multi-tenant, estado activa/inactiva.

**Non-Goals:**
- Entidad `Dictado` o `Asignacion` — eso es C-07.
- Gestión de programas de materia (C-17) o fechas académicas (C-17).
- Frontend (C-24).
- Importación masiva de catálogo — ABM manual únicamente en este change.

## Decisions

### D-01: Catálogo único de Materia por tenant (ADR-006)

`Materia` es la definición canónica en el catálogo del tenant; no existen catálogos paralelos por carrera/cohorte. Cuando una materia se dicta en varias carreras/cohortes, la instancia es `Asignacion` (C-07), no una nueva `Materia`. Esto evita duplicar definiciones y materializa el requisito de catálogo único.

**Alternativa descartada**: `Materia` con FK a `Carrera` — fuerza duplicación cuando la misma materia aparece en varias carreras y rompe el catálogo único.

### D-02: Estado `activa/inactiva` en lugar de soft delete para control funcional

Los modelos ya tienen soft delete del mixin (auditoría append-only). El campo `estado` (activa/inactiva) es un estado funcional separado: una carrera inactiva sigue existiendo en el histórico pero bloquea la creación de nuevas cohortes abiertas. No se pueden confundir "borrado lógico" con "inactivación".

**Regla de negocio**: al intentar crear o activar una Cohorte cuya Carrera tiene `estado = Inactiva`, el servicio debe retornar HTTP 422.

### D-03: Permisos — solo ADMIN puede gestionar la estructura

El permiso `estructura:gestionar` (guard en todos los endpoints ABM) está asignado exclusivamente al rol ADMIN en la matriz de C-04. COORDINADOR puede consultar (lectura) pero no modificar el catálogo. Esto se hace declarando endpoints de lectura con `require_permission("estructura:leer")` si aplica, o sin guard si la lectura es pública dentro del tenant.

### D-04: Unicidad aplicada en DB y en Service

Índices únicos compuestos en la migración (fuerzan unicidad a nivel DB) + validación en Service antes de insertar (retorna HTTP 409 con mensaje descriptivo antes de que explote la DB). Doble protección: la DB es la fuente de verdad, el Service mejora la UX.

### D-05: Endpoints bajo `/api/admin/` — scope ADMIN explícito en la ruta

Agrupa los ABMs de catálogo bajo un prefijo que deja claro que son operaciones de administración del tenant. Facilita auditoría y distinción de scope en documentación y tests.

## Risks / Trade-offs

- **[Riesgo] Migración 004 sobre DB ya corriendo con 001-003**: la migración agrega tablas nuevas (no modifica existentes), por lo que es no destructiva. El rollback borra las tablas recién creadas.
- **[Riesgo] Permiso `estructura:gestionar` no sembrado en C-04**: si el seed de C-04 no incluyó este permiso, la Migración 004 debe agregarlo. La implementación debe verificar su existencia antes de asumir que está disponible.
- **[Trade-off] ABM manual sin import masivo**: se decidió mantener el scope acotado para no bloquear el avance del camino crítico. La importación masiva puede añadirse como un change separado cuando sea necesaria.

## Migration Plan

1. Ejecutar `Migración 004` (crea `carrera`, `cohorte`, `materia` + índices).
2. Si falta permiso `estructura:gestionar`, el data migration dentro de la misma migración lo siembra en la tabla `permiso` y lo asigna al rol `ADMIN`.
3. Rollback: `alembic downgrade -1` — borra las 3 tablas nuevas y el permiso sembrado (si aplica).

## Open Questions

*(ninguna — ADR-006 ya cerrado. Las preguntas PA-01 y PA-07 sobre cohortes/carreras quedan diferidas a C-07 donde se modela Asignacion.)*
