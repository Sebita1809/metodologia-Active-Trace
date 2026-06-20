## Why

Las cátedras convocan a evaluaciones y coloquios (parciales, TPs, recuperatorios) con cupos limitados por día, pero hoy no hay forma de publicar una convocatoria, importar el padrón de candidatos habilitados, dejar que los alumnos reserven un turno respetando el cupo, ni registrar las notas resultantes. Sin esto, coordinación gestiona inscripciones y resultados por fuera del sistema, sin trazabilidad ni control de cupo.

## What Changes

- Nuevo modelo **`Evaluacion`** (E14): convocatoria a una instancia evaluativa por materia/cohorte, con `tipo` (Parcial|TP|Coloquio|Recuperatorio), `instancia` (denominación libre), `dias_disponibles`, `cupo_por_dia` y `estado` (Activa|Cerrada).
- Nuevo modelo **`ReservaEvaluacion`** (E14): reserva de turno de un alumno sobre una evaluación, con `fecha_hora` y `estado` (Activa|Cancelada).
- Nuevo modelo **`ResultadoEvaluacion`** (E14): nota final (numérica o cualitativa) de un alumno por evaluación, única por `(evaluacion_id, alumno_id)`.
- **Control de cupo por día** (regla central): al reservar, el sistema valida `count(reservas Activas para la fecha) < cupo_por_dia`; si está lleno responde **409**.
- **Unicidad de reserva activa**: un alumno no puede tener dos `ReservaEvaluacion` activas para la misma evaluación (segunda reserva → **409**).
- **Cancelación por el propio alumno**: ALUMNO cancela su reserva (Activa → Cancelada) mientras la evaluación siga Activa, liberando el cupo.
- **Importación de padrón** (F7.2): bulk-load de `alumno_id`s habilitados para una convocatoria.
- **Panel de métricas** (F7.1): total_alumnos_cargados, instancias_activas, reservas_activas, notas_registradas.
- Endpoints REST bajo `/api/v1/coloquios` (crear, listar con métricas, importar padrón, reservar, cancelar, agenda, registrar/consultar resultados).
- Nuevos permisos `coloquios:gestionar`, `coloquios:ver`, `coloquios:reservar`.
- Una migración Alembic: tablas `evaluacion`, `reserva_evaluacion`, `resultado_evaluacion` con índices tenant-scoped y constraints de unicidad.

## Capabilities

### New Capabilities
- `evaluacion`: Convocatoria a una instancia evaluativa con cupos por día; creación, listado con métricas, importación de padrón y cierre. Gobierna el cupo y el estado.
- `reserva-evaluacion`: Reserva de turno por alumno; valida cupo por día y unicidad de reserva activa (409), permite cancelación propia que libera cupo, expone la agenda consolidada.
- `resultado-evaluacion`: Registro de nota final por alumno, único por evaluación; consulta del registro académico.

### Modified Capabilities
<!-- Ninguna: C-14 introduce capabilities nuevas y solo consume FKs de C-06 (Materia, Cohorte) y C-07 (Usuario) ya existentes. -->

## Impact

- **Modelos/DB**: nuevas tablas `evaluacion`, `reserva_evaluacion`, `resultado_evaluacion` (FKs a `materia`, `cohorte`, `usuario`, `tenant`). Una migración Alembic.
- **API**: nuevo router de coloquios bajo `/api/v1/coloquios`.
- **RBAC**: alta de `coloquios:gestionar` (COORDINADOR/ADMIN), `coloquios:ver` (COORDINADOR/ADMIN/PROFESOR) y `coloquios:reservar` (ALUMNO, solo su propia reserva). Fail-closed.
- **Dependencias**: reutiliza `BaseRepository` tenant-scoped (C-02), `require_permission` (C-04), `get_current_user` (C-03), modelos de C-06/C-07. Sin cambios en esos módulos.
- **Governance**: MEDIO (lógica de dominio con control de cupo concurrente).
