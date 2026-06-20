/**
 * hooks/useFacturas.ts — TanStack Query hooks for facturas endpoints.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  cambiarEstadoFactura,
  createFactura,
  getFacturas,
  updateFactura,
} from '../services/facturasService'
import type { FacturaFilters, FacturaForm, CambiarEstadoForm } from '../types'

// Query key factories
export const facturasKeys = {
  all: ['facturas'] as const,
  list: (filters: FacturaFilters) => [...facturasKeys.all, 'list', filters] as const,
}

// ---------------------------------------------------------------------------
// useFacturas — query for GET /api/facturas
// ---------------------------------------------------------------------------

export function useFacturas(filters: FacturaFilters = {}) {
  return useQuery({
    queryKey: facturasKeys.list(filters),
    queryFn: () => getFacturas(filters),
  })
}

// ---------------------------------------------------------------------------
// useCreateFactura — mutation for POST /api/facturas
// ---------------------------------------------------------------------------

export function useCreateFactura() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: FacturaForm) => createFactura(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: facturasKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// useUpdateFactura — mutation for PATCH /api/facturas/{id}
// ---------------------------------------------------------------------------

export function useUpdateFactura() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<FacturaForm> }) =>
      updateFactura(id, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: facturasKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// useCambiarEstadoFactura — mutation for PATCH /api/facturas/{id}/estado
// ---------------------------------------------------------------------------

export function useCambiarEstadoFactura() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CambiarEstadoForm }) =>
      cambiarEstadoFactura(id, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: facturasKeys.all })
    },
  })
}
