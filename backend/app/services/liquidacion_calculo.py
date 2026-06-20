"""
app/services/liquidacion_calculo.py — Pure calculation engine for liquidaciones (C-18).

This module contains ONLY pure functions with NO I/O.
It is the core of the salary liquidation motor (RN-33, RN-34).

Function:
  calcular_liquidacion(rol, base_vigente, plus_vigentes, comisiones_por_clave)
    → (base_monto, plus_monto, total_monto, desglose)

Design (RN-34):
  total = base + Σ(plus(clave) × N_comisiones(clave))

  - base_vigente: Decimal | None — the vigent base salary for the rol.
    If None (no base configured) → base_monto = 0.
  - plus_vigentes: dict[clave, Decimal] — vigent plus amounts per clave.
    Only claves present in this dict will generate plus.
  - comisiones_por_clave: dict[clave, int] — N active comisiones per clave.
    Claves not in plus_vigentes contribute 0 (RN-33).

  The desglose is a list of dicts for full auditability:
    [{ "clave": ..., "n_comisiones": ..., "monto_unitario": ..., "monto_total": ... }]

TDD: This module can be unit-tested without a DB.
Strict TDD: all business rules enforced here are covered in test_liquidaciones.py.

Implemented: C-18 (liquidaciones-y-honorarios)
"""
from __future__ import annotations

from decimal import Decimal


def calcular_liquidacion(
    rol: str,  # noqa: ARG001 — available for future role-specific logic
    base_vigente: Decimal | None,
    plus_vigentes: dict[str, Decimal],
    comisiones_por_clave: dict[str, int],
) -> tuple[Decimal, Decimal, Decimal, dict]:
    """Calculate base, plus, total and desglose for one docente in one period.

    Parameters
    ----------
    rol:
        Role under which the docente is being liquidated.
        Kept for potential future role-specific overrides.
    base_vigente:
        The vigent SalarioBase.monto for this rol at the ref_date.
        None if no base is configured → base_monto = 0.
    plus_vigentes:
        Mapping of clave → vigent SalarioPlus.monto for this rol at ref_date.
        Only claves present here will contribute to plus.
    comisiones_por_clave:
        Mapping of clave → number of active comisiones the docente has for that clave.
        Claves with NULL clave_plus on the materia are excluded before calling this fn.

    Returns
    -------
    (base_monto, plus_monto, total_monto, desglose)
        base_monto  : Decimal
        plus_monto  : Decimal
        total_monto : Decimal (base + plus, RN-34)
        desglose    : dict with key "items" containing a list of per-clave breakdowns
    """
    # Base salary (RN-32): 0 if no base configured
    base_monto: Decimal = base_vigente if base_vigente is not None else Decimal("0")

    # Plus accumulation (RN-33): sum(monto_unitario × N_comisiones) per clave
    plus_monto: Decimal = Decimal("0")
    desglose_items: list[dict] = []

    for clave, n_comisiones in comisiones_por_clave.items():
        if clave not in plus_vigentes:
            # No vigent plus for this clave → contributes 0 (RN-33)
            continue
        monto_unitario = plus_vigentes[clave]
        monto_total = monto_unitario * n_comisiones  # accumulates N times, no cap (RN-33)
        plus_monto += monto_total
        desglose_items.append(
            {
                "clave": clave,
                "n_comisiones": n_comisiones,
                "monto_unitario": str(monto_unitario),
                "monto_total": str(monto_total),
            }
        )

    total_monto = base_monto + plus_monto  # RN-34

    desglose = {
        "rol": rol,
        "base_monto": str(base_monto),
        "items": desglose_items,
    }

    return base_monto, plus_monto, total_monto, desglose
