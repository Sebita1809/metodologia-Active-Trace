## Why

El formulario de edición de usuarios en el panel de ADMIN no muestra el rol del usuario (docente, coordinador, etc.) y los campos bancarios (CBU, alias CBU, modalidad de cobro) se comportan como obligatorios al editar, cuando deberían ser opcionales. Esto dificulta la gestión diaria del administrador.

## What Changes

- Agregar campo `roles` al `UsuarioResponse` del backend para que la API devuelva los roles del usuario desde `Asignacion`
- Agregar columna `roles` en la tabla de listado de usuarios (`UsuariosAdminTable`)
- Agregar campo `rol` en el formulario de edición/creación (`UsuarioAdminForm`) con selector de rol
- Agregar `roles` en la vista de detalle (`UsuarioDetalleView`)
- Corregir la validación Zod de `cbu`, `alias_cbu` y `modalidad_cobro` para que sean estrictamente opcionales y no bloqueen el envío del formulario cuando están vacíos
- Corregir el envío del PATCH para que los campos vacíos se envíen como `null` y no como string vacío, evitando que el backend sobrescriba valores con datos inválidos

## Capabilities

### New Capabilities

- `admin-usuario-roles`: mostrar y gestionar el rol del usuario desde el panel de administración

### Modified Capabilities

- *(ninguno — no cambian requerimientos de specs existentes, solo comportamiento de UI y validación)*

## Impact

- **Backend**: `app/schemas/usuario.py` — agregar campo `roles` a `UsuarioResponse`
- **Frontend**: 
  - `features/admin/usuarios/types/schemas.ts` — corregir Zod para CBU/alias/modalidad
  - `features/admin/usuarios/types/index.ts` — agregar `roles` al type
  - `features/admin/usuarios/components/UsuarioAdminForm.tsx` — agregar selector de rol
  - `features/admin/usuarios/components/UsuariosAdminTable.tsx` — agregar columna roles
  - `features/admin/usuarios/components/UsuarioDetalleView.tsx` — mostrar roles
  - `features/admin/usuarios/pages/UsuariosAdminPage.tsx` — ajustar handlers si es necesario
