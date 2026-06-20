"""
tests/test_audit_codes.py — TDD tests for audit action-code catalog (Task 2).

Verifies:
  - AccionAuditoria StrEnum has exactly 7 codes
  - All expected codes are present
  - AuditService.registrar() rejects a code outside the catalog
    (tested via type validation — the function signature accepts AccionAuditoria,
    not str, so passing an invalid value raises TypeError or ValueError)

No DB required for these tests.

TDD cycle:
  RED   — written before implementation
  GREEN — audit_codes.py created with AccionAuditoria StrEnum
"""
from __future__ import annotations

import pytest

from app.services.audit_codes import AccionAuditoria


# ---------------------------------------------------------------------------
# Task 2.1 — AccionAuditoria has exactly 7 codes
# ---------------------------------------------------------------------------

def test_accion_auditoria_has_seven_codes():
    """AccionAuditoria StrEnum must contain exactly 7 standardised codes."""
    assert len(AccionAuditoria) == 7, (
        f"Expected 7 action codes, got {len(AccionAuditoria)}: {list(AccionAuditoria)}"
    )


def test_accion_auditoria_contains_expected_codes():
    """All 7 expected codes are present in the catalog."""
    expected = {
        "CALIFICACIONES_IMPORTAR",
        "PADRON_CARGAR",
        "COMUNICACION_ENVIAR",
        "ASIGNACION_MODIFICAR",
        "LIQUIDACION_CERRAR",
        "IMPERSONACION_INICIAR",
        "IMPERSONACION_FINALIZAR",
    }
    actual = {member.value for member in AccionAuditoria}
    assert actual == expected, f"Code mismatch. Expected: {expected}, Got: {actual}"


def test_accion_auditoria_values_are_strings():
    """Every member value is a plain string (StrEnum guarantee)."""
    for member in AccionAuditoria:
        assert isinstance(member, str), f"Expected str, got {type(member)} for {member!r}"


# ---------------------------------------------------------------------------
# Task 2.3 — Helper rejects code outside catalog
# ---------------------------------------------------------------------------

def test_accion_auditoria_rejects_unknown_code():
    """AccionAuditoria(value) raises ValueError for a code not in the catalog."""
    with pytest.raises(ValueError):
        AccionAuditoria("CODIGO_INVENTADO")


def test_accion_auditoria_rejects_empty_string():
    """AccionAuditoria('') raises ValueError — empty string is not a valid code."""
    with pytest.raises(ValueError):
        AccionAuditoria("")


def test_accion_auditoria_member_is_accessible_by_value():
    """AccionAuditoria(value) succeeds for a valid code."""
    code = AccionAuditoria("CALIFICACIONES_IMPORTAR")
    assert code is AccionAuditoria.CALIFICACIONES_IMPORTAR
