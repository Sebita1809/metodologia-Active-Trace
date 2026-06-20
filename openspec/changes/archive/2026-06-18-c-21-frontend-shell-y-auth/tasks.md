## 1. Scaffolding del proyecto frontend

- [x] 1.1 Inicializar proyecto Vite + React 18 + TypeScript en `frontend/` con `tsconfig` en modo estricto (sin `any`)
- [x] 1.2 Instalar y configurar Tailwind CSS (config + directivas en el CSS de entrada)
- [x] 1.3 Instalar dependencias del stack: `@tanstack/react-query`, `react-hook-form`, `zod`, `@hookform/resolvers`, `axios`, `react-router-dom`
- [x] 1.4 Instalar dependencias de testing: `vitest`, `@testing-library/react`, `@testing-library/user-event`, `jsdom`, `msw`
- [x] 1.5 Crear estructura de carpetas `src/features/`, `src/shared/{services,components,hooks}` y archivos base (`main.tsx`, `App.tsx`)
- [x] 1.6 Configurar el `QueryClientProvider` de TanStack Query en la raíz de la app
- [x] 1.7 Configurar alias de importación (`@/`) y verificar que `dev` (HMR) y `build` corren sin errores

## 2. Capa shared — sesión y almacenamiento de tokens

- [x] 2.1 Implementar módulo `tokenStorage` (única superficie sobre `localStorage`: get/set/clear de access y refresh token)
- [x] 2.2 Implementar util de decodificación de claims del JWT (`sub`, `tenant_id`, `roles`, `exp`) solo para UI, con tipos
- [x] 2.3 Implementar `AuthContext` (Context + useReducer): estado autenticado/no, claims, acciones `setSession`/`clearSession`
- [x] 2.4 Hidratar la sesión al arranque desde `tokenStorage` y detectar access token expirado sin refresh posible
- [x] 2.5 Tests: hidratación de sesión tras recarga, limpieza total al cerrar sesión, sesión expirada → no autenticada

## 3. Capa shared — cliente HTTP centralizado

- [x] 3.1 Crear la instancia Axios en `shared/services/api.ts` con base URL desde variable de entorno de Vite
- [x] 3.2 Interceptor de request: inyectar `Authorization: Bearer <access_token>` cuando hay sesión
- [x] 3.3 Interceptor de response: detectar `401`, ejecutar `POST /api/auth/refresh`, persistir nuevo par y reintentar la petición original una vez
- [x] 3.4 Implementar flag `isRefreshing` + cola de peticiones concurrentes (un único refresh para N `401`)
- [x] 3.5 Excluir `/api/auth/refresh` del reintento; en fallo de refresh limpiar sesión y redirigir a login (sin bucle)
- [x] 3.6 Manejo de `403` (no refrescar, propagar como acceso denegado) y errores `>=500`/red propagados tipados
- [x] 3.7 Tests (MSW): refresh transparente 401→refresh→200 con reintento; refresh fallido limpia sesión; 403 no dispara refresh

## 4. Feature auth — schemas y servicios

- [x] 4.1 Definir schemas Zod y tipos en `features/auth/types` (login, 2fa, forgot, reset) y tipos de respuesta del backend
- [x] 4.2 Implementar servicios/hooks de TanStack Query: `useLogin` (`POST /api/auth/login`), `useVerify2fa` (`POST /api/auth/2fa/login-verify`)
- [x] 4.3 Implementar hooks `useForgotPassword` (`POST /api/auth/forgot`), `useResetPassword` (`POST /api/auth/reset`), `useLogout` (`POST /api/auth/logout`)

## 5. Feature auth — pantallas

- [x] 5.1 `LoginPage`: formulario email+password (RHF+Zod); maneja par de tokens, `requires_2fa`, errores `401`/`429`
- [x] 5.2 `TwoFactorPage`: gate TOTP usando `partial_token`; éxito establece sesión completa; partial expirado → vuelve a login
- [x] 5.3 `ForgotPasswordPage`: solicita email y muestra mensaje genérico (sin revelar existencia de la cuenta)
- [x] 5.4 `ResetPasswordPage`: recibe token del enlace, valida nueva contraseña con Zod, maneja token inválido/usado
- [x] 5.5 Acción de logout (en el shell): revoca server-side, limpia sesión local aunque falle la red, redirige a login

## 6. Routing y guards

- [x] 6.1 Configurar React Router con rutas públicas (auth) y privadas (shell)
- [x] 6.2 Implementar `<RequireAuth>`: redirige a login sin sesión y preserva la ruta de destino para volver tras autenticar
- [x] 6.3 Implementar `<RequireRole roles={...}>`: fail-closed; rol insuficiente → estado de acceso denegado
- [x] 6.4 Tratar el `403` del backend como autoridad final en la UI (estado de acceso denegado, sin insistir)
- [x] 6.5 Tests: guard redirige a login sin sesión; permite con sesión; retorno a ruta original tras login; rol insuficiente denegado

## 7. Layout y navegación adaptados a la sesión

- [x] 7.1 Implementar el shell autenticado (menú + área de contenido + identidad del usuario + acción de logout)
- [x] 7.2 Construir el menú filtrando entradas por los roles de la sesión; recalcular al cambiar la sesión
- [x] 7.3 Definir la ruta de inicio por defecto tras login y la separación visual entre pantallas de auth (sin shell) y app autenticada
- [x] 7.4 Tests: render del shell autenticado; menú filtrado por rol; login no usa el shell

## 8. Cierre

- [x] 8.1 Verificar suite de tests completa (login, flujo de auth mockeado con 2FA, guard sin sesión, refresh transparente) en verde
- [x] 8.2 Verificar `build` de producción sin errores de TypeScript y linter limpio (sin `any`, sin class components)
- [x] 8.3 Documentar en el `README` del frontend el arranque en dev y la variable de entorno de la API
