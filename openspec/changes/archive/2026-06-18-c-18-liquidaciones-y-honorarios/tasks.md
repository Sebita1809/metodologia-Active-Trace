# Tasks — C-18 Liquidaciones y Honorarios

> Governance CRÍTICO. Strict TDD: test que falla → código mínimo → triangulación → refactor. Sin mocks de DB. `extra='forbid'` en todos los schemas. Identidad/tenant SOLO de la sesión. Repositories tenant-scoped y soft delete. Archivos ≤500 LOC.

## 1. Migración

- [x] 1.1 Crear `backend/alembic/versions/016_liquidaciones_honorarios.py` con `revision = "016"`, `down_revision = "015"`
- [x] 1.2 Tabla `salario_base` (BaseTenantModel + rol VARCHAR(30), monto Numeric(12,2) CHECK >= 0, desde Date NOT NULL, hasta Date NULL); índice `ix_salario_base_tenant_rol`
- [x] 1.3 Tabla `salario_plus` (BaseTenantModel + clave VARCHAR(50), rol VARCHAR(30), descripcion Text NULL, monto Numeric(12,2) CHECK >= 0, desde Date NOT NULL, hasta Date NULL); índice `ix_salario_plus_tenant_clave_rol`
- [x] 1.4 Tabla `liquidacion` (BaseTenantModel + usuario_id FK, cohorte_id FK, periodo_mes Int CHECK 1..12, periodo_anio Int CHECK >= 2000, rol VARCHAR(30), comisiones JSONB, base_monto, plus_monto, total_monto Numeric(12,2), desglose JSONB NULL, es_nexo Bool default false, excluido_por_factura Bool default false, estado VARCHAR(20) default 'Abierta' CHECK IN ('Abierta','Cerrada'), cerrada_at DateTime(tz) NULL)
- [x] 1.5 Índices de `liquidacion`: unique partial `uq_liquidacion_combo (tenant_id, usuario_id, cohorte_id, periodo_anio, periodo_mes) WHERE deleted_at IS NULL`; `ix_liquidacion_periodo (tenant_id, cohorte_id, periodo_anio, periodo_mes)`
- [x] 1.6 Tabla `factura` (BaseTenantModel + usuario_id FK, periodo_mes/periodo_anio Int CHECK, detalle Text, referencia_archivo Text NULL, tamano_kb Numeric(12,2) NULL, monto Numeric(12,2) CHECK >= 0, estado VARCHAR(20) default 'Pendiente' CHECK IN ('Pendiente','Abonada'), abonada_at DateTime(tz) NULL); índice `ix_factura_tenant_usuario_periodo`
- [x] 1.7 `op.add_column("materias", clave_plus VARCHAR(50) NULL)`
- [x] 1.8 Seed RBAC (patrón `ON CONFLICT DO NOTHING` por tenant): permisos `liquidaciones:ver`, `liquidaciones:calcular`, `liquidaciones:cerrar`, `liquidaciones:configurar-salarios`, `facturas:gestionar` → rol FINANZAS (global). Registrar `LIQUIDACION_CERRAR` en el catálogo de acciones de auditoría
- [x] 1.9 `downgrade()` simétrico (drop indexes, drop tables, drop column `materias.clave_plus`)

## 2. Modelos

- [x] 2.1 `backend/app/models/salario_base.py` — `SalarioBase(BaseTenantModel)`
- [x] 2.2 `backend/app/models/salario_plus.py` — `SalarioPlus(BaseTenantModel)`
- [x] 2.3 `backend/app/models/liquidacion.py` — `Liquidacion(BaseTenantModel)`
- [x] 2.4 `backend/app/models/factura.py` — `Factura(BaseTenantModel)`
- [x] 2.5 Agregar `clave_plus: Mapped[str | None]` a `backend/app/models/materia.py`
- [x] 2.6 Registrar los nuevos modelos en `backend/app/models/__init__.py`

## 3. Repositories (tenant-scoped, vigencia-aware)

- [x] 3.1 `salario_base_repository.py` — `get_vigente(rol, ref_date)`, `listar()`, `existe_solapamiento(rol, desde, hasta, excluir_id=None)`
- [x] 3.2 `salario_plus_repository.py` — `get_vigente(clave, rol, ref_date)`, `listar()`, `existe_solapamiento(clave, rol, desde, hasta, excluir_id=None)`
- [x] 3.3 `liquidacion_repository.py` — `listar_periodo(cohorte_id, mes, anio)`, `get_combo(usuario_id, cohorte_id, mes, anio)`, `listar_cerradas()` (historial), `upsert_calculo(...)`
- [x] 3.4 `factura_repository.py` — `listar(filtros: usuario_id?, estado?, periodo?)`, `get_by_id`, `sumar_periodo(cohorte_id?, mes, anio)`
- [x] 3.5 Helper de conteo: `contar_comisiones_por_clave(usuario_id, cohorte_id, ref_date)` — desde `Asignacion` activas join `Materia.clave_plus`, agrupado por clave (puede vivir en `asignacion_repository` o `liquidacion_repository`)

## 4. Schemas (Pydantic v2, `extra='forbid'`)

- [x] 4.1 `schemas/salario_base.py` — Create/Update/Read
- [x] 4.2 `schemas/salario_plus.py` — Create/Update/Read
- [x] 4.3 `schemas/liquidacion.py` — `CalcularRequest`, `CerrarRequest`, `LiquidacionRead` (con `desglose`), `PeriodoView` (segmentos general/nexo/factura + KPIs `total_sin_factura`/`total_con_factura`)
- [x] 4.4 `schemas/factura.py` — Create/Update/Read, `CambiarEstadoRequest`

## 5. Services (núcleo: motor de cálculo)

- [x] 5.1 `GrillaSalarialService` — ABM Base/Plus con validación de no-solapamiento de vigencias (RN-31)
- [x] 5.2 `liquidacion_calculo.py` — función pura de cálculo: `calcular_liquidacion(rol, base_vigente, plus_vigentes, comisiones_por_clave) -> (base, plus, total, desglose)` (RN-33/34) — sin I/O, testeable en aislamiento
- [x] 5.3 `LiquidacionService.calcular_periodo(cohorte_id, mes, anio)` — orquesta repos + motor, marca `es_nexo` y `excluido_por_factura`, hace upsert idempotente del período abierto
- [x] 5.4 `LiquidacionService.vista_periodo(...)` — segmentación general/NEXO/factura + KPIs (RN-36/38)
- [x] 5.5 `LiquidacionService.cerrar_periodo(cohorte_id, mes, anio)` — valida completitud + datos bancarios (RN-26), setea `estado='Cerrada'` + `cerrada_at`, emite `AuditLog` `LIQUIDACION_CERRAR`; guard de inmutabilidad en toda escritura (RN-22)
- [x] 5.6 `LiquidacionService.historial(...)` — liquidaciones cerradas, tenant-scoped
- [x] 5.7 `FacturaService` — ABM + `cambiar_estado` (Pendiente↔Abonada, setea `abonada_at`) (RN-39)

## 6. Routers (sin lógica de negocio; guards FINANZAS fail-closed)

- [x] 6.1 `api/v1/routers/liquidaciones.py` — POST `/calcular` (`liquidaciones:calcular`), GET `/periodo` y `/{id}` y `/historial` (`liquidaciones:ver`), POST `/cerrar` (`liquidaciones:cerrar`)
- [x] 6.2 `api/v1/routers/liquidaciones.py` (grilla) o router dedicado — ABM `/grilla/base/*` y `/grilla/plus/*` (`liquidaciones:configurar-salarios`)
- [x] 6.3 `api/v1/routers/facturas.py` — ABM `/api/facturas/*` + cambio de estado (`facturas:gestionar`)
- [x] 6.4 Registrar routers en `backend/app/main.py`
- [x] 6.5 Mapear `DomainError`/`ValueError` de servicio → 409 (inmutabilidad/solapamiento) / 422 (validación)

## 7. Tests (sin mocks de DB; ≥90% en reglas de negocio)

- [x] 7.1 `get_vigente` base: selecciona la fila vigente al mes; sin fila → None; borde `hasta` inclusivo
- [x] 7.2 `get_vigente` plus: idem para `(clave, rol)`
- [x] 7.3 No-solapamiento: crear base/plus con rango solapado → 409
- [x] 7.4 Motor: total = base + plus con 1 comisión (happy path)
- [x] 7.5 Motor: N comisiones de la misma clave acumulan N veces, sin tope (RN-33) — triangular con N=1,3
- [x] 7.6 Motor: comisiones de claves distintas suman cada plus por separado
- [x] 7.7 Motor: materia con `clave_plus` nulo no aporta plus
- [x] 7.8 Motor: cambio de grilla a mitad de año usa la vigente al mes (RN-31)
- [x] 7.9 NEXO: `es_nexo = true` y suma a `total_sin_factura` (RN-36)
- [x] 7.10 Facturante: `excluido_por_factura = true` y no suma al total general (RN-35)
- [x] 7.11 Unidad (cohorte, mes): dos cohortes generan liquidaciones independientes (RN-37); recalcular período abierto no duplica filas vivas
- [x] 7.12 Cierre: período pasa a Cerrada + `cerrada_at`; editar/recalcular cerrada → 409 (RN-22)
- [x] 7.13 Cierre emite `AuditLog` `LIQUIDACION_CERRAR` con `actor_id` del JWT y `filas_afectadas` = N
- [x] 7.14 Segmentación + KPIs: `total_sin_factura` (general+NEXO) vs `total_con_factura` (RN-38)
- [x] 7.15 Factura: dos estados Pendiente/Abonada; abonar setea `abonada_at`; estado inválido → 422 (RN-39)
- [x] 7.16 Guards: cada permiso `liquidaciones:*` / `facturas:gestionar` ausente → 403; aislamiento por tenant en listados
- [x] 7.17 Materia: PATCH `clave_plus`; clave libre aceptada sin catálogo global
