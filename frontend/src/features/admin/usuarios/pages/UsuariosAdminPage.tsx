/**
 * UsuariosAdminPage.tsx — Main page for user management (ADMIN).
 *
 * Table filterable by nombre/email. Botón "Nuevo usuario".
 * SECURITY: CBU/alias only in body, never in URL params.
 * <200 LOC, no `any`, no class components.
 */

import { useState, useMemo } from 'react'
import {
  useUsuariosAdmin,
  useCreateUsuarioAdmin,
  useUpdateUsuarioAdmin,
} from '../hooks/useUsuariosAdmin'
import { UsuariosAdminTable } from '../components/UsuariosAdminTable'
import { UsuarioAdminForm } from '../components/UsuarioAdminForm'
import type { UsuarioAdmin, EstadoUsuario } from '../types'
import type { UsuarioAdminData } from '../types/schemas'

export function UsuariosAdminPage() {
  const { data, isLoading, error } = useUsuariosAdmin()
  const createMutation = useCreateUsuarioAdmin()
  const updateMutation = useUpdateUsuarioAdmin()

  const [search, setSearch] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingUser, setEditingUser] = useState<UsuarioAdmin | null>(null)

  const filteredUsuarios = useMemo(() => {
    if (!data) return []
    if (!search) return data
    const q = search.toLowerCase()
    return data.filter(
      (u) =>
        u.nombre.toLowerCase().includes(q) ||
        u.apellidos.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q),
    )
  }, [data, search])

  const _normalize = (v: string | null | undefined): string | null =>
    v === '' ? null : (v ?? null)

  function handleCreate(formData: UsuarioAdminData) {
    createMutation.mutate(
      {
        nombre: formData.nombre,
        apellidos: formData.apellidos,
        email: formData.email,
        dni: formData.dni ?? null,
        cuil: formData.cuil ?? null,
        cbu: _normalize(formData.cbu),
        alias_cbu: _normalize(formData.alias_cbu),
        banco: formData.banco ?? null,
        regional: formData.regional ?? null,
        legajo: formData.legajo ?? null,
        legajo_profesional: formData.legajo_profesional ?? null,
        sexo: formData.sexo ?? null,
        modalidad_cobro: _normalize(formData.modalidad_cobro),
        facturador: formData.facturador,
        estado: formData.estado,
      },
      { onSuccess: () => setShowCreateForm(false) },
    )
  }

  function handleUpdate(formData: UsuarioAdminData) {
    if (!editingUser) return
    updateMutation.mutate(
      {
        id: editingUser.id,
        data: {
          nombre: formData.nombre,
          apellidos: formData.apellidos,
          email: formData.email,
          dni: formData.dni ?? null,
          cuil: formData.cuil ?? null,
          cbu: _normalize(formData.cbu),         // body only — service enforces this
          alias_cbu: _normalize(formData.alias_cbu), // body only
          banco: formData.banco ?? null,
          regional: formData.regional ?? null,
          legajo: formData.legajo ?? null,
          legajo_profesional: formData.legajo_profesional ?? null,
          sexo: formData.sexo ?? null,
          modalidad_cobro: _normalize(formData.modalidad_cobro),
          facturador: formData.facturador,
          estado: formData.estado,
        },
      },
      { onSuccess: () => setEditingUser(null) },
    )
  }

  function handleToggleEstado(usuario: UsuarioAdmin) {
    const nuevoEstado: EstadoUsuario =
      usuario.estado === 'Activo' ? 'Inactivo' : 'Activo'
    updateMutation.mutate({ id: usuario.id, data: { estado: nuevoEstado } })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Usuarios</h1>
        <button
          type="button"
          onClick={() => { setShowCreateForm(true); setEditingUser(null) }}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
        >
          + Nuevo usuario
        </button>
      </div>

      <input
        type="search"
        placeholder="Buscar por nombre, apellido o email..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />

      {showCreateForm && (
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Nuevo usuario</h3>
          <UsuarioAdminForm
            onSubmit={handleCreate}
            onCancel={() => setShowCreateForm(false)}
            isPending={createMutation.isPending}
          />
        </div>
      )}

      {editingUser && (
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            Editar: {editingUser.apellidos}, {editingUser.nombre}
          </h3>
          <UsuarioAdminForm
            initial={editingUser}
            onSubmit={handleUpdate}
            onCancel={() => setEditingUser(null)}
            isPending={updateMutation.isPending}
          />
        </div>
      )}

      {isLoading && (
        <p className="text-sm text-gray-500 py-4">Cargando...</p>
      )}
      {error && (
        <p className="text-sm text-red-600 py-4">Error al cargar usuarios.</p>
      )}
      {!isLoading && !error && (
        <UsuariosAdminTable
          usuarios={filteredUsuarios}
          onEdit={(u) => { setEditingUser(u); setShowCreateForm(false) }}
          onToggleEstado={handleToggleEstado}
          isPendingToggle={updateMutation.isPending}
        />
      )}
    </div>
  )
}
