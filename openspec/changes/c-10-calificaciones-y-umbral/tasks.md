## 1. Modelo y Migración

- [x] 1.1 Agregar campo `valores_aprobatorios` (JSONB, list[str]) al modelo `UmbralMateria` existente
- [x] 1.2 Crear modelo `Calificacion` en `backend/app/models/domain/calificacion.py` con campos: `entrada_padron_id`, `materia_id`, `actividad`, `nota_numerica`, `nota_textual`, `origen` (enum Importado/Manual), `importado_at`
- [x] 1.3 Agregar `Calificacion` al `__all__` de `backend/app/models/domain/__init__.py`
- [x] 1.4 Crear migración Alembic `008_calificacion_umbral.py` con tabla `calificacion` y alter/creación de `umbral_materia`
- [x] 1.5 Correr migración y verificar que las tablas existan en BD

## 2. Repositorios

- [x] 2.1 Crear `CalificacionRepository` en `backend/app/repositories/usuarios/calificacion_repository.py`
- [x] 2.2 Actualizar `UmbralMateriaRepository` con métodos para `valores_aprobatorios`

## 3. Schemas

- [x] 3.1 Crear `backend/app/schemas/calificaciones.py` con schemas: `CalificacionCreate`, `CalificacionResponse`, `ImportPreviewResponse`, `ImportConfirmRequest`, `UmbralConfigUpdate`, `UmbralConfigResponse`

## 4. Servicio

- [x] 4.1 Crear `CalificacionService` en `backend/app/services/usuarios/calificacion_service.py` con métodos:
  - `import_preview(file, materia_id, cohorte_id)` — procesa archivo, detecta actividades
  - `import_confirm(data, materia_id, cohorte_id)` — crea registros en lote
  - `list(materia_id, cohorte_id)` — lista calificaciones
  - `clear(materia_id, cohorte_id)` — vacía datos (hard delete)
  - Derivation helper para `aprobado` (numérico vs textual)

## 5. Router

- [x] 5.1 Crear `backend/app/api/v1/routers/calificaciones.py` con endpoints:
  - `POST /calificaciones/import/preview` (calificaciones:importar)
  - `POST /calificaciones/import/confirm` (calificaciones:importar)
  - `GET /calificaciones/{materia_id}/{cohorte_id}` (calificaciones:importar)
  - `DELETE /calificaciones/{materia_id}/{cohorte_id}` (calificaciones:importar)
  - `PUT /calificaciones/umbral` (calificaciones:importar)
- [x] 5.2 Registrar router en `backend/app/main.py`

## 6. Tests

- [x] 6.1 Crear `backend/tests/test_calificaciones/__init__.py`
- [x] 6.2 Crear `backend/tests/test_calificaciones/conftest.py` con fixtures (calificacion_data, umbral_data)
- [x] 6.3 Crear `backend/tests/test_calificaciones/test_umbral.py` — tests de configuración de umbral
- [x] 6.4 Crear `backend/tests/test_calificaciones/test_import.py` — tests de importación y derivación de aprobado
- [x] 6.5 Crear `backend/tests/test_calificaciones/test_rbac_calificaciones.py` — tests de permisos
- [x] 6.6 Verificar que todos los tests pasen

## 7. Post-Implementación

- [x] 7.1 Verificar que la API responde con los nuevos endpoints (health: {"status":"ok","database":"up"})
- [x] 7.2 Verificar que la migración no rompe tests existentes (173 passed, 8 pre-existing failures)
