# active-trace — Frontend

React 18 + TypeScript SPA for the active-trace academic management platform.

## Stack

- **React 18** + **TypeScript** (strict mode, no `any`)
- **Vite** — bundler + dev server with HMR
- **Tailwind CSS** — utility-first styling (no CSS modules, no inline styles)
- **TanStack Query** — server state management
- **React Hook Form + Zod** — typed form validation
- **Axios** — HTTP client with JWT refresh interceptor
- **React Router DOM** — client-side routing

## Development startup

1. Copy the environment file and set your API URL:

   ```bash
   cp .env.example .env
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. Start the dev server:

   ```bash
   npm run dev
   ```

   The app will be available at `http://localhost:5173`.

## Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Base URL for the backend API | `http://localhost:8000` |

All Vite env vars must be prefixed with `VITE_` to be exposed to the browser.

## Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start dev server with HMR |
| `npm run build` | Type-check + production build |
| `npm run test` | Run tests in watch mode |
| `npm run test:run` | Run tests once (CI) |
| `npm run coverage` | Run tests with coverage report |
| `npm run preview` | Preview the production build |

## Project structure

```
src/
  features/          # Feature modules (auth, dashboard, ...)
    auth/
      context/       # AuthContext + useReducer
      hooks/         # TanStack Query mutations
      pages/         # LoginPage, TwoFactorPage, ForgotPasswordPage, ResetPasswordPage
      types/         # Zod schemas + inferred types
      __tests__/     # Feature tests
  shared/
    components/      # AppShell, NavMenu, RequireAuth, RequireRole, ...
    services/        # api.ts (Axios), tokenStorage.ts, jwtDecode.ts
    hooks/           # Shared hooks
  router/            # React Router configuration
  test/              # Test utilities (MSW server, fixtures, renderWithProviders)
```

## Auth flow

1. `LoginPage` calls `POST /api/auth/login`
   - On success → `setSession(access_token, refresh_token)` → navigate `/dashboard`
   - If `requires_2fa: true` → navigate `/login/2fa` with `partial_token` in location state
2. `TwoFactorPage` calls `POST /api/auth/2fa/login-verify` with the `partial_token` + TOTP code
3. On any authenticated request, the Axios interceptor attaches `Authorization: Bearer <access_token>`
4. On `401`, the interceptor refreshes via `POST /api/auth/refresh` and retries once
5. On refresh failure, `clearSession()` is called and the user is redirected to login

## Route guards

- `<RequireAuth>` — redirects unauthenticated users to `/login`; preserves the original URL in `location.state.from`
- `<RequireRole roles={[...]}>` — fail-closed; shows an "Access denied" message if the user's roles do not match

The backend `403` is the final authorization authority — the UI does not retry or escalate.
