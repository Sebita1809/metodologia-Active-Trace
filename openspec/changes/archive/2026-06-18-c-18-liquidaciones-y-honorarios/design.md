# Design — C-18 Liquidaciones y Honorarios

> Governance: **CRÍTICO**. Toca dinero, el cierre es irreversible, debe ser auditable. Este documento es la base de revisión humana ANTES de implementar.

## 1. Contexto y decisiones cerradas

- **PA-22 (cerrada)**: las claves de Plus son strings libres configurables por tenant (no enum global). `Materia` gana el campo `clave_plus VARCHAR NULL`. Materias sin `clave_plus` no generan Plus.
- **PA-23 (cerrada)**: el Plus acumula N veces para N comisiones de la misma clave. Sin tope. Misma lógica para todos los roles. NEXO usa el flag `es_nexo` en `Liquidacion`, no una lógica de Plus distinta.
- **Alineación de nomenclatura con la KB**: la KB §E18 usa `grupo`/`descripcion` y §E19 usa `periodo` (texto AAAA-MM). Las decisiones cerradas (PA-22/23, RN-33/34) hablan de **`clave`** y el resumen del change pide `periodo_mes`/`periodo_anio`. Para este change se adopta la nomenclatura de las decisiones cerradas: `SalarioPlus.clave` (no `grupo`) y `Liquidacion.periodo_mes` + `periodo_anio` (enteros, más fáciles de filtrar e indexar que un texto). Es una diferencia deliberada respecto del wording literal de la KB, no una contradicción de fondo.

## 2. Modelo de datos

Todas las tablas extienden `BaseTenantModel` (id UUID, tenant_id, created_at, updated_at, deleted_at). Todos los montos son `Numeric(12, 2)`. Soft delete siempre. FKs `ondelete="RESTRICT"`.

### SalarioBase — tabla `salario_base`
| Columna | Tipo | Notas |
|---------|------|-------|
| rol | VARCHAR(30) | PROFESOR \| TUTOR \| NEXO \| COORDINADOR \| ALL |
| monto | Numeric(12,2) | >= 0 (CHECK) |
| desde | Date NOT NULL | inicio de vigencia |
| hasta | Date NULL | nulo = vigente sin límite |

Índice: `ix_salario_base_tenant_rol (tenant_id, rol)`. No hay unique sobre `(tenant_id, rol)` porque conviven versiones históricas con distinta vigencia; la regla "una sola vigente por rol en un instante" (RN-31) se valida a nivel servicio al crear/editar (sin solapamiento de rangos para el mismo rol).

### SalarioPlus — tabla `salario_plus`
| Columna | Tipo | Notas |
|---------|------|-------|
| clave | VARCHAR(50) | string libre por tenant (PA-22), matchea `Materia.clave_plus` |
| rol | VARCHAR(30) | PROFESOR \| TUTOR \| NEXO \| COORDINADOR |
| descripcion | Text NULL | descripción legible |
| monto | Numeric(12,2) | >= 0 (CHECK) |
| desde | Date NOT NULL | |
| hasta | Date NULL | |

Índice: `ix_salario_plus_tenant_clave_rol (tenant_id, clave, rol)`. Misma estrategia de no-solapamiento por `(clave, rol)` validada en servicio.

### Liquidacion — tabla `liquidacion`
| Columna | Tipo | Notas |
|---------|------|-------|
| usuario_id | UUID FK usuarios | docente liquidado |
| cohorte_id | UUID FK cohortes | |
| periodo_mes | Integer | 1..12 (CHECK) |
| periodo_anio | Integer | >= 2000 (CHECK) |
| rol | VARCHAR(30) | rol bajo el cual se liquida |
| comisiones | JSONB | comisiones que dieron lugar al cálculo (snapshot) |
| base_monto | Numeric(12,2) | de SalarioBase vigente |
| plus_monto | Numeric(12,2) | suma de Plus aplicables |
| total_monto | Numeric(12,2) | base_monto + plus_monto |
| desglose | JSONB NULL | breakdown auditable: por clave {clave, n_comisiones, monto_unitario, subtotal} |
| es_nexo | Boolean default false | RN-36: visibilizado aparte, suma al total |
| excluido_por_factura | Boolean default false | RN-35: facturante, no se paga por este canal |
| estado | VARCHAR(20) default 'Abierta' | Abierta \| Cerrada (CHECK) |
| cerrada_at | DateTime(tz) NULL | sello de cierre |

Unique partial index `uq_liquidacion_combo (tenant_id, usuario_id, cohorte_id, periodo_anio, periodo_mes) WHERE deleted_at IS NULL` — una liquidación viva por docente × cohorte × mes. Índice `ix_liquidacion_periodo (tenant_id, cohorte_id, periodo_anio, periodo_mes)` para la vista del período.

### Factura — tabla `factura`
| Columna | Tipo | Notas |
|---------|------|-------|
| usuario_id | UUID FK usuarios | docente facturador |
| periodo_mes / periodo_anio | Integer | mismo CHECK que liquidacion |
| detalle | Text | descripción libre del servicio |
| referencia_archivo | Text NULL | puntero opaco al storage |
| tamano_kb | Numeric(12,2) NULL | |
| monto | Numeric(12,2) | >= 0 (CHECK) |
| estado | VARCHAR(20) default 'Pendiente' | Pendiente \| Abonada (CHECK) |
| abonada_at | DateTime(tz) NULL | sello de pago |

Índice `ix_factura_tenant_usuario_periodo (tenant_id, usuario_id, periodo_anio, periodo_mes)`.

### Modificación de Materia
Se agrega `clave_plus VARCHAR(50) NULL`. Mapea la materia a una clave de categoría de Plus. NULL = no aporta Plus.

## 3. Selección de valor vigente (RN-31)

Una fila de grilla es vigente para un mes M (representado por su primer día, `date(anio, mes, 1)`) si:

```
desde <= ref_date AND (hasta IS NULL OR hasta >= ref_date)
```

`ref_date` = primer día del mes liquidado. El repository expone `get_vigente(rol/clave, ref_date)` que retorna la fila vigente. Si hay más de una (no debería, por la validación de no-solapamiento), se toma la de `desde` más reciente como desempate determinista, pero se considera un estado de datos inválido a reportar.

## 4. Motor de cálculo (RN-34) — núcleo del change

Para un `(cohorte, mes, anio)` y cada docente con asignaciones activas en esa cohorte:

```
ref_date = date(anio, mes, 1)
base = SalarioBase.get_vigente(rol_docente, ref_date).monto          # RN-32
plus_total = 0
desglose = []
# agrupar comisiones activas del docente por clave_plus de su materia
for clave, n_comisiones in contar_comisiones_por_clave(docente, cohorte, ref_date):
    if clave is None:        # materia sin clave_plus → no aporta (RN-33/34)
        continue
    plus_fila = SalarioPlus.get_vigente(clave, rol_docente, ref_date)
    if plus_fila is None:
        continue
    subtotal = plus_fila.monto * n_comisiones                         # RN-33 acumula N veces, sin tope
    plus_total += subtotal
    desglose.append({clave, n_comisiones, plus_fila.monto, subtotal})
total = base + plus_total                                             # RN-34
```

- **`contar_comisiones_por_clave`**: recorre las `Asignacion` activas (vigencia cubre `ref_date`) del docente en esa cohorte, y por cada comisión de cada asignación incrementa el contador de la `clave_plus` de la materia de esa asignación. Una asignación con K comisiones de una materia de clave X aporta K al contador de X (RN-33: acumula N veces).
- **NEXO**: `es_nexo = True` cuando el rol bajo el que se liquida es NEXO. NEXO usa Base por rol NEXO; el flag solo cambia la presentación/segmentación (RN-36), no el cálculo.
- **Facturantes** (`Usuario.facturador = true`): se generan con `excluido_por_factura = True` y NO suman al total de liquidación general (RN-35). Se muestran informativamente.
- **Sin tope**: RN-33 explícitamente no acapa la acumulación. El `desglose` JSONB hace visible y auditable cómo se llegó al total, mitigando el riesgo de totales inesperadamente grandes.

## 5. Inmutabilidad del cierre (RN-22)

- `estado` arranca en `Abierta`. El cierre (`POST /api/liquidaciones/cerrar`) opera sobre todas las liquidaciones de un `(cohorte, mes, anio)`.
- **Guard de servicio**: toda escritura sobre una `Liquidacion` con `estado = 'Cerrada'` lanza `DomainError` → HTTP 409. No se permite editar, recalcular ni borrar una liquidación cerrada.
- El cierre setea `estado = 'Cerrada'` y `cerrada_at = now()` de forma atómica para el período completo.
- **Validación de completitud antes de cerrar**: el cierre verifica que el cálculo se haya ejecutado para el período (existen filas) y que ningún docente incluido carezca de datos bancarios requeridos (RN-26) — el cierre es irreversible, así que falla cerrado si el período está incompleto.
- Recalcular un período cerrado está prohibido; para corregir hay que operar fuera del sistema (decisión de negocio: el cierre es definitivo, RN-22).

## 6. Segmentación y KPIs (F10.6, RN-36/37/38)

La vista del período retorna tres segmentos: **general** (PROFESOR/TUTOR/COORDINADOR no facturantes), **NEXO** (aparte pero sumado al total general, RN-36) y **facturantes** (informativo, excluido del total, RN-35). KPIs de cabecera: `total_sin_factura` (general + NEXO) y `total_con_factura` (suma de facturas del período). La unidad es siempre `(cohorte, mes)` (RN-37); cohortes distintas son independientes.

## 7. Auditoría

Nuevo código de acción `LIQUIDACION_CERRAR` en el catálogo. Se emite un `AuditLog` al cerrar, con `detalle` JSON `{cohorte_id, periodo_mes, periodo_anio, n_liquidaciones, total_cerrado}` y `filas_afectadas` = cantidad de liquidaciones cerradas. El actor sale de la sesión (JWT), nunca del request.

## 8. Guards y RBAC

Todos los endpoints exigen rol FINANZAS vía permisos finos (fail-closed):

| Permiso | Uso |
|---------|-----|
| `liquidaciones:ver` | vista del período, detalle individual, historial, exportar |
| `liquidaciones:calcular` | disparar el cálculo del período |
| `liquidaciones:cerrar` | cierre inmutable |
| `liquidaciones:configurar-salarios` | ABM de grilla Base/Plus |
| `facturas:gestionar` | ABM de facturas y cambio de estado Pendiente↔Abonada |

La migración siembra estos permisos para el rol FINANZAS (patrón `ON CONFLICT DO NOTHING` por tenant, igual que `015`).

## 9. Estructura de capas

`Routers (liquidaciones.py, facturas.py) → Services (LiquidacionService, GrillaSalarialService, FacturaService) → Repositories (tenant-scoped, vigencia-aware) → Models`. Sin lógica de negocio en routers, sin acceso a DB desde services salvo vía repository. `extra='forbid'` en todos los schemas. Archivos ≤500 LOC (el motor de cálculo puede ir en un módulo `liquidacion_calculo.py` separado del service si crece).

## 10. Riesgos

- **Acumulación sin tope (RN-33)**: totales potencialmente grandes. Mitigado por el `desglose` JSONB visible en la vista de detalle.
- **Cierre irreversible (RN-22)**: validar completitud y datos bancarios antes de permitir el cierre; fail-closed.
- **Vigencia solapada en grilla**: validación de no-solapamiento al crear/editar Base y Plus para no tener dos filas vigentes simultáneas.
- **Materia sin `clave_plus`**: caso esperado, no error — simplemente no aporta Plus. Cubierto por test.
