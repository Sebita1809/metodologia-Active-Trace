/**
 * schemas.ts — Zod validation schemas for coordinacion module forms.
 *
 * Covers: AsignacionForm, AsignacionMasivaForm, ClonarEquipoForm,
 *         AvisoForm, TareaForm, GuardiaForm, ConvocatoriaForm
 * No `any` allowed.
 */

import { z } from 'zod'

// ---------------------------------------------------------------------------
// 1. Asignacion individual form
// ---------------------------------------------------------------------------

export const asignacionFormSchema = z
  .object({
    usuario_id: z.string().uuid('Seleccioná un docente válido'),
    rol: z.string().min(1, 'El rol es obligatorio'),
    materia_id: z.string().uuid('Seleccioná una materia').optional().nullable(),
    carrera_id: z.string().uuid('Seleccioná una carrera').optional().nullable(),
    cohorte_id: z.string().uuid('Seleccioná un cohorte').optional().nullable(),
    responsable_id: z.string().uuid().optional().nullable(),
    desde: z.string().min(1, 'La fecha de inicio es obligatoria'),
    hasta: z.string().optional().nullable(),
  })
  .refine(
    (data) => {
      if (!data.hasta) return true
      return data.hasta > data.desde
    },
    {
      message: 'La fecha de fin debe ser posterior a la fecha de inicio',
      path: ['hasta'],
    },
  )

export type AsignacionFormValues = z.infer<typeof asignacionFormSchema>

// ---------------------------------------------------------------------------
// 2. Asignacion masiva form
// ---------------------------------------------------------------------------

export const asignacionMasivaFormSchema = z
  .object({
    usuario_ids: z
      .array(z.string().uuid())
      .min(1, 'Seleccioná al menos un docente'),
    rol: z.string().min(1, 'El rol es obligatorio'),
    materia_id: z.string().uuid().optional().nullable(),
    carrera_id: z.string().uuid().optional().nullable(),
    cohorte_id: z.string().uuid().optional().nullable(),
    desde: z.string().min(1, 'La fecha de inicio es obligatoria'),
    hasta: z.string().optional().nullable(),
  })
  .refine(
    (data) => {
      if (!data.hasta) return true
      return data.hasta > data.desde
    },
    {
      message: 'La fecha de fin debe ser posterior a la fecha de inicio',
      path: ['hasta'],
    },
  )

export type AsignacionMasivaFormValues = z.infer<typeof asignacionMasivaFormSchema>

// ---------------------------------------------------------------------------
// 3. Clonar equipo form
// ---------------------------------------------------------------------------

export const clonarEquipoFormSchema = z
  .object({
    origen_materia_id: z.string().uuid('Seleccioná la materia de origen'),
    origen_carrera_id: z.string().uuid('Seleccioná la carrera de origen'),
    origen_cohorte_id: z.string().uuid('Seleccioná el cohorte de origen'),
    destino_materia_id: z.string().uuid('Seleccioná la materia de destino'),
    destino_carrera_id: z.string().uuid('Seleccioná la carrera de destino'),
    destino_cohorte_id: z.string().uuid('Seleccioná el cohorte de destino'),
    desde: z.string().optional().nullable(),
    hasta: z.string().optional().nullable(),
  })
  .refine(
    (data) => {
      if (!data.hasta || !data.desde) return true
      return data.hasta > data.desde
    },
    {
      message: 'La fecha de fin debe ser posterior a la fecha de inicio',
      path: ['hasta'],
    },
  )

export type ClonarEquipoFormValues = z.infer<typeof clonarEquipoFormSchema>

// ---------------------------------------------------------------------------
// 4. Aviso form
// ---------------------------------------------------------------------------

export const avisoFormSchema = z
  .object({
    titulo: z.string().min(1, 'El título es obligatorio').max(200),
    cuerpo: z.string().min(1, 'El cuerpo es obligatorio'),
    alcance: z.enum(['global', 'materia', 'cohorte']),
    materia_id: z.string().uuid().optional().nullable(),
    cohorte_id: z.string().uuid().optional().nullable(),
    roles_destinatarios: z
      .array(z.string())
      .min(1, 'Seleccioná al menos un rol destinatario'),
    severidad: z.enum(['info', 'advertencia', 'critica']),
    fecha_inicio: z.string().min(1, 'La fecha de inicio es obligatoria'),
    fecha_fin: z.string().optional().nullable(),
    orden: z.number().int().min(0).optional(),
    activo: z.boolean().optional(),
    require_ack: z.boolean().optional(),
  })
  .refine(
    (data) => {
      if (!data.fecha_fin) return true
      return data.fecha_fin > data.fecha_inicio
    },
    {
      message: 'La fecha de fin debe ser posterior a la fecha de inicio',
      path: ['fecha_fin'],
    },
  )
  .refine(
    (data) => {
      if (data.alcance === 'materia') return !!data.materia_id
      return true
    },
    {
      message: 'La materia es obligatoria cuando el alcance es "materia"',
      path: ['materia_id'],
    },
  )
  .refine(
    (data) => {
      if (data.alcance === 'cohorte') return !!data.cohorte_id
      return true
    },
    {
      message: 'El cohorte es obligatorio cuando el alcance es "cohorte"',
      path: ['cohorte_id'],
    },
  )

export type AvisoFormValues = z.infer<typeof avisoFormSchema>

// ---------------------------------------------------------------------------
// 5. Tarea form
// ---------------------------------------------------------------------------

export const tareaFormSchema = z.object({
  titulo: z.string().min(1, 'El título es obligatorio').max(200),
  descripcion: z.string().min(1, 'La descripción es obligatoria'),
  criterio_cierre: z.string().optional().nullable(),
  materia_id: z.string().uuid().optional().nullable(),
  asignada_a: z.string().uuid('Seleccioná un docente'),
})

export type TareaFormValues = z.infer<typeof tareaFormSchema>

// ---------------------------------------------------------------------------
// 6. Guardia form
// ---------------------------------------------------------------------------

export const guardiaFormSchema = z.object({
  asignacion_id: z.string().uuid('Seleccioná la asignación'),
  cubierto_por: z.string().uuid('Seleccioná quién cubrió la guardia'),
  materia_id: z.string().uuid().optional().nullable(),
  carrera_id: z.string().uuid().optional().nullable(),
  cohorte_id: z.string().uuid().optional().nullable(),
  dia: z.string().min(1, 'El día es obligatorio'),
  horario: z.string().min(1, 'El horario es obligatorio'),
  estado: z.enum(['Registrada', 'Auditada', 'Rechazada']).optional(),
  comentarios: z.string().optional().nullable(),
})

export type GuardiaFormValues = z.infer<typeof guardiaFormSchema>

// ---------------------------------------------------------------------------
// 7. Convocatoria (evaluacion) form
// ---------------------------------------------------------------------------

const diaDisponibleSchema = z.object({
  fecha: z.string().min(1, 'La fecha es obligatoria'),
  cupos: z
    .number({ invalid_type_error: 'Ingresá un número' })
    .int()
    .min(1, 'Los cupos deben ser mayores a 0'),
})

export const convocatoriaFormSchema = z.object({
  materia_id: z.string().uuid('Seleccioná una materia'),
  instancia: z
    .number({ invalid_type_error: 'Ingresá un número de instancia' })
    .int()
    .min(1, 'La instancia debe ser al menos 1'),
  dias_disponibles: z
    .array(diaDisponibleSchema)
    .min(1, 'Agregá al menos un día disponible'),
})

export type ConvocatoriaFormValues = z.infer<typeof convocatoriaFormSchema>
