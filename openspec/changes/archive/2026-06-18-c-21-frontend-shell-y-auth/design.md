## Context

El backend de autenticación (C-03) y RBAC (C-04) está implementado y expone los endpoints `POST /api/auth/{login, 2fa/login-verify, refresh, logout, forgot, reset}` y `GET /api/perfil`. No existe ningún frontend en el repo (`frontend/` no existe). C-21 crea el proyecto SPA desde cero y el flujo de autenticación completo, sirviendo de cimiento para C-22/C-23/C-24.

Restricciones del producto (de `CLAUDE.md` y `docs/ARQUITECTURA.md`):
- Stack obligatorio: React 18 + TypeScript (sin `any`, sin class components), Vite, Tailwind CSS, TanStack Query, React Hook Form + Zod, Axios.
- Estructura feature-based `features/{name}/{components,hooks,services,types,pages}` + `shared/`.
- Cliente Axios centralizado en `shared/services/api.ts` con interceptor JWT/refresh.
- Componentes <200 LOC; PascalCase para componentes y archivos.
- **Regla de oro**: identidad, roles y tenant salen EXCLUSIVAMENTE del JWT verificado por el backend. El frontend nunca confía en datos de la petición para identidad.
- Tests sin mocks de DB (no aplica aquí — frontend); se mockea la capa HTTP/backend.

Contrato relevante del JWT (de `auth-session`): el access token lleva `sub`, `tenant_id`, `roles`, `exp`. **Los permisos NO viajan en el token**: se resuelven server-side por request. No existe hoy un endpoint de "permisos efectivos".

Governance: **BAJO** — autonomía total si pasan los tests.

## Goals / Non-Goals

**Goals:**
- Scaffolding completo y reproducible del proyecto `frontend/` con el stack del producto.
- Cliente HTTP centralizado con refresh transparente, colado de peticiones concurrentes y manejo diferenciado de 401/403.
- Flujo de autenticación end-to-end: login, gate 2FA, recuperación y reset de contraseña, logout.
- Gestión de sesión client-side derivada del JWT, con persistencia ante recarga.
- Guards de ruta por sesión y por rol, fail-closed, con el backend como autoridad final.
- Layout/menú adaptados a la sesión.
- Suite de tests: render de login, flujo de auth mockeado, guard redirige sin sesión, refresh transparente.

**Non-Goals:**
- Features de dominio (importación, atrasados, comunicaciones, equipos, liquidaciones): son C-22/C-23/C-24.
- Enrolamiento de 2FA desde el frontend (`/api/auth/2fa/enroll`): C-21 cubre el gate de login, no el alta de 2FA (queda para una feature de perfil).
- Dockerización/Easypanel del frontend más allá del entorno de desarrollo mínimo.
- Sistema de diseño completo / librería de componentes exhaustiva: solo lo mínimo para auth + shell.
- Internacionalización.

## Decisions

### D1 — Gestión de estado de sesión: Context + reducer, no librería externa
Se usa un `AuthContext` (React Context + `useReducer`) en `features/auth/` para el estado de sesión global, complementado con TanStack Query para las llamadas. **Alternativas**: Redux/Zustand (overkill para una sola pieza de estado global), o solo TanStack Query (no encaja para estado de sesión sincrónico leído por guards en render). Context mantiene cero dependencias extra y es suficiente.

### D2 — Persistencia de tokens: `localStorage` con módulo de almacenamiento aislado
El access y refresh token se guardan vía un módulo `tokenStorage` (única superficie que toca `localStorage`), permitiendo sobrevivir recargas. **Trade-off**: `localStorage` es vulnerable a XSS frente a una cookie `HttpOnly`. Dado que el backend emite tokens en el body (no setea cookies) y el access token es de vida corta (15 min) con refresh rotado, se acepta para C-21 y se aísla el acceso en un solo módulo para poder migrar a cookies/`memory + httpOnly` sin tocar el resto. Se registra como riesgo R1.

### D3 — Refresh transparente con interceptor de respuesta + cola de espera
El interceptor de respuesta de Axios detecta `401`, y mediante un flag `isRefreshing` + una cola de promesas (`pendingRequests`) garantiza un único `POST /api/auth/refresh` para N peticiones concurrentes; al resolver, reintenta todas con el nuevo access token. La petición a `/api/auth/refresh` se excluye del reintento para evitar bucles. **Alternativa**: refresh proactivo por timer según `exp` — más complejo y propenso a desincronización de reloj; el reactivo sobre 401 es robusto y más simple.

### D4 — Guards por **rol**, no por permiso fino
Como el JWT solo trae `roles` y no hay endpoint de permisos efectivos, el guard de ruta filtra por rol (`ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS`). El control de permiso fino `modulo:accion` queda donde es autoridad: el backend (403). El frontend trata el guard como UX y respeta el 403. **Alternativa**: pedir permisos efectivos al backend tras login — requeriría un endpoint que hoy no existe; se deja como Open Question Q1 para evaluarlo cuando lleguen C-22+.

### D5 — Routing con React Router
Se usa React Router para rutas públicas (auth) y privadas (shell). Los guards se implementan como componentes wrapper (`<RequireAuth>`, `<RequireRole roles={...}>`). **Alternativa**: TanStack Router (más tipado) — se descarta para no introducir una dependencia menos estándar en el equipo; React Router es el de facto.

### D6 — Testing con Vitest + React Testing Library; backend mockeado con MSW
Vitest (nativo de Vite) + RTL para render y interacción; **MSW (Mock Service Worker)** para interceptar las llamadas HTTP y simular login, 2FA, refresh (401 → refresh → 200) sin tocar un backend real. **Alternativa**: mockear Axios directamente — más frágil; MSW prueba el cliente real incluyendo el interceptor de refresh, que es justamente lo que hay que verificar.

### D7 — Validación de formularios con Zod schemas colocados en `features/auth/types`
Cada formulario (login, forgot, reset, 2fa) tiene su schema Zod y tipo inferido, integrado con React Hook Form vía resolver. Centraliza las reglas de validación y el tipado del request.

### D8 — Decodificación del JWT solo para UI
Se decodifica el payload del access token (sin verificar firma — el backend ya la verificó) únicamente para leer `roles`/`tenant_id`/`exp` y adaptar la UI. Nunca se usa para decisiones de seguridad reales.

## Risks / Trade-offs

- **R1 — Tokens en `localStorage` (XSS)** → Aislar todo acceso en `tokenStorage`; access token de vida corta; refresh rotado; CSP/escape estricto en la app. Migrable a cookie `HttpOnly` sin refactor extendido.
- **R2 — Bucle de refresh / tormenta de 401** → Flag `isRefreshing` + cola única; exclusión de `/api/auth/refresh` del reintento; en fallo de refresh se limpia sesión y se corta.
- **R3 — Desfase entre guard por rol (UI) y permiso fino (backend)** → El backend es autoridad (403); la UI nunca asume permiso. Documentado en spec `route-guards`.
- **R4 — Stack no instalado aún (React Router, MSW, Vitest)** → Son dependencias estándar; se agregan en el scaffolding (governance BAJO permite instalarlas). No hay skill de React preinstalada (gap conocido), se siguen las convenciones de `docs/ARQUITECTURA.md`.
- **R5 — Contrato exacto de los endpoints 2FA/refresh** → Verificar nombres de campos (`partial_token`, `requires_2fa`, `access_token`, `refresh_token`) contra los schemas de C-03 al implementar; ajustar tipos si difieren.

## Migration Plan

No hay migración de datos ni código existente: es un proyecto nuevo (`frontend/`). Despliegue:
1. Crear `frontend/` con el scaffolding y dependencias.
2. Implementar capa `shared/` (cliente HTTP, tokenStorage, guards base, layout).
3. Implementar `features/auth/` (pantallas, hooks, schemas).
4. Conectar routing y guards; arrancar contra el backend de C-03 en dev.
Rollback: eliminar el directorio `frontend/`; no afecta al backend.

## Open Questions

- **Q1**: ¿Conviene exponer un endpoint backend de "permisos efectivos del usuario" para que el frontend afine guards/menú a nivel `modulo:accion` (no solo rol)? Decisión diferida a C-22 cuando las features lo necesiten. Por ahora, guard por rol + autoridad del 403.
- **Q2**: ¿`localStorage` o cookie `HttpOnly` a largo plazo? Aislado en `tokenStorage` para decidir sin costo de refactor. Revisar con el equipo de seguridad antes de producción.
- **Q3**: Confirmar el nombre exacto del endpoint de verificación 2FA en login (`/api/auth/2fa/login-verify` según specs) y sus campos al implementar.
