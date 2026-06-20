import { useNavigate } from 'react-router-dom'

export function AccessDeniedPage() {
  const navigate = useNavigate()

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="text-center p-8">
        <p className="text-5xl font-bold text-gray-300 mb-4">403</p>
        <h1 className="text-2xl font-semibold text-gray-900 mb-2">
          Acceso denegado
        </h1>
        <p className="text-gray-500 text-sm mb-6">
          No tenés los permisos necesarios para acceder a esta sección.
          Contactá a tu administrador si creés que es un error.
        </p>
        <button
          type="button"
          onClick={() => navigate('/dashboard')}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded transition-colors"
        >
          Ir al dashboard
        </button>
      </div>
    </div>
  )
}
