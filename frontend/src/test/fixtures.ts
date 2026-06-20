import type { JwtClaims, Role } from '@/shared/services/jwtDecode'

function base64url(str: string): string {
  return btoa(str)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
}

export function makeFakeJwt(
  claims: Partial<JwtClaims> & { roles?: Role[] },
  expiresInSeconds = 3600,
): string {
  const header = base64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = base64url(
    JSON.stringify({
      sub: 'user-123',
      tenant_id: 'tenant-abc',
      roles: ['ADMIN'] as Role[],
      exp: Math.floor(Date.now() / 1000) + expiresInSeconds,
      ...claims,
    }),
  )
  const signature = base64url('fake-signature')
  return `${header}.${payload}.${signature}`
}

export function makeExpiredJwt(roles: Role[] = ['ADMIN']): string {
  return makeFakeJwt({ roles }, -10)
}
