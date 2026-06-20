/**
 * schemas.ts — Zod validation schemas for facturas feature.
 */

import { z } from 'zod'

export const FacturaSchema = z.object({
  usuario_id: z.string().uuid('Debe seleccionar un docente'),
  periodo_mes: z.number().int().min(1).max(12),
  periodo_anio: z.number().int().min(2000),
  detalle: z.string().min(1, 'El detalle es requerido'),
  referencia_archivo: z.string().nullable().optional(),
  tamano_kb: z.string().nullable().optional(),
  monto: z.string().min(1, 'El monto es requerido'),
})

export type FacturaData = z.infer<typeof FacturaSchema>

export const CambiarEstadoSchema = z.object({
  nuevo_estado: z.enum(['Pendiente', 'Abonada']),
})

export type CambiarEstadoData = z.infer<typeof CambiarEstadoSchema>
