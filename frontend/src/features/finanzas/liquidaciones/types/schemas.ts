/**
 * schemas.ts — Zod validation schemas for liquidaciones feature.
 */

import { z } from 'zod'

export const LiquidacionFiltrosSchema = z.object({
  cohorte_id: z.string().uuid('Debe seleccionar una cohorte'),
  mes: z.number().int().min(1).max(12),
  anio: z.number().int().min(2000),
})

export type LiquidacionFiltrosData = z.infer<typeof LiquidacionFiltrosSchema>

export const CalcularLiquidacionSchema = z.object({
  cohorte_id: z.string().uuid(),
  mes: z.number().int().min(1).max(12),
  anio: z.number().int().min(2000),
})

export const CerrarLiquidacionSchema = z.object({
  cohorte_id: z.string().uuid(),
  mes: z.number().int().min(1).max(12),
  anio: z.number().int().min(2000),
})
