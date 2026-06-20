/**
 * FiltrosPeriodoForm.tsx — Filter form for selecting cohorte + mes/anio for liquidaciones.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { LiquidacionFiltrosSchema, type LiquidacionFiltrosData } from '../types/schemas'
import { useCohortes } from '@/features/admin/estructura/hooks/useEstructura'

const MESES = [
  { value: 1, label: 'Enero' },
  { value: 2, label: 'Febrero' },
  { value: 3, label: 'Marzo' },
  { value: 4, label: 'Abril' },
  { value: 5, label: 'Mayo' },
  { value: 6, label: 'Junio' },
  { value: 7, label: 'Julio' },
  { value: 8, label: 'Agosto' },
  { value: 9, label: 'Septiembre' },
  { value: 10, label: 'Octubre' },
  { value: 11, label: 'Noviembre' },
  { value: 12, label: 'Diciembre' },
]

interface FiltrosPeriodoFormProps {
  onFilter: (data: LiquidacionFiltrosData) => void
}

export function FiltrosPeriodoForm({ onFilter }: FiltrosPeriodoFormProps) {
  const { data: cohortes, isLoading: loadingCohortes } = useCohortes()
  const currentYear = new Date().getFullYear()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LiquidacionFiltrosData>({
    resolver: zodResolver(LiquidacionFiltrosSchema),
    defaultValues: {
      cohorte_id: '',
      mes: new Date().getMonth() + 1,
      anio: currentYear,
    },
  })

  return (
    <form
      onSubmit={handleSubmit(onFilter)}
      className="flex flex-wrap gap-4 items-end bg-gray-50 p-4 rounded-lg border border-gray-200"
    >
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">Cohorte</label>
        <select
          {...register('cohorte_id')}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[200px]"
          disabled={loadingCohortes}
        >
          <option value="">Seleccionar cohorte...</option>
          {cohortes?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nombre} ({c.anio})
            </option>
          ))}
        </select>
        {errors.cohorte_id && (
          <p className="text-xs text-red-600">{errors.cohorte_id.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">Mes</label>
        <select
          {...register('mes', { valueAsNumber: true })}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {MESES.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">Año</label>
        <input
          type="number"
          {...register('anio', { valueAsNumber: true })}
          min={2000}
          max={currentYear + 1}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-24"
        />
      </div>

      <button
        type="submit"
        className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        Consultar
      </button>
    </form>
  )
}
