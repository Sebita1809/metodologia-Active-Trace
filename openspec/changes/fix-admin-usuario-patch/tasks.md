## 1. Backend — Agregar roles a UsuarioResponse

- [x] 1.1 Agregar `UsuarioRolItem` y `roles` a `UsuarioResponse` en `app/schemas/usuario.py`
- [x] 1.2 Modificar `usuario_service.py` para cargar `asignaciones.rol` desde la tabla `Asignacion` y exponerlo en el DTO de respuesta
- [x] 1.3 Agregar `selectinload` de `asignaciones` en el repository de Usuario para los métodos `get_by_id` y `get_all`

## 2. Backend — Normalizar empty strings en PATCH

- [x] 2.1 Agregar normalización en `usuario_service.py` → `update()`: si `cbu`, `alias_cbu` o `modalidad_cobro` son string vacío `""`, tratarlos como `None` (no actualizar)

## 3. Frontend — Actualizar tipos y schemas

- [x] 3.1 Agregar campo `roles: ...` al type `UsuarioAdmin` en `types/index.ts`
- [x] 3.2 Actualizar `UsuarioAdminSchema` en `types/schemas.ts`: remover `.or(z.literal(''))` de CBU, dejar solo `.nullable().optional()`

## 4. Frontend — Mostrar roles en tabla y detalle

- [x] 4.1 Agregar columna "Roles" en `UsuariosAdminTable.tsx` con badges
- [x] 4.2 Agregar fila de roles en `UsuarioDetalleView.tsx`

## 5. Frontend — Roles en formulario de edición (read-only)

- [x] 5.1 Agregar campo read-only de roles en `UsuarioAdminForm.tsx` con display de badges

## 6. Frontend — Normalizar empty strings a null en submit

- [x] 6.1 Modificar `handleUpdate` en `UsuariosAdminPage.tsx` para convertir `""` → `null` en cbu, alias_cbu, modalidad_cobro antes de enviar el PATCH

## 7. Tests

- [x] 7.1 Backend: test de `UsuarioResponse` incluye roles
- [x] 7.2 Backend: test de PATCH con empty string no actualiza campo cifrado
- [x] 7.3 Frontend: test de submit con CBU vacío envía null
