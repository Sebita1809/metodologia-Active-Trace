import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useResetPassword } from '../hooks/useResetPassword'
import { resetSchema, type ResetFormData } from '../types'

export function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const resetMutation = useResetPassword()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetFormData>({
    resolver: zodResolver(resetSchema),
  })

  // No token in URL
  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-md bg-white rounded-lg shadow p-8 text-center">
          <h1 className="text-2xl font-semibold text-gray-900 mb-4">
            Enlace inválido
          </h1>
          <p className="text-sm text-gray-600 mb-6">
            El enlace para restablecer la contraseña es inválido o ha expirado.
          </p>
          <button
            type="button"
            onClick={() => navigate('/forgot')}
            className="text-sm text-blue-600 hover:underline"
          >
            Solicitar un nuevo enlace
          </button>
        </div>
      </div>
    )
  }

  if (resetMutation.isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-md bg-white rounded-lg shadow p-8 text-center">
          <h1 className="text-2xl font-semibold text-gray-900 mb-4">
            Contraseña actualizada
          </h1>
          <p className="text-sm text-gray-600 mb-6">
            Tu contraseña fue actualizada correctamente.
          </p>
          <button
            type="button"
            onClick={() => navigate('/login')}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded text-sm transition-colors"
          >
            Iniciar sesión
          </button>
        </div>
      </div>
    )
  }

  const onSubmit = async (data: ResetFormData) => {
    if (!token) return
    try {
      await resetMutation.mutateAsync({ token, password: data.password })
    } catch {
      // Error shown via mutation state
    }
  }

  const getErrorMessage = () => {
    if (!resetMutation.error) return null
    const err = resetMutation.error as { response?: { status?: number } }
    if (err.response?.status === 400 || err.response?.status === 422) {
      return 'El enlace es inválido o ya fue utilizado. Solicitá uno nuevo.'
    }
    return 'Error al actualizar la contraseña. Intentá de nuevo.'
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md bg-white rounded-lg shadow p-8">
        <h1 className="text-2xl font-semibold text-gray-900 mb-6">
          Nueva contraseña
        </h1>

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Nueva contraseña
            </label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              {...register('password')}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {errors.password && (
              <p className="mt-1 text-xs text-red-600" role="alert">
                {errors.password.message}
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="confirmPassword"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Confirmar contraseña
            </label>
            <input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              {...register('confirmPassword')}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {errors.confirmPassword && (
              <p className="mt-1 text-xs text-red-600" role="alert">
                {errors.confirmPassword.message}
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
            disabled={resetMutation.isPending}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-2 px-4 rounded text-sm transition-colors"
          >
            {resetMutation.isPending ? 'Actualizando...' : 'Actualizar contraseña'}
          </button>
        </form>
      </div>
    </div>
  )
}
