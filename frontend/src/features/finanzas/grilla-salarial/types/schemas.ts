/**
 * schemas.ts — Zod validation schemas for grilla-salarial feature.
 */

import { z } from 'zod'

export const SalarioBaseSchema = z
  .object({
    rol: z.string().min(1, 'El rol es requerido'),
    monto: z.string().min(1, 'El monto es requerido'),
    desde: z.string().min(1, 'La vigencia desde es requerida'),
    hasta: z.string().nullable().optional(),
  })
  .refine(
    (data) => {
      if (data.hasta && data.desde) {
        return new Date(data.hasta) > new Date(data.desde)
      }
      return true
    },
    {
      message: 'vigencia_hasta debe ser posterior a vigencia_desde',
      path: ['hasta'],
    },
  )

export type SalarioBaseData = z.infer<typeof SalarioBaseSchema>

export const PlusSchema = z
  .object({
    clave: z.string().min(1, 'La clave es requerida'),
    rol: z.string().min(1, 'El rol es requerido'),
    descripcion: z.string().nullable().optional(),
    monto: z.string().min(1, 'El monto es requerido'),
    desde: z.string().min(1, 'La vigencia desde es requerida'),
    hasta: z.string().nullable().optional(),
  })
  .refine(
    (data) => {
      if (data.hasta && data.desde) {
        return new Date(data.hasta) > new Date(data.desde)
      }
      return true
    },
    {
      message: 'vigencia_hasta debe ser posterior a vigencia_desde',
      path: ['hasta'],
    },
  )

export type PlusData = z.infer<typeof PlusSchema>
