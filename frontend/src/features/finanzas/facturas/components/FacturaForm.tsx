/**
 * FacturaForm.tsx — RHF+Zod form for creating a factura.
 *
 * Fields: docente (usuario_id select), período, detalle, referencia_archivo, monto.
 * Note: Backend uses JSON body, not multipart — referencia_archivo is a string URL/path.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { FacturaSchema, type FacturaData } from '../types/schemas'
import { useUsuariosAdmin } from '@/features/admin/usuarios/hooks/useUsuariosAdmin'

const MESES = [
  { value: 1, label: 'Enero' }, { value: 2, label: 'Febrero' },
  { value: 3, label: 'Marzo' }, { value: 4, label: 'Abril' },
  { value: 5, label: 'Mayo' }, { value: 6, label: 'Junio' },
  { value: 7, label: 'Julio' }, { value: 8, label: 'Agosto' },
  { value: 9, label: 'Septiembre' }, { value: 10, label: 'Octubre' },
  { value: 11, label: 'Noviembre' }, { value: 12, label: 'Diciembre' },
]

const currentYear = new Date().getFullYear()

interface FacturaFormProps {
  onSubmit: (data: FacturaData) => void
  onCancel: () => void
  isPending: boolean
}

export function FacturaForm({ onSubmit, onCancel, isPending }: FacturaFormProps) {
  const { data: usuarios, isLoading: loadingUsuarios } = useUsuariosAdmin()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FacturaData>({
    resolver: zodResolver(FacturaSchema),
    defaultValues: {
      usuario_id: '',
      periodo_mes: new Date().getMonth() + 1,
      periodo_anio: currentYear,
      detalle: '',
      referencia_archivo: null,
      tamano_kb: null,
      monto: '',
    },
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">
          Docente <span className="text-red-500">*</span>
        </label>
        <select
          {...register('usuario_id')}
          disabled={loadingUsuarios}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Seleccionar docente...</option>
          {usuarios?.map((u) => (
            <option key={u.id} value={u.id}>
              {u.apellidos}, {u.nombre}
            </option>
          ))}
        </select>
        {errors.usuario_id && (
          <p className="text-xs text-red-600">{errors.usuario_id.message}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">
            Mes <span className="text-red-500">*</span>
          </label>
          <select
            {...register('periodo_mes', { valueAsNumber: true })}
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
          <label className="text-sm font-medium text-gray-700">
            Año <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            {...register('periodo_anio', { valueAsNumber: true })}
            min={2000}
            max={currentYear + 1}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">
          Detalle <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          {...register('detalle')}
          placeholder="Descripción del servicio..."
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {errors.detalle && (
          <p className="text-xs text-red-600">{errors.detalle.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">
          Referencia de archivo (opcional)
        </label>
        <input
          type="text"
          {...register('referencia_archivo')}
          placeholder="URL o ruta del comprobante..."
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">
          Monto <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          {...register('monto')}
          placeholder="ej: 75000.00"
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {errors.monto && (
          <p className="text-xs text-red-600">{errors.monto.message}</p>
        )}
      </div>

      <div className="flex gap-3 justify-end pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {isPending ? 'Guardando...' : 'Registrar factura'}
        </button>
      </div>
    </form>
  )
}
