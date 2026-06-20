import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate } from 'react-router-dom'
import { useLogin } from '../hooks/useLogin'
import { useAuth } from '../context/AuthContext'
import { loginSchema, isLoginSuccessResponse, type LoginFormData } from '../types'

export function LoginPage() {
  const navigate = useNavigate()
  const { setSession } = useAuth()
  const loginMutation = useLogin()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginFormData) => {
    try {
      const result = await loginMutation.mutateAsync(data)

      if (isLoginSuccessResponse(result)) {
        setSession(result.access_token, result.refresh_token)
        navigate('/dashboard', { replace: true })
      } else {
        // requires_2fa
        navigate('/login/2fa', {
          state: { partial_token: result.partial_token },
          replace: true,
        })
      }
    } catch {
      // Error is handled via mutation.error state below
    }
  }

  const getErrorMessage = () => {
    if (!loginMutation.error) return null
    const err = loginMutation.error as { response?: { status?: number } }
    const status = err.response?.status
    if (status === 404) return 'Institución no encontrada'
    if (status === 401) return 'Credenciales incorrectas'
    if (status === 429) return 'Demasiados intentos. Intentá más tarde.'
    return 'Error al iniciar sesión. Intentá de nuevo.'
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md bg-white rounded-lg shadow p-8">
        <h1 className="text-2xl font-semibold text-gray-900 mb-6">
          Iniciar sesión
        </h1>

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          <div>
            <label
              htmlFor="tenant"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Institución
            </label>
            <input
              id="tenant"
              type="text"
              autoComplete="organization"
              placeholder="demo"
              {...register('tenant')}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {errors.tenant && (
              <p className="mt-1 text-xs text-red-600" role="alert">
                {errors.tenant.message}
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              {...register('email')}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {errors.email && (
              <p className="mt-1 text-xs text-red-600" role="alert">
                {errors.email.message}
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              {...register('password')}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {errors.password && (
              <p className="mt-1 text-xs text-red-600" role="alert">
                {errors.password.message}
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
            disabled={isSubmitting || loginMutation.isPending}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-2 px-4 rounded text-sm transition-colors"
          >
            {loginMutation.isPending ? 'Ingresando...' : 'Ingresar'}
          </button>
        </form>

        <div className="mt-4 text-center">
          <a
            href="/forgot"
            className="text-sm text-blue-600 hover:underline"
            onClick={(e) => {
              e.preventDefault()
              navigate('/forgot')
            }}
          >
            ¿Olvidaste tu contraseña?
          </a>
        </div>
      </div>
    </div>
  )
}
