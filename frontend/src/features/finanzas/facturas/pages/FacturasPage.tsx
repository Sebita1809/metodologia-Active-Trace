/**
 * FacturasPage.tsx — Main page for FINANZAS: facturas (comprobantes).
 *
 * Filters: docente, estado, rango de fechas, búsqueda libre.
 * Table of comprobantes. Button to register a new factura.
 * <200 LOC, no `any`, no class components.
 */

import { useState } from 'react'
import { useFacturas, useCreateFactura } from '../hooks/useFacturas'
import { FacturasTable } from '../components/FacturasTable'
import { FacturaForm } from '../components/FacturaForm'
import type { FacturaFilters, EstadoFactura } from '../types'
import type { FacturaData } from '../types/schemas'

export function FacturasPage() {
  const [filters, setFilters] = useState<FacturaFilters>({ limit: 50 })
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [estadoFilter, setEstadoFilter] = useState<EstadoFactura | ''>('')
  const [mesFilter, setMesFilter] = useState<number | ''>('')
  const [anioFilter, setAnioFilter] = useState<number | ''>(new Date().getFullYear())

  const { data, isLoading, error } = useFacturas(filters)
  const createMutation = useCreateFactura()

  function handleApplyFilters() {
    setFilters({
      ...(estadoFilter ? { estado: estadoFilter as EstadoFactura } : {}),
      ...(mesFilter ? { periodo_mes: mesFilter as number } : {}),
      ...(anioFilter ? { periodo_anio: anioFilter as number } : {}),
      limit: 50,
    })
  }

  function handleCreate(formData: FacturaData) {
    createMutation.mutate(
      {
        usuario_id: formData.usuario_id,
        periodo_mes: formData.periodo_mes,
        periodo_anio: formData.periodo_anio,
        detalle: formData.detalle,
        referencia_archivo: formData.referencia_archivo ?? null,
        tamano_kb: formData.tamano_kb ?? null,
        monto: formData.monto,
      },
      { onSuccess: () => setShowCreateForm(false) },
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Facturas</h1>
        <button
          type="button"
          onClick={() => setShowCreateForm(true)}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
        >
          + Registrar factura
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-end bg-gray-50 p-4 rounded-lg border border-gray-200">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Estado</label>
          <select
            value={estadoFilter}
            onChange={(e) => setEstadoFilter(e.target.value as EstadoFactura | '')}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todos</option>
            <option value="Pendiente">Pendiente</option>
            <option value="Abonada">Abonada</option>
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Mes</label>
          <select
            value={mesFilter}
            onChange={(e) => setMesFilter(e.target.value ? parseInt(e.target.value, 10) : '')}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todos</option>
            {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Año</label>
          <input
            type="number"
            value={anioFilter}
            onChange={(e) => setAnioFilter(e.target.value ? parseInt(e.target.value, 10) : '')}
            min={2000}
            max={new Date().getFullYear() + 1}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-24"
          />
        </div>

        <button
          type="button"
          onClick={handleApplyFilters}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
        >
          Filtrar
        </button>
      </div>

      {/* Create form */}
      {showCreateForm && (
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Nueva factura</h3>
          <FacturaForm
            onSubmit={handleCreate}
            onCancel={() => setShowCreateForm(false)}
            isPending={createMutation.isPending}
          />
        </div>
      )}

      {/* Table */}
      {isLoading && (
        <p className="text-sm text-gray-500 py-4">Cargando...</p>
      )}
      {error && (
        <p className="text-sm text-red-600 py-4">Error al cargar facturas.</p>
      )}
      {data && <FacturasTable facturas={data} />}
    </div>
  )
}
