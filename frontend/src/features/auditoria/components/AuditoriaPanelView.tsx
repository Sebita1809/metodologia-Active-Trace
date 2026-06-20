/**
 * AuditoriaPanelView.tsx — Panel view for COORDINADOR and ADMIN.
 *
 * Four sub-sections:
 *   1. AccionesPorDia chart (filterable by date range)
 *   2. EstadoComunicaciones table per docente
 *   3. InteraccionesDocente table
 *   4. LogAcciones table (last N actions)
 */

import { useState } from 'react'
import {
  useAccionesPorDia,
  useComunicacionesPorDocente,
  useInteraccionesDocente,
  useUltimasAcciones,
} from '../hooks/useAuditoria'
import { AccionesPorDiaChart } from './AccionesPorDiaChart'
import { EstadoComunicacionesTable } from './EstadoComunicacionesTable'
import { InteraccionesDocente } from './InteraccionesDocente'
import { LogAccionesTable } from './LogAccionesTable'
import type { AccionesPorDiaFilters } from '../types'

function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10)
}

export function AuditoriaPanelView() {
  const today = new Date()
  const thirtyDaysAgo = new Date(today)
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

  const [rangoFechas, setRangoFechas] = useState<AccionesPorDiaFilters>({
    desde: toIsoDate(thirtyDaysAgo),
    hasta: toIsoDate(today),
  })

  const [desdeInput, setDesdeInput] = useState(rangoFechas.desde)
  const [hastaInput, setHastaInput] = useState(rangoFechas.hasta)

  const { data: accionesPorDia, isLoading: loadingAcciones } =
    useAccionesPorDia(rangoFechas)
  const { data: comunicaciones, isLoading: loadingCom } =
    useComunicacionesPorDocente()
  const { data: interacciones, isLoading: loadingInt } =
    useInteraccionesDocente()
  const { data: ultimasAcciones, isLoading: loadingUA } =
    useUltimasAcciones(50)

  function handleApplyRango() {
    setRangoFechas({ desde: desdeInput, hasta: hastaInput })
  }

  return (
    <div className="space-y-8">
      {/* 1. Acciones por día */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-700">
            Acciones por día
          </h3>
          <div className="flex items-center gap-2 text-xs">
            <input
              type="date"
              value={desdeInput}
              onChange={(e) => setDesdeInput(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1 text-xs"
            />
            <span className="text-gray-400">—</span>
            <input
              type="date"
              value={hastaInput}
              onChange={(e) => setHastaInput(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1 text-xs"
            />
            <button
              type="button"
              onClick={handleApplyRango}
              className="px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
            >
              Aplicar
            </button>
          </div>
        </div>
        {loadingAcciones ? (
          <p className="text-xs text-gray-400">Cargando gráfico...</p>
        ) : (
          <AccionesPorDiaChart items={accionesPorDia?.items ?? []} />
        )}
      </section>

      {/* 2. Estado comunicaciones por docente */}
      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          Estado de comunicaciones por docente
        </h3>
        {loadingCom ? (
          <p className="text-xs text-gray-400">Cargando...</p>
        ) : (
          <EstadoComunicacionesTable
            items={comunicaciones?.items ?? []}
          />
        )}
      </section>

      {/* 3. Interacciones docente × materia */}
      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          Interacciones docente × materia
        </h3>
        {loadingInt ? (
          <p className="text-xs text-gray-400">Cargando...</p>
        ) : (
          <InteraccionesDocente items={interacciones?.items ?? []} />
        )}
      </section>

      {/* 4. Últimas acciones */}
      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          Últimas 50 acciones
        </h3>
        {loadingUA ? (
          <p className="text-xs text-gray-400">Cargando...</p>
        ) : (
          <LogAccionesTable items={ultimasAcciones?.items ?? []} />
        )}
      </section>
    </div>
  )
}
