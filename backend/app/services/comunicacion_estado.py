"""
app/services/comunicacion_estado.py — Pure state-machine functions for Comunicacion.

This module contains ONLY pure functions — no DB, no side effects.
It implements the state transitions defined in RN-15 and design D-01.

Valid transitions (RN-15):
    Pendiente  → Enviando   (worker picks the message)
    Pendiente  → Cancelado  (manual cancellation)
    Enviando   → Enviado    (channel confirms OK)
    Enviando   → Error      (channel fails)

All other transitions are INVALID and transicion_valida() returns False.

Template rendering (D-05):
    render_plantilla(plantilla, variables) — replaces {{token}} with values.
    Missing variables are left as-is (literal token, never raises).

Implemented: C-12 (comunicaciones-cola-worker)
"""
from __future__ import annotations

import re

from app.models.comunicacion import EstadoComunicacion

# ---------------------------------------------------------------------------
# Transition table — single source of truth for RN-15
# ---------------------------------------------------------------------------

_TRANSICIONES_VALIDAS: frozenset[tuple[str, str]] = frozenset({
    (EstadoComunicacion.Pendiente,  EstadoComunicacion.Enviando),
    (EstadoComunicacion.Pendiente,  EstadoComunicacion.Cancelado),
    (EstadoComunicacion.Enviando,   EstadoComunicacion.Enviado),
    (EstadoComunicacion.Enviando,   EstadoComunicacion.Error),
})


# ---------------------------------------------------------------------------
# Task 3.1 — transicion_valida (pure function, no DB)
# ---------------------------------------------------------------------------

def transicion_valida(
    estado_actual: EstadoComunicacion | str,
    estado_destino: EstadoComunicacion | str,
) -> bool:
    """Return True if the transition from estado_actual to estado_destino is valid.

    Accepts both EstadoComunicacion enum values and plain strings (for
    convenience when working with DB-fetched string values).

    Parameters:
        estado_actual   — current state of the Comunicacion
        estado_destino  — target state to transition to

    Returns:
        True if the transition is valid (RN-15), False otherwise.
    """
    # Normalise to EstadoComunicacion to handle plain strings from DB
    try:
        actual = EstadoComunicacion(estado_actual) if isinstance(estado_actual, str) else estado_actual
        destino = EstadoComunicacion(estado_destino) if isinstance(estado_destino, str) else estado_destino
    except ValueError:
        return False

    return (actual, destino) in _TRANSICIONES_VALIDAS


# ---------------------------------------------------------------------------
# Task 3.2 — render_plantilla (pure function, no DB)
# ---------------------------------------------------------------------------

_TOKEN_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def render_plantilla(plantilla: str, variables: dict[str, str]) -> str:
    """Replace {{token}} placeholders in *plantilla* with values from *variables*.

    Behaviour:
      - A token that has a matching key in *variables* → replaced with its value.
      - A token with NO matching key → left as-is (literal {{token}}).
      - Multiple occurrences of the same token → all replaced.
      - Empty plantilla or empty variables → returns plantilla unchanged.

    Parameters:
        plantilla  — template string with {{token}} placeholders
        variables  — mapping from token name to replacement value

    Returns:
        The rendered string.

    Examples:
        >>> render_plantilla("Hola {{nombre_alumno}}", {"nombre_alumno": "Ana"})
        'Hola Ana'
        >>> render_plantilla("Hola {{desconocido}}", {})
        'Hola {{desconocido}}'
    """
    def _replace(match: re.Match) -> str:
        token = match.group(1)
        return variables.get(token, match.group(0))  # keep literal if missing

    return _TOKEN_PATTERN.sub(_replace, plantilla)
