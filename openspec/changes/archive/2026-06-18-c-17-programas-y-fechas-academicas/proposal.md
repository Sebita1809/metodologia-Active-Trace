## Why

Los programas oficiales de las materias y las fechas de las instancias evaluativas (parciales, TPs, coloquios) hoy viven dispersos fuera de la plataforma. Centralizarlos por materia × carrera × cohorte (programas) y por materia × cohorte × instancia (fechas) los hace accesibles a los actores autorizados, y permite generar un fragmento listo para publicar en el aula virtual del LMS (F5.4).

## What Changes

- Nuevo modelo `ProgramaMateria` (E16): documento oficial por combinación materia × carrera × cohorte, con `titulo` y `referencia_archivo` (cadena opaca a un servicio de almacenamiento externo — sin lógica de upload de binarios en este change).
- Nuevo modelo `FechaAcademica` (E15): instancia evaluativa por materia × cohorte × `tipo` × `numero`, con `tipo` enum (Parcial | TP | Coloquio | Recuperatorio), `periodo`, `fecha` y `titulo`.
- Nuevo enum `TipoFechaAcademica` (StrEnum → VARCHAR + CheckConstraint, consistente con `EstadoTarea`).
- Nueva API `/api/v1/programas`: alta/asociación (crear o reemplazar para una combinación) y consulta, bajo el permiso `estructura:gestionar`.
- Nueva API `/api/v1/fechas-academicas`: CRUD completo, listado tabular por materia × cohorte y endpoint read-only de fragmento LMS (F5.4), bajo `estructura:gestionar`.
- Nueva migración `015_programas_fechas_academicas.py` (revises 014): tablas `programa_materia` y `fecha_academica` + seed RBAC `estructura:gestionar`.

## Capabilities

### New Capabilities
- `programa-materia`: alta/asociación, reemplazo y consulta del programa oficial de una materia para una combinación carrera × cohorte, referenciando un archivo de almacenamiento externo de forma opaca.
- `fecha-academica`: CRUD de fechas de instancias evaluativas por materia × cohorte × tipo × número, con listado tabular y generación de un fragmento de contenido para el aula virtual del LMS.

### Modified Capabilities
(ninguna — no se modifican specs existentes)

## Impact

- **Modelos nuevos**: `backend/app/models/programa_materia.py`, `backend/app/models/fecha_academica.py` (+ enum), registrados en `app/models/__init__.py`.
- **Repositories nuevos**: `programa_materia_repository.py`, `fecha_academica_repository.py`.
- **Schemas nuevos**: `app/schemas/programas.py`, `app/schemas/fechas_academicas.py`.
- **Services nuevos**: `programa_materia_service.py`, `fecha_academica_service.py`.
- **Routers nuevos**: `app/api/v1/routers/programas.py`, `app/api/v1/routers/fechas_academicas.py`, registrados en `app/main.py`.
- **Migración nueva**: `backend/alembic/versions/015_programas_fechas_academicas.py` (revises 014).
- **RBAC**: nuevo permiso `estructura:gestionar` (COORDINADOR, ADMIN) sembrado por tenant.
- **Dependencias**: requiere C-06 (estructura académica: `materias`, `carreras`, `cohortes`). FKs `ondelete=RESTRICT` hacia esas tablas.
- **Governance**: BAJO (CRUD sobre catálogo académico; sin PII ni dinero). Autonomía total si pasan los tests.
