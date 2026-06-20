## 1. Estructura de la feature y tipos

- [x] 1.1 Crear el módulo `frontend/src/features/gestion-comision/` con sub-carpetas `components/{import,umbral,analisis,seguimiento,comunicacion}`, `hooks/`, `services/`, `types/`, `pages/`
- [x] 1.2 Definir en `types/` los tipos de request/response espejando los schemas Pydantic de calificaciones (preview, import, finalización, umbral), análisis (atrasados, ranking, notas-finales, reporte) y comunicaciones (preview, encolar lote, cola), sin `any`
- [x] 1.3 Definir los schemas Zod para los formularios (selección de actividades, umbral, redacción de comunicación, filtros del monitor)

## 2. Servicios de API tipados

- [x] 2.1 `services/calificacionesService`: funciones para `POST /api/calificaciones/preview`, `POST /api/calificaciones/import` (construcción del FormData multipart con form field `request` JSON-encoded), `POST /api/calificaciones/finalizacion-preview`, `GET /api/calificaciones`, `GET`/`PUT /api/calificaciones/umbral`, usando el Axios compartido de `shared/services/api`
- [x] 2.2 `services/analisisService`: funciones para `GET /api/v1/analisis/{atrasados,ranking,notas-finales,reporte}` por `asignacion_id`
- [x] 2.3 `services/comunicacionesService`: funciones para `POST /preview`, `POST /` (encolar lote → `lote_id`), `GET /` (cola por `lote_id`/`estado`), centralizando la base path del módulo de comunicaciones

## 3. Hooks de TanStack Query

- [x] 3.1 Hooks de calificaciones: `useImportPreview`, `useConfirmImport`, `useFinalizacionPreview`, `useUmbral` (get), `useUpsertUmbral`
- [x] 3.2 Hooks de análisis: `useAtrasados`, `useRanking`, `useNotasFinales`, `useReporte` (parametrizados por `asignacion_id`, deshabilitados sin asignación seleccionada)
- [x] 3.3 Hooks de comunicaciones: `usePreviewComunicacion`, `useEnviarComunicacion` (encolar), `useColaComunicaciones(lote_id)` con `refetchInterval` activo solo mientras existan mensajes no terminales

## 4. Selección de comisión y orquestación (gestion-comision-ui)

- [x] 4.1 Test: la página de gestión muestra estado informativo sin comisión seleccionada y no dispara peticiones de datos académicos
- [x] 4.2 Implementar el selector de comisión y el contexto local de `asignacion_id` que alimenta las sub-vistas
- [x] 4.3 Test: al seleccionar comisión sin datos, las sub-vistas muestran estado "sin datos" en lugar de tablas vacías
- [x] 4.4 Implementar la página `pages/GestionComisionPage` que orquesta las sub-vistas y los estados informativos
- [x] 4.5 Test + manejo del `403` del backend como acceso denegado (fail-closed)

## 5. Importación de calificaciones (importacion-calificaciones-ui)

- [x] 5.1 Test: subir archivo → preview muestra actividades detectadas sin persistir (mock de `POST /preview`)
- [x] 5.2 Implementar el componente de subida + preview de actividades
- [x] 5.3 Test: error `422` en preview muestra mensaje y permite reintentar
- [x] 5.4 Test: selección de actividades + confirmación envía el shape multipart correcto y refleja importación (`201`)
- [x] 5.5 Implementar la selección de actividades (RHF) y la confirmación de importación
- [x] 5.6 Test: confirmar sin actividades seleccionadas queda bloqueado

## 6. Entregas sin corregir + export

- [x] 6.1 Test: subir reporte de finalización muestra la tabla de posibles entregas sin corregir (mock de `POST /finalizacion-preview`)
- [x] 6.2 Implementar el componente de detección de entregas sin corregir
- [x] 6.3 Test: exportar genera y descarga el archivo CSV a partir de los datos recibidos
- [x] 6.4 Implementar el export CSV en cliente (Blob + descarga)

## 7. Configuración de umbral (umbral-configuracion-ui)

- [x] 7.1 Test: muestra umbral por defecto (60 %) cuando no está configurado y el persistido cuando existe
- [x] 7.2 Implementar la vista de umbral (lectura)
- [x] 7.3 Test: guardar umbral válido envía `PUT /umbral` y refleja el valor actualizado; umbral fuera de rango bloqueado por Zod
- [x] 7.4 Implementar el formulario de configuración del umbral (RHF + Zod)

## 8. Análisis académico (analisis-academico-ui)

- [x] 8.1 Test: tabla de atrasados renderiza datos del backend y muestra estado "sin atrasados" con lista vacía
- [x] 8.2 Implementar la tabla de atrasados
- [x] 8.3 Test + implementación: ranking de actividades aprobadas
- [x] 8.4 Test + implementación: notas finales agrupadas
- [x] 8.5 Test + implementación: reportes rápidos con estado informativo sin datos

## 9. Monitor de seguimiento (monitor-seguimiento-ui)

- [x] 9.1 Test: el monitor muestra estado de actividades de la comisión y estado informativo sin datos
- [x] 9.2 Implementar la tabla del monitor de seguimiento
- [x] 9.3 Test: filtros por alumno/correo y por mínimo de actividad cumplida acotan las filas mostradas
- [x] 9.4 Implementar los filtros del monitor (alumno, correo, comisión, actividad, mínimo cumplido)

## 10. Comunicación a atrasados con tracking (comunicacion-atrasados-ui)

- [x] 10.1 Test: selección de destinatarios desde la tabla de atrasados; bloqueo si no hay destinatarios
- [x] 10.2 Implementar la selección de destinatarios
- [x] 10.3 Test: preview de comunicación muestra asunto/cuerpo por destinatario sin encolar (mock de `POST /preview`)
- [x] 10.4 Implementar la previsualización de la comunicación
- [x] 10.5 Test: confirmar encola el lote y recibe `lote_id`, dejando mensajes en Pendiente
- [x] 10.6 Implementar el envío a la cola
- [x] 10.7 Test de integración: tracking refleja transiciones Pendiente → Enviando → OK/Fallido y detiene el polling al llegar todos a estado terminal (mock de `GET /` cola)
- [x] 10.8 Implementar el panel de tracking con `useColaComunicaciones` y `refetchInterval` condicional

## 11. Integración en la app y cierre

- [x] 11.1 Registrar la ruta de gestión de comisión en el router bajo el guard por rol/permiso de C-21
- [x] 11.2 Agregar la entrada de navegación en el shell para PROFESOR/TUTOR
- [x] 11.3 Verificar que toda la suite de tests de la feature pasa (componentes + integración con mocks)
- [x] 11.4 Verificar que cada componente queda < 200 LOC y que no hay `any` ni class components
- [x] 11.5 Marcar C-22 como implementado en CHANGES.md
