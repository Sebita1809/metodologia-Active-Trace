"""
tests/test_padron_parser.py — TDD tests for the padrón file parser (tasks 3.1-3.3).

These are pure unit tests (no DB, no HTTP) — the parser helper is stateless.

Tests:
  3.1 — parsing valid CSV returns N normalized entries
  3.2 — parsing valid XLSX returns the same entries as the CSV equivalent
  3.3 — file with missing columns returns errors and NO entries;
         errors must NOT contain email in plain text
"""
from __future__ import annotations

import csv
import io

import pytest

from app.services.padron_parser import parsear_archivo as _parsear_archivo, _REQUIRED_COLUMNS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_csv(rows: list[dict]) -> bytes:
    """Build a UTF-8 CSV from a list of dicts."""
    output = io.StringIO()
    fieldnames = ["nombre", "apellidos", "email", "comision", "regional"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def _build_xlsx(rows: list[dict]) -> bytes:
    """Build an XLSX file from a list of dicts using openpyxl."""
    import openpyxl  # noqa: PLC0415
    wb = openpyxl.Workbook()
    ws = wb.active
    headers = ["nombre", "apellidos", "email", "comision", "regional"]
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h, "") for h in headers])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


SAMPLE_ROWS = [
    {"nombre": "Ana",   "apellidos": "Garcia",   "email": "ana@test.com",   "comision": "A1", "regional": "Norte"},
    {"nombre": "Bruno", "apellidos": "Lopez",     "email": "bruno@test.com", "comision": "B2", "regional": "Sur"},
    {"nombre": "Clara", "apellidos": "Martinez",  "email": "clara@test.com", "comision": "",   "regional": ""},
]


# ---------------------------------------------------------------------------
# Task 3.1 — CSV parser
# ---------------------------------------------------------------------------

def test_parsear_csv_valido_devuelve_entradas():
    """Parsing a valid CSV returns normalized entries with all required fields."""
    data = _build_csv(SAMPLE_ROWS)
    entradas, errores = _parsear_archivo(data, "text/csv")

    assert errores == [], f"Expected no errors, got: {errores}"
    assert len(entradas) == 3

    # Check normalization
    emails = [e.email for e in entradas]
    assert "ana@test.com" in emails
    assert "bruno@test.com" in emails
    assert "clara@test.com" in emails

    # Check comision/regional
    ana = next(e for e in entradas if e.nombre == "Ana")
    assert ana.comision == "A1"
    assert ana.regional == "Norte"

    clara = next(e for e in entradas if e.nombre == "Clara")
    assert clara.comision is None
    assert clara.regional is None


def test_parsear_csv_email_normalizado_lowercase():
    """CSV parser normalizes email to lowercase."""
    rows = [{"nombre": "Ana", "apellidos": "Garcia", "email": "ANA@TEST.COM", "comision": "", "regional": ""}]
    data = _build_csv(rows)
    entradas, errores = _parsear_archivo(data, "text/csv")

    assert len(entradas) == 1
    assert entradas[0].email == "ana@test.com"


# ---------------------------------------------------------------------------
# Task 3.2 — XLSX parser returns same entries as CSV equivalent
# ---------------------------------------------------------------------------

def test_parsear_xlsx_devuelve_mismas_entradas_que_csv():
    """XLSX parser returns the same entries as the CSV equivalent."""
    pytest.importorskip("openpyxl")

    csv_data = _build_csv(SAMPLE_ROWS)
    xlsx_data = _build_xlsx(SAMPLE_ROWS)

    csv_entradas, csv_errores = _parsear_archivo(csv_data, "text/csv")
    xlsx_entradas, xlsx_errores = _parsear_archivo(
        xlsx_data,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    assert csv_errores == []
    assert xlsx_errores == []

    assert len(csv_entradas) == len(xlsx_entradas)

    csv_emails = sorted(e.email for e in csv_entradas)
    xlsx_emails = sorted(e.email for e in xlsx_entradas)
    assert csv_emails == xlsx_emails

    csv_nombres = sorted(e.nombre for e in csv_entradas)
    xlsx_nombres = sorted(e.nombre for e in xlsx_entradas)
    assert csv_nombres == xlsx_nombres


# ---------------------------------------------------------------------------
# Task 3.3 — Invalid files return errors and NO entries; errors contain no PII
# ---------------------------------------------------------------------------

def test_parsear_csv_columnas_faltantes_devuelve_errores():
    """CSV with missing required columns returns errors and no entries."""
    # CSV without 'email' column
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["nombre", "apellidos"])
    writer.writeheader()
    writer.writerow({"nombre": "Ana", "apellidos": "Garcia"})
    data = output.getvalue().encode("utf-8")

    entradas, errores = _parsear_archivo(data, "text/csv")

    assert entradas == []
    assert len(errores) >= 1
    # Errors must not contain email values in plain text
    for error in errores:
        assert "ana@" not in error.mensaje.lower()
        assert "@test.com" not in error.mensaje.lower()


def test_parsear_csv_fila_con_email_invalido_devuelve_error():
    """Rows with invalid email format produce an error; the bad value is NOT echoed."""
    rows = [
        {"nombre": "Ana", "apellidos": "Garcia", "email": "notavalidemail", "comision": "", "regional": ""},
        {"nombre": "Bruno", "apellidos": "Lopez",  "email": "bruno@ok.com",   "comision": "", "regional": ""},
    ]
    data = _build_csv(rows)
    entradas, errores = _parsear_archivo(data, "text/csv")

    # Only the valid row is parsed
    assert len(entradas) == 1
    assert entradas[0].nombre == "Bruno"

    # The error row exists
    assert len(errores) == 1
    # The bad email value is NOT in the error message
    assert "notavalidemail" not in errores[0].mensaje


def test_parsear_csv_fila_con_nombre_vacio_devuelve_error():
    """Rows with empty nombre produce an error."""
    rows = [{"nombre": "", "apellidos": "Garcia", "email": "ok@test.com", "comision": "", "regional": ""}]
    data = _build_csv(rows)
    entradas, errores = _parsear_archivo(data, "text/csv")

    assert entradas == []
    assert len(errores) == 1
    assert errores[0].columna == "nombre"


def test_parsear_tipo_no_soportado_devuelve_error():
    """Unknown content type returns a single error."""
    entradas, errores = _parsear_archivo(b"data", "application/pdf")
    assert entradas == []
    assert len(errores) == 1
    assert "no soportado" in errores[0].mensaje.lower()


def test_parsear_xlsx_columnas_faltantes():
    """XLSX with missing required columns returns errors and no entries."""
    pytest.importorskip("openpyxl")
    import openpyxl  # noqa: PLC0415

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["nombre", "apellidos"])  # missing 'email'
    ws.append(["Ana", "Garcia"])
    buf = io.BytesIO()
    wb.save(buf)
    data = buf.getvalue()

    entradas, errores = _parsear_archivo(
        data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert entradas == []
    assert len(errores) >= 1
    # No PII in errors
    for error in errores:
        assert "@" not in error.mensaje
