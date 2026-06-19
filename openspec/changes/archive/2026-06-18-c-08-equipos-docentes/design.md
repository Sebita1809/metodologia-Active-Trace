## Context

C-07 habilitó el modelo `Asignacion` con endpoints CRUD individuales (`POST/GET/PATCH/DELETE /api/asignaciones`). Un "equipo docente" no es una entidad separada — es el conjunto de asignaciones que comparten `materia_id` (y opcionalmente `carrera_id`, `cohorte_id`). Actualmente no existe lógica de negocio que opere sobre ese conjunto: las operaciones de asignación masiva, clonado entre períodos, modificación de vigencia en bloque y exportación deben hacerse una asignación a la vez.

Este cambio agrega una capa de servicio de dominio sobre `Asignacion` que el COORDINADOR necesita para la operatoria real del inicio de cuatrimestre (FL-03).

**Precedentes**: Los services existentes (`UsuarioService`, `AsignacionService`) siguen el patrón Router → Service → Repository → Model con inyección de dependencias vía FastAPI `Depends()`. C-08 sigue el mismo patrón.

**Constraints**:
- Sin migraciones de BD — C-08 es 100% lógica de aplicación
- Sin nuevos modelos — opera sobre `Asignacion`, `Materia`, `Carrera`, `Cohorte`, `Usuario`, `UmbralMateria`
- Las operaciones masivas deben ser transaccionales (all-or-nothing)
- Toda escritura genera auditoría con acción `ASIGNACION_MODIFICAR`

## Goals / Non-Goals

**Goals:**
- Vista de "mis equipos" para el docente autenticado (F4.2)
- Consulta de equipo completo por materia para COORDINADOR/ADMIN (F4.3)
- Asignación masiva transaccional de N docentes (F4.4)
- Clonación de equipo entre cohortes con ajuste de fechas (F4.5, RN-12)
- Modificación de vigencia en bloque (F4.6)
- Exportación de equipo a archivo descargable (F4.7)
- Validación de soft-delete de materia/carrera/cohorte con asignaciones activas
- Creación automática de `UmbralMateria` al asignar docentes (umbral default 60%)
- Eventos de auditoría para toda operación de escritura

**Non-Goals:**
- Modificar el CRUD individual de `Asignacion` existente — los endpoints de C-07 no se tocan
- Interfaz de usuario — C-08 es puramente backend (el frontend será C-23)
- Notificaciones o comunicaciones al docente cuando se le asigna — eso corresponde a C-12/C-15
- Importación de padrón Moodle — eso corresponde a C-09
- Liquidaciones o cálculos de honorarios — eso corresponde a C-18

## Decisions

### D1: Nuevo servicio `EquipoDocenteService` separado de `AsignacionService`

**Decisión**: Crear `backend/app/services/equipos/equipo_docente_service.py` como servicio independiente.

**Rationale**: Las operaciones de C-08 son de dominio (gestión de equipos docentes), no de CRUD de asignaciones. Mezclarlas en `AsignacionService` inflaría ese servicio con lógica que opera sobre conjuntos de asignaciones en vez de una asignación individual. Sigue el patrón establecido de un service por dominio (`AsignacionService`, `UsuarioService`, `AuthService`, etc.).

**Alternativa considerada**: Extender `AsignacionService` con métodos masivos. Descartado porque el service ya maneja CRUD individual y las operaciones de equipo tienen precondiciones y efectos secundarios distintos (transacciones multi-fila, auditoría de conjunto, UmbralMateria).

### D2: Nuevo router `/api/equipos/*`

**Decisión**: Crear `backend/app/api/v1/routers/equipos.py` registrado bajo `/api/equipos`.

**Rationale**: Separación de concerns. El router existente `asignaciones.py` expone CRUD individual. El nuevo router expone operaciones de dominio de alto nivel. Ambos pueden coexistir y usar el mismo `AsignacionRepository`.

```
/api/equipos/
├── GET  /mis-equipos                    → EquipoDocenteService.get_mis_equipos()
├── GET  /materias/{materia_id}          → EquipoDocenteService.get_equipo_por_materia()
├── POST /asignacion-masiva              → EquipoDocenteService.asignacion_masiva()
├── POST /clonar                         → EquipoDocenteService.clonar_equipo()
├── PATCH /vigencia                      → EquipoDocenteService.modificar_vigencia()
└── GET  /{materia_id}/exportar          → EquipoDocenteService.exportar_equipo()
```

### D3: Asignación masiva transaccional con validación previa

**Decisión**: Validar TODOS los inputs antes de INSERTAR cualquier asignación. Si algún docente no existe, está inactivo, o las fechas son inválidas → 422 sin crear nada.

**Rationale**: Las validaciones parciales (crear algunas, fallar otras) dejarían el sistema en estado inconsistente desde la perspectiva del usuario. El COORDINADOR espera que "asignar estos 20 docentes" sea atómico.

**Flujo**:
```python
# 1. Validar materia/carrera/cohorte existen en el tenant
# 2. Validar rol contra enum conocido
# 3. Validar que desde <= hasta
# 4. Validar que TODOS los usuario_id existen y están activos
# 5. Validar responsable_id si se provee (existe, activo, mismo tenant)
# 6. Crear todas las asignaciones en una transacción
# 7. Por cada asignación con rol docente y materia_id, crear UmbralMateria (60%)
# 8. Registrar evento de auditoría
# 9. Commit
```

### D4: Clonación con duplicación lógica no raw-SQL

**Decisión**: Leer todas las asignaciones vigentes del origen, crear nuevas instancias en Python con nuevos UUIDs y fechas del destino, persistir en una transacción.

**Rationale**: Aunque podría hacerse con SQL directo (`INSERT INTO ... SELECT ...`), la capa de aplicación permite:
- Validar que origen y destino son distintos
- Validar tenencia (ambos en el mismo tenant)
- Aplicar hooks automáticos (ej. creación de UmbralMateria)
- Mantener el patrón de repositorio consistente

### D5: Exportación como CSV con streaming

**Decisión**: Generar CSV en memoria usando `csv.writer` sobre `io.StringIO`, retornar como `StreamingResponse` con `text/csv` y headers de descarga.

**Rationale**: Es el formato más universal y no requiere dependencias externas. El volumen de datos (equipo docente de una materia) es pequeño — no justifica una librería de reporting.

### D6: Validación de desactivación en services de estructura (C-06)

**Decisión**: Modificar `MateriaService.update()` y el método de soft-delete para que, antes de marcar `estado = Inactiva`, consulte `AsignacionRepository.asignaciones_activas_para_materia(materia_id)`. Si hay asignaciones vigentes → levantar excepción → 409 Conflict.

**Rationale**: Es la validación más cercana al punto de cambio. C-07 delegó expresamente esta responsabilidad a C-08. El service de estructura ya existe y es el lugar natural para esta guarda.

### D7: UmbralMateria auto-creación como hook post-asignación

**Decisión**: Al crear una asignación (tanto individual vía `AsignacionService` como masiva vía `EquipoDocenteService`) con rol PROFESOR o TUTOR y `materia_id` definido, crear automáticamente un `UmbralMateria` con `umbral_pct = 60`.

**Rationale**: Los umbrales son parte del setup del equipo docente — cada docente necesita uno para que el módulo de calificaciones (C-10) pueda operar. Automatizar su creación evita que el COORDINADOR tenga que hacerlo manualmente.

**Ubicación**: `AsignacionService.crear()` en C-07 se extiende para incluir este hook. `EquipoDocenteService` también lo implementa al crear asignaciones masivas (reutiliza `AsignacionRepository.crear()` que internamente podría no tener el hook, por lo que el service de equipo lo hace explícitamente).

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|------------|
| **[R1] Asignación masiva con 500+ docentes**: Timeout o uso excesivo de memoria por la transacción gigante | `POST /api/equipos/asignacion-masiva` acepta hasta 200 docentes por request. Si el COORDINADOR necesita más, hace múltiples requests. El service valida el tamaño del array al inicio. |
| **[R2] Clonación duplica UmbralMateria**: Al clonar asignaciones, se crearían UmbralMateria duplicados para el destino | La creación de UmbralMateria se hace en el hook post-creación. Si la asignación se clona, se crea un UmbralMateria nuevo para la copia (con el destino), no se duplica el existente. Es el comportamiento esperado. |
| **[R3] Modificación de vigencia en bloque afecta asignaciones incorrectas**: Si el filtro es muy amplio, podría modificar asignaciones no deseadas | El endpoint requiere `materia_id` obligatorio. `cohorte_id` y `carrera_id` son opcionales pero se recomienda usarlos. El response incluye conteo de asignaciones afectadas para que el usuario confirme. |
| **[R4] Exportación falla si el equipo es muy grande**: Materias con 50+ docentes + comisiones | El volumen de datos de un equipo docente es pequeño (< 100 registros). CSV en memoria no tiene problemas. Si en futuro escala, se puede paginar. |
| **[R5] La validación de desactivación C-06 es un cambio cross-change**: Modificar services de C-06 desde un change C-08 | Está expresamente delegado en C-07 design.md §Riesgos: "Esto se aborda en C-08 (equipos-docentes) que gestiona el ciclo de vida de asignaciones." Es un cambio localizado en los services de estructura. |

## Open Questions

- **Q1**: ¿El formato de exportación (F4.7) debe ser CSV, XLSX o ambos? Por ahora se define CSV como mínimo viable. Si se necesita XLSX, se agrega en una iteración futura.
- **Q2**: ¿La asignación masiva debe soportar distintos roles dentro de un mismo request (ej. 10 PROFESOR + 5 TUTOR en un solo POST)? Por ahora se define un solo rol por request. Si se necesita multi-rol, se agrega como extensión.
- **Q3**: ¿Clonación debe permitir excluir ciertos roles? Por ahora clona todos los roles del origen. Si se necesita filtro, se agrega como parámetro opcional.
