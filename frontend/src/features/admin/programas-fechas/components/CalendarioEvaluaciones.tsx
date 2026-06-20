/**
 * CalendarioEvaluaciones.tsx — Monthly calendar grid showing evaluation events.
 *
 * Pure Tailwind/SVG — no external chart library.
 * Shows all fechas académicas in a monthly calendar view.
 */

import type { FechaAcademica } from '../types'

const DIAS_SEMANA = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']

const TIPO_COLORS: Record<string, string> = {
  parcial: 'bg-blue-100 text-blue-700 border-blue-200',
  TP: 'bg-green-100 text-green-700 border-green-200',
  coloquio: 'bg-purple-100 text-purple-700 border-purple-200',
}

interface CalendarioEvaluacionesProps {
  fechas: FechaAcademica[]
  mes: number  // 1-12
  anio: number
}

export function CalendarioEvaluaciones({
  fechas,
  mes,
  anio,
}: CalendarioEvaluacionesProps) {
  // Build calendar grid
  const firstDay = new Date(anio, mes - 1, 1)
  const lastDay = new Date(anio, mes, 0)
  const startWeekDay = firstDay.getDay()
  const daysInMonth = lastDay.getDate()

  // Map fechas by day
  const eventosPorDia = new Map<number, FechaAcademica[]>()
  for (const fecha of fechas) {
    const d = new Date(fecha.fecha)
    if (d.getFullYear() === anio && d.getMonth() + 1 === mes) {
      const day = d.getDate()
      const events = eventosPorDia.get(day) ?? []
      events.push(fecha)
      eventosPorDia.set(day, events)
    }
  }

  // Build grid cells
  const cells: (number | null)[] = []
  for (let i = 0; i < startWeekDay; i++) {
    cells.push(null)
  }
  for (let d = 1; d <= daysInMonth; d++) {
    cells.push(d)
  }
  // Pad to complete last row
  while (cells.length % 7 !== 0) {
    cells.push(null)
  }

  const NOMBRE_MES = [
    '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
  ]

  return (
    <div className="space-y-2">
      <div className="text-center text-sm font-semibold text-gray-700">
        {NOMBRE_MES[mes]} {anio}
      </div>

      <div className="border border-gray-200 rounded-lg overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-7 bg-gray-50">
          {DIAS_SEMANA.map((d) => (
            <div
              key={d}
              className="text-center text-xs font-medium text-gray-500 py-2"
            >
              {d}
            </div>
          ))}
        </div>

        {/* Grid */}
        <div className="grid grid-cols-7 divide-x divide-y divide-gray-100">
          {cells.map((day, i) => {
            const eventos = day ? (eventosPorDia.get(day) ?? []) : []
            const today = new Date()
            const isToday =
              day !== null &&
              today.getDate() === day &&
              today.getMonth() + 1 === mes &&
              today.getFullYear() === anio

            return (
              <div
                key={i}
                className={[
                  'min-h-[80px] p-1 text-xs',
                  day === null ? 'bg-gray-50' : 'bg-white',
                  isToday ? 'bg-blue-50' : '',
                ].join(' ')}
              >
                {day !== null && (
                  <>
                    <div
                      className={[
                        'w-5 h-5 flex items-center justify-center rounded-full mb-1 font-medium',
                        isToday
                          ? 'bg-blue-600 text-white text-xs'
                          : 'text-gray-700',
                      ].join(' ')}
                    >
                      {day}
                    </div>
                    <div className="space-y-0.5">
                      {eventos.slice(0, 2).map((e) => (
                        <div
                          key={e.id}
                          title={e.titulo}
                          className={[
                            'truncate px-1 py-0.5 rounded border text-xs',
                            TIPO_COLORS[e.tipo] ?? 'bg-gray-100 text-gray-600',
                          ].join(' ')}
                        >
                          {e.tipo === 'parcial' ? 'P' : e.tipo === 'TP' ? 'T' : 'C'}
                          {e.numero} — {e.titulo.slice(0, 12)}
                        </div>
                      ))}
                      {eventos.length > 2 && (
                        <div className="text-gray-400 text-xs pl-1">
                          +{eventos.length - 2} más
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-4 text-xs">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-blue-200 inline-block" />
          Parcial
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-green-200 inline-block" />
          TP
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-purple-200 inline-block" />
          Coloquio
        </span>
      </div>
    </div>
  )
}
