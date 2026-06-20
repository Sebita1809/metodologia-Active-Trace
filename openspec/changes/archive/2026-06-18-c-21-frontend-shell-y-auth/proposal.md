## Why

El backend de autenticación (C-03) y RBAC (C-04) ya están listos, pero no existe ninguna interfaz que los consuma: hoy el sistema no tiene frontend. Sin un shell SPA y un flujo de login funcional, ninguna de las features de presentación (C-22/C-23/C-24) puede construirse ni probarse. C-21 establece los cimientos del frontend —scaffolding, cliente HTTP con refresh transparente, autenticación completa y navegación adaptada a la sesión— sobre los que se montará toda la capa de presentación.

## What Changes

- **Scaffolding del proyecto frontend**: nuevo directorio `frontend/` con React 18 + TypeScript + Vite, Tailwind CSS, TanStack Query, React Hook Form + Zod y Axios. Estructura feature-based (`features/{name}/{components,hooks,services,types,pages}`) más `shared/`.
- **Cliente HTTP centralizado** (`shared/services/api.ts`): instancia Axios única con interceptor que inyecta el access token, detecta `401`, ejecuta **refresh transparente** del par de tokens (con rotación), reintenta la petición original y, si el refresh falla, cierra la sesión. Manejo diferenciado de `403` (sin permiso, no reintenta).
- **Feature `auth`**: pantallas de login (email + password), gate 2FA TOTP, solicitud de recuperación de contraseña y reset con token. Consumen los endpoints de C-03 (`/api/auth/login`, `/api/auth/2fa/login-verify`, `/api/auth/refresh`, `/api/auth/logout`, `/api/auth/forgot`, `/api/auth/reset`).
- **Manejo de sesión client-side**: persistencia y limpieza de tokens, decodificación de claims mínimos del JWT (`sub`, `tenant_id`, `roles`, `exp`), estado de sesión global y logout que revoca tokens server-side.
- **Guard de rutas**: redirección a login si no hay sesión válida; guard por rol/permiso que oculta o bloquea rutas según la sesión, tratando el `403` del backend como autoridad final (fail-closed).
- **Layout y navegación adaptados a la sesión**: menú y shell que muestran únicamente las secciones permitidas según los roles de la sesión.
- **Tests**: render de login, flujo de auth mockeado (incluido gate 2FA), guard que redirige sin sesión, y refresh transparente sobre `401`.

## Capabilities

### New Capabilities
- `frontend-scaffold`: estructura base del proyecto SPA (React 18 + TS + Vite + Tailwind + TanStack Query + RHF/Zod + Axios), organización feature-based y convenciones de carpetas.
- `http-client`: cliente Axios centralizado con interceptor de autenticación, refresh transparente de tokens y manejo de errores 401/403.
- `frontend-auth`: pantallas y flujo de autenticación (login, gate 2FA TOTP, recuperación y reset de contraseña, logout) consumiendo el backend de C-03.
- `session-management`: gestión client-side de la sesión (tokens, claims, estado de sesión) derivada exclusivamente del JWT verificado por el backend.
- `route-guards`: protección de rutas por sesión y por rol/permiso, con redirección y fail-closed.
- `app-shell-navigation`: layout, shell de la aplicación y menú adaptados a los permisos de la sesión.

### Modified Capabilities
<!-- Ninguna: este change introduce capacidades nuevas de frontend; no modifica el comportamiento especificado de las capacidades de backend existentes. -->

## Impact

- **Nuevo código**: directorio `frontend/` completo (scaffolding, configuración de build, `features/auth/`, `shared/services/api.ts`, guards, layout, tests).
- **APIs consumidas** (sin cambios en el backend): `POST /api/auth/login`, `POST /api/auth/2fa/login-verify`, `POST /api/auth/refresh`, `POST /api/auth/logout`, `POST /api/auth/forgot`, `POST /api/auth/reset`, `GET /api/perfil`.
- **Dependencias**: depende de C-04 (RBAC) y C-03 (auth-jwt-2fa) ya implementados. Habilita C-22, C-23 y C-24.
- **Infraestructura**: agrega el servicio frontend al stack (build Vite, integración Docker/Easypanel queda fuera del alcance de este change salvo lo mínimo de dev).
- **Restricción de seguridad clave**: la identidad, roles y tenant se derivan EXCLUSIVAMENTE del JWT; el frontend nunca confía en datos de la petición para identidad. El guard de rutas es UX; el backend (403) es la autoridad de autorización.
