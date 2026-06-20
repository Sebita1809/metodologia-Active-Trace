# Propuesta — C-18 Liquidaciones y Honorarios

## Why

El equipo de FINANZAS necesita calcular y cerrar la remuneración mensual de los docentes de cada cohorte sin planillas manuales. El dominio define una remuneración en dos partes (Base por rol + Plus por categoría de materia y comisión, RN-21) versionada en el tiempo (RN-31), una unidad de liquidación por `(cohorte, mes)` (RN-37), un cierre inmutable e irreversible (RN-22) y un flujo contable separado para los docentes que facturan (RN-35). Sin este módulo no existe forma trazable, auditable ni multi-tenant de liquidar honorarios.

Este es el último change del camino crítico funcional del producto financiero. Es de governance **CRÍTICO**: toca dinero, es irreversible al cerrar y debe ser auditable.

## What Changes

- Se agregan cuatro entidades nuevas: `SalarioBase`, `SalarioPlus`, `Liquidacion`, `Factura` (modelo de datos §E17–E20), con su migración Alembic (`016`).
- Se incorpora el **motor de cálculo de liquidación** del período (FL-08, RN-34): selección de Base vigente por rol+mes, agrupación de comisiones activas por `clave_plus` de su materia, multiplicación por el Plus vigente de `(clave, rol, mes)` y acumulación N veces sin tope (RN-33).
- Se incorpora el **ABM de grilla salarial** (Base y Plus) con vigencia temporal abierta (F10.4, RN-31/32/33).
- Se incorpora la **gestión de facturas** de docentes facturantes (F10.5, RN-35/39/40), excluidos de la liquidación general.
- Se incorpora el **cierre inmutable** de liquidación por `(cohorte, mes)` (F10.2, RN-22) con emisión del evento de auditoría `LIQUIDACION_CERRAR`.
- Se incorpora la **segmentación contable** general / NEXO / facturantes y KPIs "Total sin factura" / "Total con factura" (F10.6, RN-36/37/38).
- Se exponen `/api/liquidaciones/*` y `/api/facturas/*` protegidos por guards `liquidaciones:*` (rol FINANZAS).
- Se agrega el campo `clave_plus` (nullable) a `Materia`: el mapeo materia → clave de categoría de Plus (PA-33). Materias sin `clave_plus` no generan Plus.

## Capabilities

### New Capabilities

- **`salario-base`** — grilla de bases salariales por rol con vigencia temporal abierta; selección del valor vigente para un mes.
- **`salario-plus`** — grilla de plus por `(clave, rol)` con vigencia temporal abierta; selección del valor vigente para un mes.
- **`liquidacion`** — motor de cálculo Base+Plus por `(cohorte, mes)`, vista de detalle, segmentación general/NEXO/factura, cierre inmutable, historial y KPIs.
- **`factura`** — ABM de comprobantes de docentes facturantes con estados Pendiente/Abonada (flujo de pago separado de la liquidación general).

### Modified Capabilities

- **`materia`** — se agrega el atributo `clave_plus` (string libre, nullable) que mapea la materia a una clave de categoría de Plus. Materias sin `clave_plus` no aportan Plus al cálculo de liquidación.

## Impact

- **Migración**: `016_liquidaciones_honorarios.py` — crea `salario_base`, `salario_plus`, `liquidacion`, `factura`; agrega columna `clave_plus` a `materias`; siembra los permisos `liquidaciones:*` y `facturas:*` para el rol FINANZAS.
- **Modelos**: `SalarioBase`, `SalarioPlus`, `Liquidacion`, `Factura`; modificación de `Materia`.
- **Repositories**: cuatro repositories nuevos, todos tenant-scoped, con consultas conscientes de vigencia (`desde <= mes <= hasta` con `hasta` nullable).
- **Services**: `LiquidacionService` (motor de cálculo + cierre + segmentación), `GrillaSalarialService` (ABM Base/Plus), `FacturaService` (ABM facturas).
- **Routers**: `liquidaciones.py`, `facturas.py`, ABM de grilla bajo `/api/liquidaciones/grilla/*`.
- **Auditoría**: nuevo código de acción `LIQUIDACION_CERRAR` emitido al cerrar.
- **Dependencias**: requiere C-07 (Usuario, Asignacion, Cohorte) ya implementado. Cierra las preguntas abiertas PA-22 y PA-23.
- **Governance**: CRÍTICO — afecta dinero y el cierre es irreversible. Las decisiones de modelo y motor de cálculo se documentan en `design.md` para revisión humana antes de implementar.
