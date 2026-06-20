/**
 * types/index.ts — TypeScript types for admin/usuarios feature.
 *
 * Mirror of backend Pydantic schemas (C-07):
 *   - usuario.py: UsuarioResponse, UsuarioCreate, UsuarioUpdate
 *
 * Security: CBU/alias NEVER sent in query strings — only in body JSON.
 *
 * No `any` allowed.
 */

// ---------------------------------------------------------------------------
// UsuarioAdmin — full response (matches UsuarioResponse from backend)
// ---------------------------------------------------------------------------

export type ModalidadCobro = 'Factura' | 'Liquidacion'
export type EstadoUsuario = 'Activo' | 'Inactivo'

export interface UsuarioRolItem {
  rol: string
  materia: string | null
  vigencia: string | null
}

export interface UsuarioAdmin {
  id: string
  tenant_id: string
  nombre: string
  apellidos: string
  email: string         // decrypted by backend
  dni: string | null
  cuil: string | null
  cbu: string | null    // decrypted — displayed as-is; NEVER send in URL params
  alias_cbu: string | null  // same
  banco: string | null
  regional: string | null
  legajo: string | null
  legajo_profesional: string | null
  sexo: string | null
  modalidad_cobro: ModalidadCobro | null
  facturador: boolean
  estado: EstadoUsuario
  roles: UsuarioRolItem[]
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// UsuarioAdminForm — create/update (CBU/alias go only in body, never in URL)
// ---------------------------------------------------------------------------

export interface UsuarioAdminForm {
  nombre: string
  apellidos: string
  email: string
  dni: string | null
  cuil: string | null
  cbu: string | null       // body only — never URL params
  alias_cbu: string | null // body only — never URL params
  banco: string | null
  regional: string | null
  legajo: string | null
  legajo_profesional: string | null
  sexo: string | null
  modalidad_cobro: ModalidadCobro | null
  facturador: boolean
  estado: EstadoUsuario
}
