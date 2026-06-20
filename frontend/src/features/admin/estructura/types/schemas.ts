/**
 * schemas.ts — Zod validation schemas for admin/estructura feature.
 */

import { z } from 'zod'

export const CarreraSchema = z.object({
  codigo: z.string().min(1, 'El código es requerido'),
  nombre: z.string().min(1, 'El nombre es requerido'),
  estado: z.enum(['Activa', 'Inactiva']),
})

export type CarreraData = z.infer<typeof CarreraSchema>

export const CohorteSchema = z
  .object({
    carrera_id: z.string().uuid('Debe seleccionar una carrera'),
    nombre: z.string().min(1, 'El nombre es requerido'),
    anio: z.number().int().min(2000, 'Año inválido'),
    vig_desde: z.string().min(1, 'La vigencia desde es requerida'),
    vig_hasta: z.string().nullable().optional(),
    estado: z.enum(['Activa', 'Inactiva']),
  })
  .refine(
    (data) => {
      if (data.vig_hasta && data.vig_desde) {
        return new Date(data.vig_hasta) > new Date(data.vig_desde)
      }
      return true
    },
    {
      message: 'vig_hasta debe ser posterior a vig_desde',
      path: ['vig_hasta'],
    },
  )

export type CohorteData = z.infer<typeof CohorteSchema>

export const MateriaSchema = z.object({
  nombre: z.string().min(1, 'El nombre es requerido'),
  codigo: z.string().nullable().optional(),
  estado: z.enum(['Activa', 'Inactiva']),
})

export type MateriaData = z.infer<typeof MateriaSchema>
