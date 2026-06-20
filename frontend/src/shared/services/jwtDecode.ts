export type Role =
  | 'ALUMNO'
  | 'TUTOR'
  | 'PROFESOR'
  | 'COORDINADOR'
  | 'NEXO'
  | 'ADMIN'
  | 'FINANZAS'

export interface JwtClaims {
  sub: string
  tenant_id: string
  roles: Role[]
  exp: number
}

/**
 * Decodes the payload of a JWT for UI purposes only.
 * Does NOT verify the signature — the backend is the security authority.
 */
export function decodeJwt(token: string): JwtClaims | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null

    const payload = parts[1]
    // Fix base64url padding
    const padded = payload.replace(/-/g, '+').replace(/_/g, '/').padEnd(
      payload.length + ((4 - (payload.length % 4)) % 4),
      '='
    )
    const decoded = atob(padded)
    const parsed = JSON.parse(decoded) as unknown

    if (!isJwtClaims(parsed)) return null

    return parsed
  } catch {
    return null
  }
}

function isJwtClaims(value: unknown): value is JwtClaims {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  return (
    typeof v['sub'] === 'string' &&
    typeof v['tenant_id'] === 'string' &&
    Array.isArray(v['roles']) &&
    typeof v['exp'] === 'number'
  )
}

export function isTokenExpired(claims: JwtClaims): boolean {
  return Date.now() / 1000 >= claims.exp
}
