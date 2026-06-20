"""
tests/test_comunicacion_estado.py — TDD tests for pure state-machine functions.

Group 3 tasks:
  3.1 — transicion_valida: all valid transitions return True, all invalid return False
  3.2 — render_plantilla: variable substitution, missing variable, multiple occurrences

All tests are pure unit tests — no DB required.

Implemented: C-12 (comunicaciones-cola-worker)
"""
from __future__ import annotations

import pytest

from app.models.comunicacion import EstadoComunicacion
from app.services.comunicacion_estado import render_plantilla, transicion_valida


# ---------------------------------------------------------------------------
# Task 3.1 — transicion_valida — VALID transitions
# ---------------------------------------------------------------------------

def test_pendiente_a_enviando_valida():
    """Pendiente → Enviando is a valid transition (worker takes the message)."""
    assert transicion_valida(EstadoComunicacion.Pendiente, EstadoComunicacion.Enviando) is True


def test_pendiente_a_cancelado_valida():
    """Pendiente → Cancelado is a valid transition (manual cancellation)."""
    assert transicion_valida(EstadoComunicacion.Pendiente, EstadoComunicacion.Cancelado) is True


def test_enviando_a_enviado_valida():
    """Enviando → Enviado is a valid transition (channel confirms OK)."""
    assert transicion_valida(EstadoComunicacion.Enviando, EstadoComunicacion.Enviado) is True


def test_enviando_a_error_valida():
    """Enviando → Error is a valid transition (channel fails)."""
    assert transicion_valida(EstadoComunicacion.Enviando, EstadoComunicacion.Error) is True


# ---------------------------------------------------------------------------
# Task 3.1 — transicion_valida — INVALID transitions (TRIANGULATE)
# ---------------------------------------------------------------------------

def test_enviado_a_pendiente_invalida():
    """Enviado → Pendiente is invalid."""
    assert transicion_valida(EstadoComunicacion.Enviado, EstadoComunicacion.Pendiente) is False


def test_enviando_a_cancelado_invalida():
    """Enviando → Cancelado is invalid (only Pendiente can be cancelled)."""
    assert transicion_valida(EstadoComunicacion.Enviando, EstadoComunicacion.Cancelado) is False


def test_cancelado_a_enviando_invalida():
    """Cancelado → Enviando is invalid (cancelled is terminal)."""
    assert transicion_valida(EstadoComunicacion.Cancelado, EstadoComunicacion.Enviando) is False


def test_error_a_enviando_invalida():
    """Error → Enviando is invalid (Error is terminal for this version)."""
    assert transicion_valida(EstadoComunicacion.Error, EstadoComunicacion.Enviando) is False


def test_pendiente_a_enviado_invalida():
    """Pendiente → Enviado is invalid (must go through Enviando)."""
    assert transicion_valida(EstadoComunicacion.Pendiente, EstadoComunicacion.Enviado) is False


def test_pendiente_a_pendiente_invalida():
    """Pendiente → Pendiente is invalid (self-transition)."""
    assert transicion_valida(EstadoComunicacion.Pendiente, EstadoComunicacion.Pendiente) is False


def test_enviado_a_error_invalida():
    """Enviado → Error is invalid (Enviado is terminal)."""
    assert transicion_valida(EstadoComunicacion.Enviado, EstadoComunicacion.Error) is False


def test_cancelado_a_cancelado_invalida():
    """Cancelado → Cancelado is invalid (self-transition on terminal state)."""
    assert transicion_valida(EstadoComunicacion.Cancelado, EstadoComunicacion.Cancelado) is False


def test_transicion_valida_acepta_strings():
    """transicion_valida accepts plain string values (DB-fetched states)."""
    assert transicion_valida("Pendiente", "Enviando") is True
    assert transicion_valida("Enviando", "Enviado") is True
    assert transicion_valida("Enviado", "Pendiente") is False


def test_transicion_valida_string_invalido():
    """transicion_valida returns False for invalid state strings."""
    assert transicion_valida("NoExiste", "Enviando") is False
    assert transicion_valida("Pendiente", "EstadoInventado") is False


# ---------------------------------------------------------------------------
# Task 3.2 — render_plantilla — happy path
# ---------------------------------------------------------------------------

def test_render_variable_simple():
    """{{nombre_alumno}} is replaced with the variable value."""
    result = render_plantilla("Hola {{nombre_alumno}}", {"nombre_alumno": "Ana"})
    assert result == "Hola Ana"


def test_render_multiples_variables():
    """Multiple different variables are all replaced."""
    result = render_plantilla(
        "Estimado {{nombre}}, tu nota en {{materia}} es {{nota}}.",
        {"nombre": "Carlos", "materia": "Prog II", "nota": "8.5"},
    )
    assert result == "Estimado Carlos, tu nota en Prog II es 8.5."


def test_render_multiples_ocurrencias():
    """Multiple occurrences of the same token are all replaced."""
    result = render_plantilla(
        "{{nombre}} / {{nombre}}",
        {"nombre": "Ana"},
    )
    assert result == "Ana / Ana"


# ---------------------------------------------------------------------------
# Task 3.2 — render_plantilla — TRIANGULATE: missing variable / edge cases
# ---------------------------------------------------------------------------

def test_render_variable_ausente_queda_literal():
    """A token without a matching variable key is left as-is."""
    result = render_plantilla("Hola {{desconocido}}", {})
    assert result == "Hola {{desconocido}}"


def test_render_sin_variables():
    """Plantilla without any variables passes through unchanged."""
    plantilla = "Sin tokens aquí."
    result = render_plantilla(plantilla, {})
    assert result == plantilla


def test_render_variables_vacias():
    """When variables dict is empty, tokens are left literal."""
    result = render_plantilla("{{a}} y {{b}}", {})
    assert result == "{{a}} y {{b}}"


def test_render_plantilla_vacia():
    """Empty plantilla returns empty string regardless of variables."""
    result = render_plantilla("", {"nombre": "X"})
    assert result == ""


def test_render_token_parcialmente_presente():
    """A token present in variables is replaced; absent token stays literal."""
    result = render_plantilla("{{presente}} y {{ausente}}", {"presente": "OK"})
    assert result == "OK y {{ausente}}"
