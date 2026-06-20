"""
app/services/audit_codes.py — Standardised action-code catalog for audit log.

The catalog is defined as a StrEnum so it can be used as a Python type while
serialising to plain strings in the database column (String, not a PG enum —
avoids migrations on catalog extension per D-05).

Implemented: C-05 (audit-log)
"""
from __future__ import annotations

from enum import StrEnum


class AccionAuditoria(StrEnum):
    """Standardised action codes for the audit_log.accion column.

    The helper AuditService.registrar() expects a value of this enum —
    raw strings are not accepted so the catalog is always enforced.

    Codes:
        CALIFICACIONES_IMPORTAR   — bulk grade import
        PADRON_CARGAR             — student roster load
        COMUNICACION_ENVIAR       — outgoing communication dispatched
        ASIGNACION_MODIFICAR      — teaching assignment changed
        LIQUIDACION_CERRAR        — payroll period closed
        IMPERSONACION_INICIAR     — impersonation session started
        IMPERSONACION_FINALIZAR   — impersonation session ended
    """

    CALIFICACIONES_IMPORTAR = "CALIFICACIONES_IMPORTAR"
    PADRON_CARGAR = "PADRON_CARGAR"
    COMUNICACION_ENVIAR = "COMUNICACION_ENVIAR"
    ASIGNACION_MODIFICAR = "ASIGNACION_MODIFICAR"
    LIQUIDACION_CERRAR = "LIQUIDACION_CERRAR"
    IMPERSONACION_INICIAR = "IMPERSONACION_INICIAR"
    IMPERSONACION_FINALIZAR = "IMPERSONACION_FINALIZAR"
