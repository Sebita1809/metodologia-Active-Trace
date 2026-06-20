"""
app/services/coloquio_helpers.py — Pure helper functions for evaluaciones/coloquios.

These are pure functions (no DB, no side effects) that implement the core
business rules for cupo/capacity calculations.

Business rules:
  RN-C01: hay_cupo → True if reservas_activas_en_fecha < cupo_por_dia
  RN-C02: cupos_libres → max(0, cupo_por_dia - reservas_activas)

Implemented: C-14 (evaluaciones-y-coloquios)
"""
from __future__ import annotations


def hay_cupo(reservas_activas_en_fecha: int, cupo_por_dia: int) -> bool:
    """Return True if there is capacity left for a new reservation on this date.

    Parameters
    ----------
    reservas_activas_en_fecha:
        Count of active (estado='Activa') reservations on the target date.
    cupo_por_dia:
        Maximum allowed reservations per calendar day.

    Returns
    -------
    bool
        True if reservas_activas_en_fecha < cupo_por_dia.
    """
    return reservas_activas_en_fecha < cupo_por_dia


def cupos_libres(cupo_por_dia: int, reservas_activas: int) -> int:
    """Return the number of remaining free slots for a given day.

    Parameters
    ----------
    cupo_por_dia:
        Maximum allowed reservations per calendar day.
    reservas_activas:
        Count of active reservations already made for that day.

    Returns
    -------
    int
        max(0, cupo_por_dia - reservas_activas)
    """
    return max(0, cupo_por_dia - reservas_activas)
