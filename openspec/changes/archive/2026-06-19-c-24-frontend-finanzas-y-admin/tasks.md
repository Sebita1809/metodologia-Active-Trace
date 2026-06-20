## 1. Preparación

- [x] 1.1 Leer routers `liquidaciones.py`, `facturas.py`, `carreras.py`, `cohortes.py`, `usuarios.py`, `programas.py`, `fechas_academicas.py`, `auditoria.py` para confirmar paths exactos antes de implementar services
- [x] 1.2 Verificar `frontend/package.json` para saber si hay librería de charts disponible (recharts, chart.js, etc.) — decisión afecta la implementación del gráfico de auditoría
- [x] 1.3 Crear estructura de directorios `features/finanzas/{liquidaciones,grilla-salarial,facturas}/` y `features/admin/{estructura,usuarios,programas-fechas}/` y `features/auditoria/`
- [x] 1.4 Definir tipos TypeScript: `Liquidacion`, `LiquidacionSegmentada`, `LiquidacionFilters`, `CerrarLiquidacionRequest` en `finanzas/liquidaciones/types.ts`
- [x] 1.5 Definir tipos: `SalarioBase`, `Plus`, `SalarioBaseForm`, `PlusForm` en `finanzas/grilla-salarial/types.ts`
- [x] 1.6 Definir tipos: `Factura`, `FacturaFilters`, `FacturaForm` en `finanzas/facturas/types.ts`
- [x] 1.7 Definir tipos: `Carrera`, `Cohorte`, `Materia`, `CarreraForm`, `CohorteForm`, `MateriaForm` en `admin/estructura/types.ts`
- [x] 1.8 Definir tipos: `UsuarioAdmin`, `UsuarioAdminForm` (con cbu/alias nunca en query) en `admin/usuarios/types.ts`
- [x] 1.9 Definir tipos: `ProgramaMateria`, `FechaAcademica`, `ProgramaForm`, `FechaAcademicaForm` en `admin/programas-fechas/types.ts`
- [x] 1.10 Definir tipos: `AuditoriaPanelResponse`, `LogAuditoriaItem`, `AuditoriaFilters` en `auditoria/types.ts`
- [x] 1.11 Crear schemas Zod: `LiquidacionFiltrosSchema`, `SalarioBaseSchema`, `PlusSchema`, `FacturaSchema`, `CarreraSchema`, `CohorteSchema`, `MateriaSchema`, `UsuarioAdminSchema`, `ProgramaSchema`, `FechaAcademicaSchema`

## 2. Services

- [x] 2.1 Crear `finanzas/liquidaciones/services/liquidacionesService.ts`: `getLiquidaciones(filters)`, `cerrarLiquidacion(id)`, `exportarLiquidacion(filters)` → blob, `getHistorial()`
- [x] 2.2 Crear `finanzas/grilla-salarial/services/grillaSalarialService.ts`: `getSalariosBase()`, `createSalarioBase(data)`, `updateSalarioBase(id, data)`, `deleteSalarioBase(id)`, `getPlus()`, `createPlus(data)`, `updatePlus(id, data)`, `deletePlus(id)`
- [x] 2.3 Crear `finanzas/facturas/services/facturasService.ts`: `getFacturas(filters)`, `createFactura(data)` multipart, `updateFactura(id, data)`
- [x] 2.4 Crear `admin/estructura/services/estructuraService.ts`: `getCarreras()`, `createCarrera(data)`, `updateCarrera(id, data)`, `getCohortes()`, `createCohorte(data)`, `updateCohorte(id, data)`, `getMaterias()`, `createMateria(data)`, `updateMateria(id, data)`
- [x] 2.5 Crear `admin/usuarios/services/usuariosAdminService.ts`: `getUsuarios()`, `createUsuario(data)`, `updateUsuario(id, data)` — nunca CBU/alias en query string
- [x] 2.6 Crear `admin/programas-fechas/services/programasService.ts`: `getProgramas(filters)`, `createPrograma(data)` multipart; `fechasAcademicasService.ts`: `getFechas(filters)`, `createFecha(data)`, `updateFecha(id, data)`
- [x] 2.7 Crear `auditoria/services/auditoriaService.ts`: `getPanel(filters)`, `getLogCompleto(filters)` — verificar paths exactos antes de implementar

## 3. Hooks

- [x] 3.1 Hooks de liquidaciones: `useLiquidaciones(filters)`, `useCerrarLiquidacion()`, `useHistorialLiquidaciones()`
- [x] 3.2 Hooks de grilla salarial: `useSalariosBase()`, `useCreateSalarioBase()`, `useUpdateSalarioBase()`, `useDeleteSalarioBase()`, `usePlus()`, `useCreatePlus()`, `useUpdatePlus()`, `useDeletePlus()`
- [x] 3.3 Hooks de facturas: `useFacturas(filters)`, `useCreateFactura()`, `useUpdateFactura()`
- [x] 3.4 Hooks de estructura: `useCarreras()`, `useCreateCarrera()`, `useUpdateCarrera()`, `useCohortes()`, `useCreateCohorte()`, `useUpdateCohorte()`, `useMaterias()`, `useCreateMateria()`, `useUpdateMateria()`
- [x] 3.5 Hooks de usuarios admin: `useUsuariosAdmin()`, `useCreateUsuarioAdmin()`, `useUpdateUsuarioAdmin()`
- [x] 3.6 Hooks de programas y fechas: `useProgramas(filters)`, `useCreatePrograma()`, `useFechasAcademicas(filters)`, `useCreateFecha()`, `useUpdateFecha()`
- [x] 3.7 Hooks de auditoría: `useAuditoriaPanel(filters)`, `useLogCompleto(filters)`

## 4. Feature — Liquidaciones

- [x] 4.1 Crear `LiquidacionesPage.tsx` con tabs "Período actual", "Historial" y acceso a "Grilla salarial"
- [x] 4.2 Crear `FiltrosPeriodoForm.tsx`: selectores de cohorte y mes como filtros del período
- [x] 4.3 Crear `LiquidacionSegmentadaView.tsx`: tres secciones (General, NEXO, Factura) con tabla por docente y KPIs "Total sin factura" / "Total con factura" en cabecera
- [x] 4.4 Crear `CerrarLiquidacionDialog.tsx`: diálogo de doble confirmación con período y total. Botón "Cerrar" deshabilitado si la liquidación ya está cerrada. Badge "Cerrada" en filas inmutables
- [x] 4.5 Crear `HistorialLiquidacionesView.tsx`: tabla de períodos cerrados con fecha de cierre y total
- [x] 4.6 Implementar exportación: botón "Exportar" → descarga CSV blob

## 5. Feature — Grilla salarial

- [x] 5.1 Crear `GrillaSalarialPage.tsx` con tabs "Salario base" y "Plus"
- [x] 5.2 Crear `SalariosBaseView.tsx`: tabla de salarios con acciones inline editar/eliminar + botón "Nuevo salario base"
- [x] 5.3 Crear `SalarioBaseForm.tsx` (RHF+Zod): rol (select enum), importe, vigencia_desde, vigencia_hasta. Validar vigencia_hasta > vigencia_desde
- [x] 5.4 Crear `PlusView.tsx`: tabla de plus con acciones inline + botón "Nuevo plus"
- [x] 5.5 Crear `PlusForm.tsx` (RHF+Zod): clave, rol, descripción, importe, vigencia_desde, vigencia_hasta. Validar vigencias. Dialog de confirmación en eliminar

## 6. Feature — Facturas

- [x] 6.1 Crear `FacturasPage.tsx` con filtros (docente, estado, rango de fechas, búsqueda libre) y tabla de comprobantes
- [x] 6.2 Crear `FacturasTable.tsx`: columnas fecha_carga, docente, período, detalle, archivo (link de descarga), tamaño, estado (badge), datos_pago. Acción inline "Cambiar estado"
- [x] 6.3 Crear `FacturaForm.tsx` (RHF+Zod): docente (select), período, detalle, archivo (file input), datos_pago. Enviar como multipart/form-data

## 7. Feature — Estructura académica (ADMIN)

- [x] 7.1 Crear `EstructuraPage.tsx` con tabs "Carreras", "Cohortes", "Materias"
- [x] 7.2 Crear `CarrerasView.tsx`: tabla con código, nombre, estado. Acciones: editar, toggle estado. Botón "Nueva carrera"
- [x] 7.3 Crear `CarreraForm.tsx` (RHF+Zod): código (requerido), nombre (requerido), estado (toggle)
- [x] 7.4 Crear `CohorteView.tsx`: tabla con nombre, año, vigencia_desde, vigencia_hasta, estado. Botón "Nueva cohorte"
- [x] 7.5 Crear `CohorteForm.tsx` (RHF+Zod): nombre, año_inicio, vigencia_desde, vigencia_hasta, estado. Validar fechas
- [x] 7.6 Crear `MateriasView.tsx` + `MateriaForm.tsx` (RHF+Zod): nombre, código opcional, estado. Toggle activo/inactivo

## 8. Feature — Usuarios (ADMIN)

- [x] 8.1 Crear `UsuariosAdminPage.tsx` con tabla filtrable y botón "Nuevo usuario"
- [x] 8.2 Crear `UsuariosAdminTable.tsx`: columnas nombre, identificación, rol, regional, estado, modalidad_cobro. Acciones inline: editar, toggle estado
- [x] 8.3 Crear `UsuarioAdminForm.tsx` (RHF+Zod): nombre, identificación_fiscal, rol (select), regional, banco, cbu (validar formato), alias, modalidad_cobro (factura/liquidación), estado. CBU/alias van solo en body, nunca en URL
- [x] 8.4 Crear `UsuarioDetalleView.tsx`: vista de solo lectura con todos los datos del usuario incluyendo CBU/alias tal como los devuelve la API

## 9. Feature — Programas y fechas académicas (ADMIN + COORDINADOR)

- [x] 9.1 Crear `ProgramasFechasPage.tsx` con tabs "Programas de materia" y "Fechas de evaluaciones"
- [x] 9.2 Crear `ProgramasView.tsx`: tabla de programas con filtros por carrera y cohorte. Botón "Subir programa"
- [x] 9.3 Crear `ProgramaForm.tsx` (RHF+Zod): carrera (select), cohorte (select), materia (select), título, archivo (file input PDF/DOCX). Verificar formato multipart del router antes de implementar
- [x] 9.4 Crear `FechasAcademicasView.tsx` con dos vistas toggle: tabla (materia, tipo, instancia, fecha, cohorte, título) y calendario mensual visual
- [x] 9.5 Crear `FechaAcademicaForm.tsx` (RHF+Zod): materia, tipo (parcial/TP/coloquio), número de instancia, fecha, cohorte, título descriptivo
- [x] 9.6 Implementar calendario visual: grilla mensual con eventos de evaluaciones (Tailwind puro, sin librería externa)

## 10. Feature — Auditoría

- [x] 10.1 Crear `AuditoriaPage.tsx` con tabs "Panel" (COORDINADOR+ADMIN) y "Log completo" (solo ADMIN, oculto para COORDINADOR)
- [x] 10.2 Crear `AuditoriaPanelView.tsx` con filtros (rango de fechas, materia, usuario, estado actividad) y cuatro sub-secciones
- [x] 10.3 Crear `AccionesPorDiaChart.tsx`: verificar `package.json` para charts. Si hay librería instalada usarla; si no, implementar gráfico de barras SVG nativo con Tailwind
- [x] 10.4 Crear `EstadoComunicacionesTable.tsx`: tabla por docente con columnas Pendiente/Enviando/OK/Fallido/Cancelado
- [x] 10.5 Crear `InteraccionesDocente.tsx`: tabla de métricas de uso por docente y materia (análisis, importación, envío, etc.)
- [x] 10.6 Crear `LogAccionesTable.tsx`: tabla de últimas N acciones con columnas fecha/hora, usuario, materia, acción, registros_afectados, ip, agente
- [x] 10.7 Crear `LogCompletoView.tsx`: igual que `LogAccionesTable` pero sin límite de registros, solo visible con `RequireRole(['ADMIN'])`

## 11. Integración y routing

- [x] 11.1 Agregar rutas en `frontend/src/router/index.tsx`:
  - `/finanzas/liquidaciones` — `RequireRole(['FINANZAS', 'ADMIN'])`
  - `/finanzas/grilla-salarial` — `RequireRole(['FINANZAS'])`
  - `/finanzas/facturas` — `RequireRole(['FINANZAS'])`
  - `/admin/estructura` — `RequireRole(['ADMIN'])`
  - `/admin/usuarios` — `RequireRole(['ADMIN'])`
  - `/admin/programas-fechas` — `RequireRole(['ADMIN', 'COORDINADOR'])`
  - `/auditoria` — `RequireRole(['COORDINADOR', 'ADMIN'])`
  - `/auditoria/log-completo` — `RequireRole(['ADMIN'])`
- [x] 11.2 Agregar secciones de nav en `NavMenu.tsx`: "Finanzas" (FINANZAS/ADMIN), "Administración" (ADMIN), "Auditoría" (COORDINADOR/ADMIN) — condicionales por rol
- [x] 11.3 Verificar que COORDINADOR no puede acceder a `/finanzas/*` ni `/admin/*` (fail-closed)

## 12. Tests

- [x] 12.1 Tests de `LiquidacionSegmentadaView`: render con tres segmentos, KPIs correctos, estado vacío
- [x] 12.2 Tests de `CerrarLiquidacionDialog`: no cierra sin confirmación, liquidación ya cerrada deshabilita botón, confirmar dispara mutation
- [x] 12.3 Tests de `GrillaSalarialPage`: crear salario base con validación de fechas, crear plus, eliminar con confirmación
- [x] 12.4 Tests de `EstructuraPage`: crear carrera, toggle estado cohorte, validación de fechas cohorte
- [x] 12.5 Tests de `UsuarioAdminForm`: validación de campos requeridos, CBU nunca en params de URL (spy en axios)
- [x] 12.6 Tests de `AuditoriaPanelView`: panel vacío con estado informativo, filtro por fecha actualiza sub-vistas, COORDINADOR no ve tab "Log completo"
