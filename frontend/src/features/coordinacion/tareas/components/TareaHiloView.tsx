/**
 * TareaHiloView.tsx — Thread panel for a tarea with comments + add comment form.
 *
 * Shows hilo of comentarios + form to add a new one.
 * Validates: comment must not be empty.
 * < 200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useAddComentario, useComentarios } from '../hooks/useTareas'
import type { Tarea } from '../types'

interface TareaHiloViewProps {
  tarea: Tarea
  onClose?: () => void
}

export function TareaHiloView({ tarea, onClose }: TareaHiloViewProps) {
  const { data: comentarios = [], isLoading } = useComentarios(tarea.id)
  const addComentario = useAddComentario()
  const [texto, setTexto] = useState('')
  const [error, setError] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!texto.trim()) {
      setError('El comentario no puede estar vacío.')
      return
    }
    setError('')
    addComentario.mutate(
      { id: tarea.id, texto: texto.trim() },
      { onSuccess: () => setTexto('') },
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-800">{tarea.titulo}</h3>
          <p className="text-xs text-gray-500 mt-0.5">{tarea.descripcion}</p>
        </div>
        {onClose && (
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        )}
      </div>

      <div className="space-y-2">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          Hilo de comentarios
        </h4>
        {isLoading ? (
          <p className="text-sm text-gray-500">Cargando comentarios...</p>
        ) : comentarios.length === 0 ? (
          <p className="text-sm text-gray-400">Sin comentarios aún.</p>
        ) : (
          <ul className="space-y-2">
            {comentarios.map((c) => (
              <li key={c.id} className="bg-gray-50 rounded p-3 text-sm">
                <p className="text-gray-800">{c.texto}</p>
                <p className="text-xs text-gray-400 mt-1">
                  {c.autor_id} · {new Date(c.created_at).toLocaleDateString('es-AR')}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-2">
        <textarea
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          rows={3}
          placeholder="Agregar comentario o evidencia..."
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {error && <p className="text-red-600 text-xs">{error}</p>}
        <button
          type="submit"
          disabled={addComentario.isPending}
          className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {addComentario.isPending ? 'Enviando...' : 'Agregar comentario'}
        </button>
      </form>
    </div>
  )
}
