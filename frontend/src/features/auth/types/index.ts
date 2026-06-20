import { z } from 'zod'

// ---- Form schemas ----

export const loginSchema = z.object({
  tenant: z.string().min(1, 'La institución es requerida'),
  email: z.string().email('Email inválido'),
  password: z.string().min(1, 'La contraseña es requerida'),
})

export type LoginFormData = z.infer<typeof loginSchema>

export const twoFactorSchema = z.object({
  code: z
    .string()
    .length(6, 'El código debe tener 6 dígitos')
    .regex(/^\d+$/, 'Solo dígitos'),
})

export type TwoFactorFormData = z.infer<typeof twoFactorSchema>

export const forgotSchema = z.object({
  email: z.string().email('Email inválido'),
})

export type ForgotFormData = z.infer<typeof forgotSchema>

export const resetSchema = z
  .object({
    password: z
      .string()
      .min(8, 'Mínimo 8 caracteres')
      .regex(/[A-Z]/, 'Debe contener al menos una mayúscula')
      .regex(/[0-9]/, 'Debe contener al menos un número'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Las contraseñas no coinciden',
    path: ['confirmPassword'],
  })

export type ResetFormData = z.infer<typeof resetSchema>

// ---- Backend response types ----

export interface LoginSuccessResponse {
  access_token: string
  refresh_token: string
}

export interface LoginWith2FaResponse {
  requires_2fa: true
  partial_token: string
}

export type LoginResponse = LoginSuccessResponse | LoginWith2FaResponse

export interface TwoFactorResponse {
  access_token: string
  refresh_token: string
}

export function isLoginSuccessResponse(
  r: LoginResponse,
): r is LoginSuccessResponse {
  return 'access_token' in r && !('requires_2fa' in r)
}
