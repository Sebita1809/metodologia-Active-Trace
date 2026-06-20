import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate, useLocation } from 'react-router-dom'
import { useVerify2fa } from '../hooks/useVerify2fa'
import { useAuth } from '../context/AuthContext'
import { twoFactorSchema, type TwoFactorFormData } from '../types'

interface LocationState {
  partial_token?: string
}

export function TwoFactorPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { setSession } = useAuth()
  const verifyMutation = useVerify2fa()

  const state = location.state as LocationState | null
  const partialToken = state?.partial_token

  // If no partial token, redirect back to login
  useEffect(() => {
    if (!partialToken) {
      navigate('/login', { replace: true })
    }
  }, [partialToken, navigate])

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<TwoFactorFormData>({
    resolver: zodResolver(twoFactorSchema),
  })

  const onSubmit = async (data: TwoFactorFormData) => {
    if (!partialToken) return

    try {
      const result = await verifyMutation.mutateAsync({
        partial_token: partialToken,
        code: data.code,
      })
      setSession(result.access_token, result.refresh_token)
      navigate('/dashboard', { replace: true })
    } catch {
      // Error shown via mutation state
    }
  }

  const getErrorMessage = () => {
    if (!verifyMutation.error) return null
    const err = verifyMutation.error as { response?: { status?: number } }
    if (err.response?.status === 401) {
      return 'Código inválido o token expirado. Volvé a iniciar sesión.'
    }
    return 'Error al verificar el código. Intentá de nuevo.'
  }

  if (!partialToken) return null

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md bg-white rounded-lg shadow p-8">
        <h1 className="text-2xl font-semibold text-gray-900 mb-2">
          Verificación en dos pasos
        </h1>
        <p className="text-sm text-gray-500 mb-6">
          Ingresá el código de 6 dígitos de tu aplicación autenticadora.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          <div>
            <label
              htmlFor="code"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Código TOTP
            </label>
            <input
              id="code"
              type="text"
              inputMode="numeric"
              maxLength={6}
              autoComplete="one-time-code"
              {...register('code')}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm tracking-widest text-center focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {errors.code && (
              <p className="mt-1 text-xs text-red-600" role="alert">
                {errors.code.message}
              </p>
            )}
          </div>

          {getErrorMessage() && (
            <p className="text-sm text-red-600" role="alert">
              {getErrorMessage()}
            </p>
          )}

          <button
            type="submit"
            disabled={verifyMutation.isPending}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-2 px-4 rounded text-sm transition-colors"
          >
            {verifyMutation.isPending ? 'Verificando...' : 'Verificar'}
          </button>
        </form>

        <div className="mt-4 text-center">
          <button
            type="button"
            className="text-sm text-blue-600 hover:underline"
            onClick={() => navigate('/login', { replace: true })}
          >
            Volver al inicio de sesión
          </button>
        </div>
      </div>
    </div>
  )
}
