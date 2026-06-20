/**
 * components/comunicacion/PreviewStep.tsx — Preview step of the communication flow.
 *
 * Shows per-recipient previews and confirm/back buttons.
 * < 200 LOC, no `any`, no class components.
 */

import type { RenderResult } from '../../types/comunicaciones'

interface PreviewStepProps {
  previews: RenderResult[]
  isPending: boolean
  isError: boolean
  onBack: () => void
  onConfirm: () => Promise<void>
}

export function PreviewStep({
  previews,
  isPending,
  isError,
  onBack,
  onConfirm,
}: PreviewStepProps) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600 font-medium">
        Vista previa por destinatario:
      </p>

      {previews.map((p) => (
        <div
          key={p.email}
          className="border border-gray-200 rounded-lg p-4 space-y-2"
        >
          <p className="text-xs text-gray-500">{p.email}</p>
          <p className="text-sm font-medium text-gray-800">
            {p.asunto_renderizado}
          </p>
          <p className="text-sm text-gray-600 whitespace-pre-line">
            {p.cuerpo_renderizado}
          </p>
        </div>
      ))}

      {isError && (
        <div className="rounded-md bg-red-50 p-3">
          <p className="text-sm text-red-700">
            Error al enviar. Intentá de nuevo.
          </p>
        </div>
      )}

      <div className="flex gap-3">
        <button
          type="button"
          onClick={onBack}
          className="rounded border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          Volver
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={isPending}
          className="rounded bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
        >
          {isPending ? 'Enviando...' : 'Confirmar envío'}
        </button>
      </div>
    </div>
  )
}
