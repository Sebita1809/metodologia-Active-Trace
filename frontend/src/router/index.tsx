import { createBrowserRouter, Navigate } from 'react-router-dom'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { TwoFactorPage } from '@/features/auth/pages/TwoFactorPage'
import { ForgotPasswordPage } from '@/features/auth/pages/ForgotPasswordPage'
import { ResetPasswordPage } from '@/features/auth/pages/ResetPasswordPage'
import { DashboardPage } from '@/features/dashboard/pages/DashboardPage'
import { AppShell } from '@/shared/components/AppShell'
import { RequireAuth } from '@/shared/components/RequireAuth'
import { RequireRole } from '@/shared/components/RequireRole'
import { AccessDeniedPage } from '@/shared/components/AccessDeniedPage'
import { GestionComisionPage } from '@/features/gestion-comision/pages/GestionComisionPage'
// Coordinacion pages (C-23)
import { EquiposPage } from '@/features/coordinacion/equipos/pages/EquiposPage'
import { AvisosPage } from '@/features/coordinacion/avisos/components/AvisosPage'
import { TareasPage } from '@/features/coordinacion/tareas/pages/TareasPage'
import { EncuentrosAdminPage } from '@/features/coordinacion/encuentros/components/EncuentrosAdminPage'
import { ColoquiosPage } from '@/features/coordinacion/coloquios/components/ColoquiosPage'
import { MonitorGeneralPage } from '@/features/coordinacion/monitor-general/components/MonitorGeneralPage'
import { AprobacionComunicacionesPage } from '@/features/coordinacion/comunicaciones/components/AprobacionComunicacionesPage'
// Finanzas pages (C-24)
import { LiquidacionesPage } from '@/features/finanzas/liquidaciones/pages/LiquidacionesPage'
import { GrillaSalarialPage } from '@/features/finanzas/grilla-salarial/pages/GrillaSalarialPage'
import { FacturasPage } from '@/features/finanzas/facturas/pages/FacturasPage'
// Admin pages (C-24)
import { EstructuraPage } from '@/features/admin/estructura/pages/EstructuraPage'
import { UsuariosAdminPage } from '@/features/admin/usuarios/pages/UsuariosAdminPage'
import { ProgramasFechasPage } from '@/features/admin/programas-fechas/pages/ProgramasFechasPage'
// Auditoria pages (C-24)
import { AuditoriaPage } from '@/features/auditoria/pages/AuditoriaPage'

export const router = createBrowserRouter([
  // Public auth routes (no shell)
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/login/2fa',
    element: <TwoFactorPage />,
  },
  {
    path: '/forgot',
    element: <ForgotPasswordPage />,
  },
  {
    path: '/reset',
    element: <ResetPasswordPage />,
  },

  // Private routes — wrapped in RequireAuth + AppShell
  {
    path: '/',
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: <DashboardPage />,
      },
      {
        path: 'gestion',
        element: (
          <div className="p-4">
            <h1 className="text-xl font-semibold">Gestión</h1>
            <p className="text-gray-500 text-sm mt-2">Módulo en desarrollo.</p>
          </div>
        ),
      },
      {
        path: 'comision',
        element: (
          <RequireRole roles={['PROFESOR', 'TUTOR']}>
            <GestionComisionPage />
          </RequireRole>
        ),
      },
      // -----------------------------------------------------------------
      // Tareas — shared route, TareasPage bifurcates by role internally
      // -----------------------------------------------------------------
      {
        path: 'tareas',
        element: (
          <RequireRole roles={['TUTOR', 'PROFESOR', 'COORDINADOR', 'ADMIN']}>
            <TareasPage />
          </RequireRole>
        ),
      },
      // -----------------------------------------------------------------
      // Coordinacion routes (C-23) — COORDINADOR and ADMIN only
      // -----------------------------------------------------------------
      {
        path: 'coordinacion',
        children: [
          {
            path: 'equipos',
            element: (
              <RequireRole roles={['COORDINADOR', 'ADMIN']}>
                <EquiposPage />
              </RequireRole>
            ),
          },
          {
            path: 'avisos',
            element: (
              <RequireRole roles={['COORDINADOR', 'ADMIN']}>
                <AvisosPage />
              </RequireRole>
            ),
          },
          {
            path: 'encuentros',
            element: (
              <RequireRole roles={['COORDINADOR', 'ADMIN']}>
                <EncuentrosAdminPage />
              </RequireRole>
            ),
          },
          {
            path: 'coloquios',
            element: (
              <RequireRole roles={['COORDINADOR', 'ADMIN']}>
                <ColoquiosPage />
              </RequireRole>
            ),
          },
          {
            path: 'monitor-general',
            element: (
              <RequireRole roles={['COORDINADOR', 'ADMIN']}>
                <MonitorGeneralPage />
              </RequireRole>
            ),
          },
          {
            path: 'comunicaciones/aprobacion',
            element: (
              <RequireRole roles={['COORDINADOR', 'ADMIN']}>
                <AprobacionComunicacionesPage />
              </RequireRole>
            ),
          },
        ],
      },
      // -----------------------------------------------------------------
      // Finanzas routes (C-24) — FINANZAS and ADMIN
      // -----------------------------------------------------------------
      {
        path: 'finanzas',
        children: [
          {
            path: 'liquidaciones',
            element: (
              <RequireRole roles={['FINANZAS', 'ADMIN']}>
                <LiquidacionesPage />
              </RequireRole>
            ),
          },
          {
            path: 'grilla-salarial',
            element: (
              <RequireRole roles={['FINANZAS']}>
                <GrillaSalarialPage />
              </RequireRole>
            ),
          },
          {
            path: 'facturas',
            element: (
              <RequireRole roles={['FINANZAS']}>
                <FacturasPage />
              </RequireRole>
            ),
          },
        ],
      },
      // -----------------------------------------------------------------
      // Admin routes (C-24) — ADMIN only (programas-fechas: ADMIN+COORDINADOR)
      // -----------------------------------------------------------------
      {
        path: 'admin',
        children: [
          {
            path: 'estructura',
            element: (
              <RequireRole roles={['ADMIN']}>
                <EstructuraPage />
              </RequireRole>
            ),
          },
          {
            path: 'usuarios',
            element: (
              <RequireRole roles={['ADMIN']}>
                <UsuariosAdminPage />
              </RequireRole>
            ),
          },
          {
            path: 'programas-fechas',
            element: (
              <RequireRole roles={['ADMIN', 'COORDINADOR']}>
                <ProgramasFechasPage />
              </RequireRole>
            ),
          },
        ],
      },
      // -----------------------------------------------------------------
      // Auditoría routes (C-24) — COORDINADOR and ADMIN
      // Log completo gated inside AuditoriaPage for ADMIN only
      // -----------------------------------------------------------------
      {
        path: 'auditoria',
        element: (
          <RequireRole roles={['COORDINADOR', 'ADMIN']}>
            <AuditoriaPage />
          </RequireRole>
        ),
      },
      {
        path: 'alumnos',
        element: (
          <div className="p-4">
            <h1 className="text-xl font-semibold">Alumnos</h1>
            <p className="text-gray-500 text-sm mt-2">Módulo en desarrollo.</p>
          </div>
        ),
      },
      {
        path: '403',
        element: <AccessDeniedPage />,
      },
    ],
  },

  // Fallback
  {
    path: '*',
    element: <Navigate to="/dashboard" replace />,
  },
])
