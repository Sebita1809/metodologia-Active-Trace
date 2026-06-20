/**
 * types/index.ts — TypeScript types for grilla-salarial feature.
 *
 * Mirror of backend Pydantic schemas (C-18):
 *   - salario_base.py: SalarioBaseResponse, SalarioBaseCreate, SalarioBaseUpdate
 *   - salario_plus.py: SalarioPlusResponse, SalarioPlusCreate, SalarioPlusUpdate
 *
 * No `any` allowed.
 */

// ---------------------------------------------------------------------------
// SalarioBase
// ---------------------------------------------------------------------------

export interface SalarioBase {
  id: string
  tenant_id: string
  rol: string
  monto: string
  desde: string  // ISO date string (YYYY-MM-DD)
  hasta: string | null
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface SalarioBaseForm {
  rol: string
  monto: string
  desde: string
  hasta: string | null
}

// ---------------------------------------------------------------------------
// Plus (SalarioPlus)
// ---------------------------------------------------------------------------

export interface Plus {
  id: string
  tenant_id: string
  clave: string
  rol: string
  descripcion: string | null
  monto: string
  desde: string  // ISO date string
  hasta: string | null
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface PlusForm {
  clave: string
  rol: string
  descripcion: string | null
  monto: string
  desde: string
  hasta: string | null
}
