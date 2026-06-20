/**
 * components/comunicacion/ComunicacionView.tsx — Full communication flow orchestrator.
 *
 * Steps:
 *   1. seleccion — select recipients from atrasados table
 *   2. draft    — write message (asunto + cuerpo) via DraftForm
 *   3. preview  — per-recipient preview via PreviewStep
 *   4. tracking — real-time state tracking via TrackingPanel
 *
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { TablaAtrasados } from '../analisis/TablaAtrasados'
import { TrackingPanel } from './TrackingPanel'
import { DraftForm } from './DraftForm'
import { PreviewStep } from './PreviewStep'
import { useUmbral } from '../../hooks/useCalificaciones'
import { usePreviewComunicacion, useEnviarComunicacion } from '../../hooks/useComunicaciones'
import type { AlumnoAtrasado } from '../../types/analisis'
import type { RenderResult } from '../../types/comunicaciones'
import type { ComunicacionDraftForm } from '../../types/schemas'

interface ComunicacionViewProps {
  asignacionId: string
}

type Step = 'seleccion' | 'draft' | 'preview' | 'tracking'

export function ComunicacionView({ asignacionId }: ComunicacionViewProps) {
  const [step, setStep] = useState<Step>('seleccion')
  const [selectedAlumnos, setSelectedAlumnos] = useState<Map<string, AlumnoAtrasado>>(new Map())
  const [previews, setPreviews] = useState<RenderResult[]>([])
  const [draftData, setDraftData] = useState<ComunicacionDraftForm | null>(null)
  const [loteId, setLoteId] = useState<string | null>(null)

  const umbralQuery = useUmbral(asignacionId)
  const materiaId = umbralQuery.data?.materia_id ?? ''

  const previewMutation = usePreviewComunicacion()
  const enviarMutation = useEnviarComunicacion()

  function handleToggle(alumno: AlumnoAtrasado) {
    setSelectedAlumnos((prev) => {
      const next = new Map(prev)
      if (next.has(alumno.alumno_id)) {
        next.delete(alumno.alumno_id)
      } else {
        next.set(alumno.alumno_id, alumno)
      }
      return next
    })
  }

  function buildDestinatarios(alumnos: AlumnoAtrasado[]) {
    return alumnos.map((a) => ({
      email: `${a.alumno_id}@placeholder.com`,
      variables: { nombre: a.nombre, apellidos: a.apellidos },
    }))
  }

  async function handlePreview(data: ComunicacionDraftForm) {
    setDraftData(data)
    const destinatarios = buildDestinatarios(Array.from(selectedAlumnos.values()))
    const result = await previewMutation.mutateAsync({
      materia_id: data.materia_id || materiaId,
      asunto: data.asunto,
      cuerpo: data.cuerpo,
      destinatarios,
    })
    setPreviews(result.resultados)
    setStep('preview')
  }

  async function handleEnviar() {
    if (!draftData) return
    const destinatarios = buildDestinatarios(Array.from(selectedAlumnos.values()))
    const result = await enviarMutation.mutateAsync({
      materia_id: draftData.materia_id || materiaId,
      asunto: draftData.asunto,
      cuerpo: draftData.cuerpo,
      destinatarios,
    })
    setLoteId(result.lote_id)
    setStep('tracking')
  }

  function resetFlow() {
    setStep('seleccion')
    setSelectedAlumnos(new Map())
    setPreviews([])
    setDraftData(null)
    setLoteId(null)
  }

  return (
    <div className="space-y-6">
      <h2 className="text-base font-semibold text-gray-900">
        Comunicación a atrasados
      </h2>

      {step === 'seleccion' && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Seleccioná los alumnos a los que querés comunicar:
          </p>
          <TablaAtrasados
            asignacionId={asignacionId}
            selectable
            selectedIds={new Set(selectedAlumnos.keys())}
            onToggle={handleToggle}
          />
          <button
            type="button"
            onClick={() => setStep('draft')}
            disabled={selectedAlumnos.size === 0}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Continuar ({selectedAlumnos.size} seleccionado
            {selectedAlumnos.size !== 1 ? 's' : ''})
          </button>
        </div>
      )}

      {step === 'draft' && (
        <DraftForm
          selectedCount={selectedAlumnos.size}
          materiaId={materiaId}
          isPending={previewMutation.isPending}
          onBack={() => setStep('seleccion')}
          onPreview={handlePreview}
        />
      )}

      {step === 'preview' && (
        <PreviewStep
          previews={previews}
          isPending={enviarMutation.isPending}
          isError={enviarMutation.isError}
          onBack={() => setStep('draft')}
          onConfirm={handleEnviar}
        />
      )}

      {step === 'tracking' && loteId && (
        <div className="space-y-4">
          <TrackingPanel loteId={loteId} />
          <button
            type="button"
            onClick={resetFlow}
            className="rounded border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            Nueva comunicación
          </button>
        </div>
      )}
    </div>
  )
}
