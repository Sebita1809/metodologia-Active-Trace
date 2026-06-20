/**
 * services/monitorGeneralService.ts — API functions for monitor general endpoint.
 * No `any` allowed.
 */

import { api } from '@/shared/services/api'
import type { MonitorGeneralFilters, MonitorGeneralResponse } from '../types'

const BASE = '/api/v1/analisis/monitor'

// ---------------------------------------------------------------------------
// GET /api/v1/calificaciones/monitor — global student activity monitor
// ---------------------------------------------------------------------------

export async function getMonitorGeneral(
  filters?: MonitorGeneralFilters,
): Promise<MonitorGeneralResponse> {
  const { data } = await api.get<MonitorGeneralResponse>(BASE, {
    params: filters,
  })
  return data
}

// ---------------------------------------------------------------------------
// GET /api/v1/analisis/monitor — CSV export as blob
// ---------------------------------------------------------------------------

export async function exportarMonitor(
  filters?: MonitorGeneralFilters,
): Promise<Blob> {
  const { data } = await api.get<Blob>(BASE, {
    params: { ...filters, format: 'csv' },
    responseType: 'blob',
  })
  return data
}
