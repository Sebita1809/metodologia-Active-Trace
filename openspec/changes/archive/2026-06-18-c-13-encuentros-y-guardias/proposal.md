## Why

Los profesores dictan encuentros sincrónicos (recurrentes o únicos) y los tutores cubren guardias de consulta, pero hoy no hay forma de planificarlos, registrar su realización ni dejar trazabilidad (grabaciones, estados, comentarios). Sin esto, los coordinadores no pueden auditar qué se dictó vs. qué quedó pendiente, ni publicar el calendario con grabaciones en el aula virtual.

## What Changes

- Nuevo modelo **`SlotEncuentro`** (E9): plantilla de encuentro recurrente o de fecha única por asignación/materia, con horario, día, vigencia y enlace de sala virtual.
- Nuevo modelo **`InstanciaEncuentro`** (E10): ocurrencia concreta de un encuentro con estado independiente (`Programado | Realizado | Cancelado`), grabación y comentario.
- Nuevo modelo **`Guardia`** (E11): registro de guardia de consulta por tutor, con día, horario, estado y comentarios, consultable y exportable por coordinación.
- **Creación dual de encuentros** (RN-13, excluyente): modo recurrente (`cant_semanas > 0` genera N instancias automáticamente) o modo único (`fecha_unica` genera 1 instancia sin slot).
- **Estado de instancia independiente** del slot y del resto de instancias (RN-14): editar una instancia no afecta a las demás.
- Endpoints REST: `POST /slots`, `POST /encuentros`, `PATCH /encuentros/{id}`, `GET /encuentros/html`, `GET /admin/encuentros`, `POST /guardias`, `GET /guardias`.
- Nuevo permiso `encuentros:gestionar` y reglas de acceso para guardias (registro TUTOR; consulta COORDINADOR/ADMIN).
- Generación de un bloque **HTML** (calendario + grabaciones) para incrustar en el aula virtual de Moodle.
- Una migración Alembic: tablas `slot_encuentro`, `instancia_encuentro`, `guardia` con índices tenant-scoped.

## Capabilities

### New Capabilities
- `slot-encuentro`: Plantilla de encuentro recurrente o único; valida los dos modos excluyentes (RN-13) y dispara la generación de instancias.
- `instancia-encuentro`: Ocurrencia concreta de un encuentro; estado/grabación/comentario independientes (RN-14), edición y exportación HTML para el aula virtual.
- `guardia`: Registro de guardias de consulta por tutor; consulta y exportación por coordinación.

### Modified Capabilities
<!-- Ninguna: C-13 introduce capabilities nuevas y solo consume FKs de C-06/C-07 ya existentes. -->

## Impact

- **Modelos/DB**: nuevas tablas `slot_encuentro`, `instancia_encuentro`, `guardia` (FKs a `asignacion`, `materia`, `carrera`, `cohorte`, `tenant`). Una migración Alembic.
- **API**: nuevo router de encuentros y de guardias bajo `/api/v1`.
- **RBAC**: alta del permiso `encuentros:gestionar`; reglas fail-closed para registro/consulta de guardias.
- **Integración Moodle**: fragmento HTML consumible por el aula virtual (no requiere Moodle WS, es generación local).
- **Dependencias**: reutiliza `BaseRepository` tenant-scoped (C-02), `require_permission` (C-04), `get_current_user` (C-03), modelos de C-06/C-07. Sin cambios en esos módulos.
- **Governance**: MEDIO (lógica de dominio + generación de instancias).
