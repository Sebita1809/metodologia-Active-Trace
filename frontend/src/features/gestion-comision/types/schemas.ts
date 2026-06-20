/**
 * types/schemas.ts — Zod schemas for forms in gestion-comision feature.
 *
 * Covers: activity selection, umbral config, communication drafting, monitor filters.
 * No `any` allowed.
 */

import { z } from 'zod'

// ---------------------------------------------------------------------------
// 1. Activity selection form (import step 2)
// ---------------------------------------------------------------------------

export const actividadSeleccionSchema = z.object({
  actividades_seleccionadas: z
    .array(z.string())
    .min(1, 'Seleccioná al menos una actividad'),
})

export type ActividadSeleccionForm = z.infer<typeof actividadSeleccionSchema>

// ---------------------------------------------------------------------------
// 2. Umbral configuration form
// ---------------------------------------------------------------------------

export const umbralFormSchema = z.object({
  umbral_pct: z
    .number({ invalid_type_error: 'Ingresá un número' })
    .int('El umbral debe ser un entero')
    .min(0, 'El umbral mínimo es 0 %')
    .max(100, 'El umbral máximo es 100 %'),
  valores_aprobatorios: z
    .array(z.string().min(1))
    .min(1, 'Ingresá al menos un valor aprobatorio'),
})

export type UmbralForm = z.infer<typeof umbralFormSchema>

// ---------------------------------------------------------------------------
// 3. Communication draft form
// ---------------------------------------------------------------------------

export const comunicacionDraftSchema = z.object({
  materia_id: z.string().uuid('ID de materia inválido'),
  asunto: z.string().min(1, 'El asunto es obligatorio'),
  cuerpo: z.string().min(1, 'El cuerpo es obligatorio'),
})

export type ComunicacionDraftForm = z.infer<typeof comunicacionDraftSchema>

// ---------------------------------------------------------------------------
// 4. Monitor filters form
// ---------------------------------------------------------------------------

export const monitorFiltrosSchema = z.object({
  alumno: z.string().optional(),
  correo: z.string().optional(),
  actividad: z.string().optional(),
  min_cumplido: z
    .number()
    .min(0)
    .max(100)
    .optional(),
})

export type MonitorFiltrosForm = z.infer<typeof monitorFiltrosSchema>
