/**
 * schemas.ts — Zod validation schemas for admin/programas-fechas feature.
 *
 * IMPORTANT: ProgramaCreate uses JSON body (not multipart).
 * referencia_archivo is a string URL/path reference.
 */

import { z } from 'zod'

export const ProgramaSchema = z.object({
  materia_id: z.string().uuid('Debe seleccionar una materia'),
  carrera_id: z.string().uuid('Debe seleccionar una carrera'),
  cohorte_id: z.string().uuid('Debe seleccionar una cohorte'),
  titulo: z.string().min(1, 'El título es requerido'),
  referencia_archivo: z.string().min(1, 'La referencia de archivo es requerida'),
})

export type ProgramaData = z.infer<typeof ProgramaSchema>

export const FechaAcademicaSchema = z.object({
  materia_id: z.string().uuid('Debe seleccionar una materia'),
  cohorte_id: z.string().uuid('Debe seleccionar una cohorte'),
  tipo: z.enum(['parcial', 'TP', 'coloquio'], {
    required_error: 'El tipo es requerido',
  }),
  numero: z.number().int().min(1, 'El número de instancia debe ser >= 1'),
  fecha: z.string().min(1, 'La fecha es requerida'),
  titulo: z.string().min(1, 'El título es requerido'),
  periodo: z.string().nullable().optional(),
})

export type FechaAcademicaData = z.infer<typeof FechaAcademicaSchema>
