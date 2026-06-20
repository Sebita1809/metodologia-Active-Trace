/**
 * components/comunicacion/DraftForm.tsx — Message draft step of the communication flow.
 *
 * Collects asunto and cuerpo, triggers preview on submit.
 * < 200 LOC, no `any`, no class components.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { comunicacionDraftSchema, type ComunicacionDraftForm } from '../../types/schemas'

interface DraftFormProps {
  selectedCount: number
  materiaId: string
  isPending: boolean
  onBack: () => void
  onPreview: (data: ComunicacionDraftForm) => Promise<void>
}

export function DraftForm({
  selectedCount,
  materiaId,
  isPending,
  onBack,
  onPreview,
}: DraftFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ComunicacionDraftForm>({
    resolver: zodResolver(comunicacionDraftSchema),
    defaultValues: {
      materia_id: materiaId,
      asunto: '',
      cuerpo: '',
    },
  })

  return (
    <form onSubmit={handleSubmit(onPreview)} className="space-y-4 max-w-lg">
      <p className="text-sm text-gray-600">
        {selectedCount} destinatario{selectedCount !== 1 ? 's' : ''} seleccionado
        {selectedCount !== 1 ? 's' : ''}.
      </p>

      <input type="hidden" {...register('materia_id')} />

      <div>
        <label
          htmlFor="com-asunto"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          Asunto
        </label>
        <input
          id="com-asunto"
          type="text"
          {...register('asunto')}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
        {errors.asunto && (
          <p className="mt-1 text-xs text-red-600">{errors.asunto.message}</p>
        )}
      </div>

      <div>
        <label
          htmlFor="com-cuerpo"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          Cuerpo
        </label>
        <textarea
          id="com-cuerpo"
          rows={5}
          {...register('cuerpo')}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
        {errors.cuerpo && (
          <p className="mt-1 text-xs text-red-600">{errors.cuerpo.message}</p>
        )}
      </div>

      <div className="flex gap-3">
        <button
          type="button"
          onClick={onBack}
          className="rounded border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          Volver
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {isPending ? 'Previsualizar...' : 'Previsualizar'}
        </button>
      </div>
    </form>
  )
}
