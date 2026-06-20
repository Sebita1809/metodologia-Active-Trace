/**
 * ImportarAlumnosDialog.tsx — File upload dialog to import students into a convocatoria.
 *
 * Shows result (N imported / errors).
 * < 200 LOC, no `any`, no class components.
 */

import { useRef, useState } from 'react'
import { useImportarAlumnos } from '../hooks/useColoquios'
import type { ImportarPadronResponse } from '../types'

interface ImportarAlumnosDialogProps {
  evaluacionId: string
  onClose: () => void
}

export function ImportarAlumnosDialog({
  evaluacionId,
  onClose,
}: ImportarAlumnosDialogProps) {
  const importar = useImportarAlumnos()
  const fileRef = useRef<HTMLInputElement>(null)
  const [result, setResult] = useState<ImportarPadronResponse | null>(null)
  const [fileError, setFileError] = useState('')

  function handleConfirm() {
    const file = fileRef.current?.files?.[0]
    if (!file) {
      setFileError('Seleccioná un archivo para importar.')
      return
    }
    setFileError('')
    importar.mutate(
      { evaluacionId, file },
      {
        onSuccess: (data) => setResult(data),
      },
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full mx-4 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-gray-900">Importar padrón de alumnos</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>

        {!result ? (
          <>
            <p className="text-sm text-gray-500">
              Seleccioná el archivo de padrón (.csv o .xlsx) para esta convocatoria.
            </p>
            <div>
              <input
                ref={fileRef}
                type="file"
                accept=".csv,.xlsx,.xls"
                className="block w-full text-sm text-gray-700 border border-gray-300 rounded px-3 py-2"
              />
              {fileError && <p className="text-red-600 text-xs mt-1">{fileError}</p>}
            </div>
            {importar.isError && (
              <p className="text-red-600 text-sm">
                Error al importar. Verificá el formato del archivo.
              </p>
            )}
            <div className="flex gap-2">
              <button
                onClick={handleConfirm}
                disabled={importar.isPending}
                className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                {importar.isPending ? 'Importando...' : 'Importar'}
              </button>
              <button
                onClick={onClose}
                className="bg-gray-100 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-200"
              >
                Cancelar
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="bg-green-50 border border-green-200 rounded p-3 text-sm text-green-800">
              {result.importados} alumno(s) importado(s) correctamente.
            </div>
            {result.errores.length > 0 && (
              <div className="space-y-1">
                <p className="text-sm font-medium text-red-700">Errores:</p>
                <ul className="space-y-0.5">
                  {result.errores.map((err, i) => (
                    <li key={i} className="text-xs text-red-600">{err}</li>
                  ))}
                </ul>
              </div>
            )}
            <button
              onClick={onClose}
              className="bg-gray-100 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-200"
            >
              Cerrar
            </button>
          </>
        )}
      </div>
    </div>
  )
}
