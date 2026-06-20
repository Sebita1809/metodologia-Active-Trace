/**
 * components/import/ImportacionView.tsx — Import flow sub-view.
 *
 * Steps:
 *   1. Upload file → POST /preview → show detected activities (no persist)
 *   2. Select activities via RHF → confirm → POST /import (multipart)
 *   3. Show success or error feedback
 *
 * < 200 LOC, no `any`, no class components.
 */

import { useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useConfirmImport, useImportPreview } from '../../hooks/useCalificaciones'
import type { ImportPreviewResponse } from '../../types/calificaciones'
import { actividadSeleccionSchema, type ActividadSeleccionForm } from '../../types/schemas'
import { EmptyState } from '../EmptyState'
import { FinalizacionView } from './FinalizacionView'

interface ImportacionViewProps {
  asignacionId: string
}

export function ImportacionView({ asignacionId }: ImportacionViewProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null)
  const [importSuccess, setImportSuccess] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)

  const previewMutation = useImportPreview()
  const importMutation = useConfirmImport(asignacionId)

  const allActivities = preview
    ? [...(preview.actividades_numericas ?? []), ...(preview.actividades_textuales ?? [])]
    : []

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ActividadSeleccionForm>({
    resolver: zodResolver(actividadSeleccionSchema),
    defaultValues: { actividades_seleccionadas: [] },
  })

  const selected = watch('actividades_seleccionadas') ?? []

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    setSelectedFile(file)
    setPreview(null)
    setPreviewError(null)
    setImportSuccess(false)

    try {
      const result = await previewMutation.mutateAsync({ file, asignacion_id: asignacionId })
      setPreview(result)
    } catch {
      setPreviewError('Error al previsualizar el archivo. Verificá el formato e intentá de nuevo.')
    }
  }

  async function onConfirm(data: ActividadSeleccionForm) {
    if (!selectedFile) return
    try {
      await importMutation.mutateAsync({
        file: selectedFile,
        actividades_seleccionadas: data.actividades_seleccionadas,
      })
      setImportSuccess(true)
      setPreview(null)
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch {
      // error handled by mutation state
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-base font-semibold text-gray-900">
        Importación de calificaciones
      </h2>

      {/* File upload */}
      <div>
        <label
          htmlFor="file-calificaciones"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          Archivo de calificaciones (LMS export)
        </label>
        <input
          id="file-calificaciones"
          type="file"
          accept=".csv,.xlsx,.xls"
          ref={fileInputRef}
          onChange={handleFileChange}
          className="block text-sm text-gray-700 file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
        />
      </div>

      {previewMutation.isPending && (
        <p className="text-sm text-gray-500">Analizando archivo...</p>
      )}

      {previewError && (
        <div className="rounded-md bg-red-50 p-3">
          <p className="text-sm text-red-700">Error: {previewError}</p>
        </div>
      )}

      {importSuccess && (
        <div className="rounded-md bg-green-50 p-3">
          <p className="text-sm text-green-700">
            Calificaciones importadas correctamente.
          </p>
        </div>
      )}

      {importMutation.isError && (
        <div className="rounded-md bg-red-50 p-3">
          <p className="text-sm text-red-700">
            Error al importar. Intentá de nuevo.
          </p>
        </div>
      )}

      {preview && (
        <form onSubmit={handleSubmit(onConfirm)} className="space-y-4">
          <div>
            <p className="text-sm text-gray-600 mb-3">
              Se detectaron{' '}
              <strong>{preview.alumnos_detectados}</strong> alumnos y{' '}
              <strong>{allActivities.length}</strong> actividades.
              Seleccioná las que querés incluir:
            </p>

            {allActivities.length === 0 && (
              <EmptyState
                title="Sin actividades detectadas"
                description="El archivo no contiene actividades reconocibles."
              />
            )}

            {allActivities.length > 0 && (
              <fieldset className="space-y-2">
                <legend className="sr-only">Actividades a importar</legend>
                {allActivities.map((act) => (
                  <label
                    key={act}
                    className="flex items-center gap-2 text-sm text-gray-700"
                  >
                    <input
                      type="checkbox"
                      value={act}
                      {...register('actividades_seleccionadas')}
                      className="rounded border-gray-300 text-blue-600"
                    />
                    {act}
                  </label>
                ))}
              </fieldset>
            )}

            {errors.actividades_seleccionadas && (
              <p className="mt-1 text-xs text-red-600">
                {errors.actividades_seleccionadas.message}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={selected.length === 0 || importMutation.isPending}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {importMutation.isPending ? 'Importando...' : 'Confirmar importación'}
          </button>
        </form>
      )}

      {/* Finalizacion preview section */}
      <hr className="border-gray-200" />
      <FinalizacionView asignacionId={asignacionId} />
    </div>
  )
}
