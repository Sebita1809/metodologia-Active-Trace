## Context

C-21 entregó el shell del frontend: scaffolding React 18 + TS + Vite, Tailwind, TanStack Query, React Hook Form + Zod, cliente Axios centralizado (`shared/services/api.ts`) con refresh transparente, autenticación, `session-management`, `route-guards` y `app-shell-navigation`. La estructura actual de `frontend/src/` es feature-based: `features/auth/`, `features/dashboard/`, `shared/{components,hooks,services}` y `router/`.

El backend ya expone los contratos que C-22 consume:
- **Calificaciones + umbral (C-10)** bajo `/api/calificaciones`: `POST /preview`, `POST /import` (multipart, body JSON en form field `request`), `POST /finalizacion-preview`, `GET /` (por `asignacion_id`), `GET`/`PUT /umbral`.
- **Análisis (C-11)** bajo `/api/v1/analisis`: `GET /atrasados`, `/ranking`, `/notas-finales`, `/reporte`, todos por `asignacion_id`.
- **Comunicaciones (C-12)**: `POST /preview`, `POST /` (encolar lote, devuelve `lote_id`), `GET /` (cola por `lote_id` / `estado`), con estados Pendiente → Enviando → OK/Fallido/Cancelado procesados por el worker.

C-22 es una capa de presentación pura. No agrega endpoints ni toca la DB. Governance del dominio: **BAJO** (autonomía total si pasan los tests). Restricción transversal: identidad/roles/tenant salen exclusivamente del JWT; `asignacion_id` y `materia_id` son datos de negocio enviados como query/form, nunca identidad.

## Goals / Non-Goals

**Goals:**
- Implementar la feature `gestion-comision` que cubre FL-02 (importar → analizar → comunicar) y F2.8 (monitor de seguimiento) para PROFESOR/TUTOR.
- Todo el acceso a datos pasa por hooks de TanStack Query envolviendo servicios tipados que usan el cliente Axios compartido.
- Tracking de estados de comunicación en tiempo real mediante polling de la cola por `lote_id`.
- Cobertura de tests de componentes e integración con mocks de API (sin DB real, sin backend levantado).

**Non-Goals:**
- No se modifica ningún endpoint ni schema del backend.
- No se cubren las vistas de COORDINADOR/ADMIN del monitor general (F2.7/F2.9) ni la aprobación de lotes (F3.3) — corresponden a otro change de presentación.
- No se implementa WebSocket/SSE para el tracking; se usa polling (el worker es asincrónico y el contrato actual es REST).
- No se aborda la integración Docker/Easypanel del servicio frontend más allá del dev server.
- No se construye un design system nuevo: se reutilizan los tokens/componentes de `shared/` establecidos en C-21.

## Decisions

**1. Una feature `gestion-comision` que orquesta sub-vistas, en vez de seis features separadas.**
Las seis capacidades del proposal (`gestion-comision-ui`, `importacion-calificaciones-ui`, `umbral-configuracion-ui`, `analisis-academico-ui`, `monitor-seguimiento-ui`, `comunicacion-atrasados-ui`) son cohesivas alrededor de una misma asignación y comparten el contexto `asignacion_id` seleccionado. Se implementan como un único módulo `features/gestion-comision/` con sub-carpetas por área (`components/import`, `components/analisis`, `components/comunicacion`, `components/seguimiento`), hooks y servicios agrupados por dominio de API. Alternativa descartada: una feature por capacidad → duplicaría el manejo de la asignación seleccionada y fragmentaría tests cohesivos.

**2. Servicios tipados por dominio de API (`calificacionesService`, `analisisService`, `comunicacionesService`), no un cliente monolítico.**
Cada servicio expone funciones puras que llaman al Axios compartido y devuelven tipos derivados de los schemas del backend. Los hooks de TanStack Query (`useImportPreview`, `useAtrasados`, `useUmbral`, `useEnviarComunicacion`, etc.) envuelven esos servicios. Esto mantiene `<200 LOC` por archivo y permite mockear el servicio en tests sin tocar Axios. Alternativa descartada: llamar Axios desde los componentes → viola la regla de "todo fetch pasa por hooks de services".

**3. Importación multipart con preview en dos pasos.**
El `POST /import` del backend espera multipart con el archivo y un form field `request` JSON-encoded. El servicio construye el `FormData` (archivo + `request` serializado). El flujo de UI es: (a) subir archivo → `useImportPreview` (`POST /preview`) → mostrar actividades detectadas; (b) el usuario selecciona actividades vía RHF; (c) confirmar → `useConfirmImport` (`POST /import`) con las actividades seleccionadas. El preview no persiste nada (RN-01/RN-02). Estado informativo (`EmptyState`) cuando no hay datos ni actividades seleccionadas.

**4. Tracking de estados por polling con `refetchInterval` de TanStack Query.**
Tras encolar un lote (`POST /` devuelve `lote_id`), `useColaComunicaciones(lote_id)` hace `GET /` con `refetchInterval` activo mientras existan mensajes en estados no terminales (Pendiente/Enviando) y se detiene cuando todos llegan a estado terminal (OK/Fallido/Cancelado). Intervalo configurable (default ~3 s). Alternativa descartada: WebSocket/SSE → no hay contrato en el backend y agrega complejidad innecesaria para el volumen esperado.

**5. Export de entregas sin corregir generado en el cliente (CSV), no por endpoint.**
El backend devuelve la tabla de finalización vía `POST /finalizacion-preview`; no existe un endpoint de export dedicado. La UI genera el archivo CSV descargable en el cliente a partir de los datos ya recibidos (Blob + anchor download). Alternativa descartada: pedir un endpoint de export al backend → fuera de scope y el dato ya está disponible en el cliente.

**6. Selección de comisión (`asignacion_id`) como contexto compartido de la feature.**
Un selector de asignación (materia × cohorte de las que el docente está a cargo) fija el `asignacion_id` que alimenta todas las sub-vistas. Se mantiene en estado local de la página de gestión (o un context ligero de la feature), no en estado global de la app. El `asignacion_id` es dato de negocio; la autorización efectiva la resuelve el backend (`scope="propio"` → 403 si no corresponde).

**7. Validación de formularios con Zod, derivando tipos de los schemas del backend.**
Los formularios (selección de actividades, umbral, redacción/preview de comunicación) usan React Hook Form + `zodResolver`. Los tipos de request/response se definen en `types/` espejando los schemas Pydantic del backend, sin `any`.

## Risks / Trade-offs

- **[Polling puede generar carga si hay muchos lotes abiertos]** → `refetchInterval` solo activo mientras haya mensajes no terminales; se desactiva al alcanzar estado terminal. Intervalo configurable y razonable (no sub-segundo).
- **[El montaje/prefijo del router de comunicaciones no está confirmado en `main.py`]** → durante la implementación se verifica la URL real; el servicio centraliza la base path para ajustarla en un solo lugar. El contrato funcional (preview/encolar/cola) es estable según la spec `comunicaciones`.
- **[El contrato multipart de `POST /import` (form field `request` JSON-encoded) es poco habitual]** → se encapsula la construcción del `FormData` en el servicio con un test de integración que verifica el shape enviado; los componentes no conocen ese detalle.
- **[Divergencia de tipos frontend ↔ schemas Pydantic]** → los tipos en `types/` se derivan manualmente de los schemas existentes; se cubren con tests de integración que mockean respuestas con el shape real para detectar drift temprano.
- **[Reglas de negocio (umbral 60 %, definición de atrasado, valores aprobatorios) viven en el backend]** → el frontend no replica lógica de negocio; solo presenta y selecciona. Evita duplicar RN-03/RN-06/RN-09 en el cliente.

## Open Questions

- ¿El selector de asignación necesita un endpoint propio para listar las asignaciones del docente, o reutiliza datos ya disponibles desde `equipos`/`asignaciones` (C-07/C-08)? Se asume que sí existe y se confirma en implementación; si no, queda como dependencia a surfacear.
- Intervalo exacto de polling y tope de reintentos del tracking — se decide en implementación con un default conservador (~3 s) configurable.
