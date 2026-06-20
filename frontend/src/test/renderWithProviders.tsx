import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, type MemoryRouterProps } from 'react-router-dom'
import { render, type RenderOptions } from '@testing-library/react'
import type { ReactNode } from 'react'
import { AuthProvider } from '@/features/auth/context/AuthContext'

interface WrapperOptions {
  routerProps?: MemoryRouterProps
}

function makeWrapper(options: WrapperOptions = {}) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter {...(options.routerProps ?? {})}>
          <AuthProvider>
            {children}
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }

  return Wrapper
}

export function renderWithProviders(
  ui: ReactNode,
  options: RenderOptions & WrapperOptions = {},
) {
  const { routerProps, ...renderOptions } = options
  return render(ui, {
    wrapper: makeWrapper({ routerProps }),
    ...renderOptions,
  })
}
