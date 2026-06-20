## Context

C-22 implementó la feature `gestion-comision` para PROFESOR/TUTOR. El backend de coordinación está 100% operativo desde C-08 (equipos), C-13 (encuentros), C-14 (coloquios), C-15 (avisos), C-16 (tareas) y C-12 (aprobación de comunicaciones). C-23 expone todo eso en la UI bajo una feature `coordinacion` protegida por `RequireRole(['COORDINADOR', 'ADMIN'])`, con extensiones menores a features existentes.

Frontend ya tiene: shell (C-21), cliente HTTP centralizado, TanStack Query configurado, Zod, Tailwind, feature-based modules, route guards.

## Goals / Non-Goals

**Goals:**
- Proveer UI completa para el flujo de setup de cuatrimestre (FL-03): equipos, clonado, vigencias
- ABM de avisos con scope + ack (F3.5, FL-09)
- Workflow de tareas internas con vista docente y vista coordinador (F8.1–F8.3, FL-05)
- Vista supervisora de encuentros del tenant + guardias (F6.5, F6.6)
- Panel de coloquios: convocatorias, importación de alumnos, agenda de reservas, resultados (F7.1–F7.5)
- Monitor general de alumnos del tenant (F2.7)
- Cola de aprobación de comunicaciones para COORDINADOR (F3.3, FL-04B)
- Extensión del monitor de seguimiento con filtro de rango de fechas para COORDINADOR (F2.9)

**Non-Goals:**
- Ningún cambio de backend — todos los endpoints necesarios ya existen
- Gestión de liquidaciones, facturas, estructura académica ni auditoría (C-24)
- Perfil de usuario o mensajería interna (C-20 ya implementado)
- Nueva lógica de importación (ya en C-22)

## Decisions

### 1 — Feature única `coordinacion` para todos los módulos

Una sola feature `features/coordinacion/` con subdirectorios por módulo (`equipos/`, `avisos/`, `tareas/`, `encuentros/`, `coloquios/`, `monitor-general/`) en lugar de features separadas.

**Razón**: todos los módulos comparten el mismo guard de rol (`COORDINADOR|ADMIN`) y el mismo entry point de navegación. Una feature los agrupa sin crear rutas de router duplicadas ni nav entries dispersos. El tamaño por archivo sigue por debajo de 200 LOC con la subdivisión interna.

### 2 — Tareas: ruta compartida con acceso por rol

`/tareas` es accesible a TUTOR, PROFESOR, COORDINADOR y ADMIN, pero la view varía: TUTOR/PROFESOR ven solo sus propias tareas; COORDINADOR/ADMIN ven la vista global con filtros.

**Razón**: F8.1 y F8.3 son el mismo módulo con diferente scope. Un solo `TareasPage` con bifurcación condicional según `currentUser.roles` es más limpio que dos rutas/pages redundantes.

### 3 — Aprobación de comunicaciones en `coordinacion`, no en `gestion-comision`

El panel de aprobación (cola de lotes pendientes, aprobar/cancelar) vive en `features/coordinacion/comunicaciones/` aunque consume los mismos endpoints de `/api/comunicaciones`.

**Razón**: la acción de aprobar es exclusiva de COORDINADOR/ADMIN — mezclarla en la feature `gestion-comision` (PROFESOR) rompe la separación de roles. El PROFESOR ya tiene el panel de tracking en C-22; el COORDINADOR tiene el panel de aprobación en C-23. Ambos usan el mismo hook `useComunicaciones` del shared layer.

### 4 — Monitor general como nueva feature, monitor de seguimiento extendido por delta

F2.7 (monitor global, todos los alumnos del tenant) es una vista distinta de F2.8 (alumnos de la comisión del docente): distinto endpoint, distintos filtros, distinto scope. Se implementa como módulo nuevo `monitor-general` dentro de `coordinacion`.

F2.9 solo agrega un filtro de rango de fechas al monitor de seguimiento existente, visible condicionalmente para COORDINADOR/ADMIN. Se implementa como una extensión del hook `useMonitorSeguimiento` con parámetro `fecha_desde`/`fecha_hasta` opcionales.

### 5 — Coloquios: feature completa con submódulo por rol

El panel de coloquios (F7.1–F7.5) tiene tres vistas: métricas, convocatorias (COORDINADOR) y agenda/resultados (COORDINADOR/ADMIN). Se implementan como tabs dentro de `ColoquiosPage` bajo `/coordinacion/coloquios`.

### 6 — Endpoints de backend a consumir

| Módulo | Endpoints clave |
|--------|----------------|
| Equipos | `GET/POST /api/v1/asignaciones`, `POST /masiva`, `POST /clonar`, `PUT /{id}/vigencia`, `GET /exportar` |
| Avisos | `GET/POST/PUT/DELETE /api/v1/avisos`, `POST /api/v1/avisos/{id}/ack` |
| Tareas | `GET/POST /api/v1/tareas`, `PUT /api/v1/tareas/{id}`, `POST /api/v1/tareas/{id}/comentarios` |
| Encuentros | `GET /api/v1/encuentros` (con param `?tenant=true`), `GET/POST /api/v1/guardias` |
| Coloquios | `GET/POST /api/v1/evaluaciones`, `GET /api/v1/reservas`, `GET /api/v1/resultados` |
| Monitor general | `GET /api/v1/calificaciones/monitor` |
| Comunicaciones aprobación | `GET /api/v1/comunicaciones?estado=PENDIENTE`, `PUT /api/v1/comunicaciones/lotes/{id}/aprobar`, `PUT /api/v1/comunicaciones/lotes/{id}/cancelar` |

## Risks / Trade-offs

- [Volumen de tareas ~55] La feature tiene muchos módulos → riesgo de scope creep en una sesión. Mitigation: tasks granulares por módulo, el agente marca [x] incrementalmente.
- [APIs no documentadas inline] Los endpoints de C-08 a C-16 fueron implementados en sesiones anteriores; si algún path difiere del documentado aquí, el agente debe leer `backend/app/api/v1/routers/` antes de hardcodear URLs. Mitigation: el skill `openspec-apply-change` instruye a leer los routers antes de crear services.
- [Monitor general endpoint] F2.7 describe un monitor "de todos los alumnos del tenant" — el endpoint exacto puede ser `GET /analisis/monitor` o puede requerir un query param. El agente debe verificar en el router antes de implementar el hook.
- [Coloquios y ALUMNO] F7.4 menciona que los ALUMNOs reservan turnos — esa funcionalidad es fuera del scope de C-23 (solo la vista supervisora del COORDINADOR).

## Open Questions

- **Endpoint del monitor general**: ¿es `GET /api/v1/calificaciones/monitor` o un endpoint distinto bajo `/analisis/`? El agente debe leer `backend/app/api/v1/routers/` para confirmar antes de implementar.
- **Exportar equipos**: el endpoint `GET /asignaciones/exportar` puede devolver CSV directo o una URL de descarga — verificar el router de C-08.
