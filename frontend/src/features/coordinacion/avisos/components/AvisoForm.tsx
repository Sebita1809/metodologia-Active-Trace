/**
 * AvisoForm.tsx — Create/edit aviso form (RHF + Zod).
 *
 * Fields: título, cuerpo, alcance, contexto condicional, roles, severidad,
 *         fechas, orden, activo, require_ack.
 * < 200 LOC, no `any`, no class components.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { avisoFormSchema, type AvisoFormValues } from '../../schemas'
import { useCreateAviso, useUpdateAviso } from '../hooks/useAvisos'
import type { Aviso } from '../types'

const ROLES = ['ALUMNO', 'TUTOR', 'PROFESOR', 'COORDINADOR', 'NEXO', 'ADMIN']

interface AvisoFormProps {
  aviso?: Aviso
  onSuccess?: () => void
  onCancel?: () => void
}

export function AvisoForm({ aviso, onSuccess, onCancel }: AvisoFormProps) {
  const createAviso = useCreateAviso()
  const updateAviso = useUpdateAviso()
  const isPending = createAviso.isPending || updateAviso.isPending

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<AvisoFormValues>({
    resolver: zodResolver(avisoFormSchema),
    defaultValues: aviso
      ? {
          titulo: aviso.titulo,
          cuerpo: aviso.cuerpo,
          alcance: aviso.alcance,
          materia_id: aviso.materia_id ?? undefined,
          cohorte_id: aviso.cohorte_id ?? undefined,
          roles_destinatarios: aviso.roles_destinatarios,
          severidad: aviso.severidad,
          fecha_inicio: aviso.fecha_inicio,
          fecha_fin: aviso.fecha_fin ?? undefined,
          activo: aviso.activo,
          require_ack: aviso.require_ack,
        }
      : { alcance: 'global', severidad: 'info', activo: true, require_ack: false },
  })

  const alcance = watch('alcance')

  function onSubmit(values: AvisoFormValues) {
    if (aviso) {
      updateAviso.mutate(
        { id: aviso.id, body: values },
        { onSuccess },
      )
    } else {
      createAviso.mutate(values, { onSuccess })
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 max-w-lg">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Título</label>
        <input
          {...register('titulo')}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
        {errors.titulo && <p className="text-red-600 text-xs mt-1">{errors.titulo.message}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Cuerpo</label>
        <textarea
          {...register('cuerpo')}
          rows={4}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
        {errors.cuerpo && <p className="text-red-600 text-xs mt-1">{errors.cuerpo.message}</p>}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Alcance</label>
          <select {...register('alcance')} className="w-full border border-gray-300 rounded px-3 py-2 text-sm">
            <option value="global">Global</option>
            <option value="materia">Materia</option>
            <option value="cohorte">Cohorte</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Severidad</label>
          <select {...register('severidad')} className="w-full border border-gray-300 rounded px-3 py-2 text-sm">
            <option value="info">Info</option>
            <option value="advertencia">Advertencia</option>
            <option value="critica">Crítica</option>
          </select>
        </div>
      </div>

      {alcance === 'materia' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Materia (UUID)</label>
          <input {...register('materia_id')} className="w-full border border-gray-300 rounded px-3 py-2 text-sm" placeholder="UUID" />
          {errors.materia_id && <p className="text-red-600 text-xs mt-1">{errors.materia_id.message}</p>}
        </div>
      )}

      {alcance === 'cohorte' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Cohorte (UUID)</label>
          <input {...register('cohorte_id')} className="w-full border border-gray-300 rounded px-3 py-2 text-sm" placeholder="UUID" />
          {errors.cohorte_id && <p className="text-red-600 text-xs mt-1">{errors.cohorte_id.message}</p>}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Roles destinatarios</label>
        <div className="flex flex-wrap gap-2">
          {ROLES.map((rol) => (
            <label key={rol} className="flex items-center gap-1 text-sm">
              <input type="checkbox" value={rol} {...register('roles_destinatarios')} />
              {rol}
            </label>
          ))}
        </div>
        {errors.roles_destinatarios && (
          <p className="text-red-600 text-xs mt-1">{errors.roles_destinatarios.message}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Fecha inicio</label>
          <input {...register('fecha_inicio')} type="date" className="w-full border border-gray-300 rounded px-3 py-2 text-sm" />
          {errors.fecha_inicio && <p className="text-red-600 text-xs mt-1">{errors.fecha_inicio.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Fecha fin</label>
          <input {...register('fecha_fin')} type="date" className="w-full border border-gray-300 rounded px-3 py-2 text-sm" />
          {errors.fecha_fin && <p className="text-red-600 text-xs mt-1">{errors.fecha_fin.message}</p>}
        </div>
      </div>

      <div className="flex gap-6">
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input {...register('activo')} type="checkbox" />
          Activo
        </label>
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input {...register('require_ack')} type="checkbox" />
          Requiere confirmación de lectura
        </label>
      </div>

      <div className="flex gap-2 pt-2">
        <button type="submit" disabled={isPending} className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
          {isPending ? 'Guardando...' : aviso ? 'Actualizar aviso' : 'Crear aviso'}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} className="bg-gray-100 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-200">
            Cancelar
          </button>
        )}
      </div>
    </form>
  )
}
