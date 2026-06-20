/**
 * schemas.ts — Zod validation schemas for admin/usuarios feature.
 *
 * Security: CBU/alias validated here but ONLY sent in body JSON, never in URL params.
 */

import { z } from 'zod'

// CBU format: 22 digits
const cbuRegex = /^\d{22}$/

export const UsuarioAdminSchema = z.object({
  nombre: z.string().min(1, 'El nombre es requerido').max(200),
  apellidos: z.string().min(1, 'Los apellidos son requeridos').max(200),
  email: z.string().email('Email inválido'),
  dni: z.string().max(20).nullable().optional(),
  cuil: z.string().max(20).nullable().optional(),
  cbu: z
    .string()
    .regex(cbuRegex, 'CBU debe tener 22 dígitos')
    .nullable()
    .optional()
    .or(z.literal('')),
  alias_cbu: z.string().max(100).nullable().optional(),
  banco: z.string().max(100).nullable().optional(),
  regional: z.string().max(100).nullable().optional(),
  legajo: z.string().max(50).nullable().optional(),
  legajo_profesional: z.string().max(50).nullable().optional(),
  sexo: z.string().max(50).nullable().optional(),
  modalidad_cobro: z
    .enum(['Factura', 'Liquidacion'])
    .nullable()
    .optional()
    .or(z.literal('')),
  facturador: z.boolean(),
  estado: z.enum(['Activo', 'Inactivo']),
})

export type UsuarioAdminData = z.infer<typeof UsuarioAdminSchema>
