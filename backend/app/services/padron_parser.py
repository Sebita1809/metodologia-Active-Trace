"""
app/services/padron_parser.py — Pure file parser for padron uploads.

Stateless helper: parses .csv (stdlib) and .xlsx (openpyxl) files
into normalized _FilaRaw rows + ErrorParseo errors.

PII rule: errors NEVER include the email value — only row/column position.

Implemented: C-09 (padron-ingesta-moodle)
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from app.schemas.padron import ErrorParseo

# Required column names (case-insensitive, stripped)
_REQUIRED_COLUMNS = {"nombre", "apellidos", "email"}
_OPTIONAL_COLUMNS = {"comision", "regional"}


@dataclass
class _FilaRaw:
    """Intermediate representation of a parsed file row (before PII handling)."""
    fila: int
    nombre: str
    apellidos: str
    email: str
    comision: str | None
    regional: str | None


def _normalize_headers(headers: list[str]) -> dict[str, str]:
    """Return a mapping {normalized_lower_stripped -> original} for file headers."""
    return {h.strip().lower(): h for h in headers}


def parsear_archivo(
    data: bytes,
    content_type: str,
) -> tuple[list[_FilaRaw], list[ErrorParseo]]:
    """Parse a CSV or XLSX file into rows + errors.

    PII rule: errors NEVER include the email value — only row/column position.

    Parameters:
        data         — raw file bytes
        content_type — MIME type

    Returns:
        (list[_FilaRaw], list[ErrorParseo])
    """
    ct = content_type.lower().split(";")[0].strip()

    if ct in ("text/csv", "application/csv", "text/plain"):
        return _parsear_csv(data)
    elif ct in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/octet-stream",
    ):
        return _parsear_xlsx(data)
    else:
        return [], [ErrorParseo(fila=0, columna=None, mensaje=f"Tipo de archivo no soportado: {ct!r}")]


def _parsear_csv(data: bytes) -> tuple[list[_FilaRaw], list[ErrorParseo]]:
    """Parse CSV bytes into rows + errors."""
    entradas: list[_FilaRaw] = []
    errores: list[ErrorParseo] = []

    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = data.decode("latin-1")
        except Exception as exc:
            return [], [ErrorParseo(fila=0, columna=None, mensaje=f"No se pudo decodificar el archivo: {exc}")]

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return [], [ErrorParseo(fila=0, columna=None, mensaje="El archivo CSV no tiene encabezados")]

    header_map = _normalize_headers(list(reader.fieldnames))
    missing = _REQUIRED_COLUMNS - set(header_map.keys())
    if missing:
        return [], [ErrorParseo(
            fila=0,
            columna=None,
            mensaje=f"Columnas requeridas faltantes: {sorted(missing)}",
        )]

    for fila_num, row in enumerate(reader, start=2):
        result, error = _parse_row(fila_num, row, header_map)
        if error:
            errores.append(error)
        elif result:
            entradas.append(result)

    return entradas, errores


def _parsear_xlsx(data: bytes) -> tuple[list[_FilaRaw], list[ErrorParseo]]:
    """Parse XLSX bytes into rows + errors using openpyxl (read-only mode)."""
    try:
        import openpyxl  # noqa: PLC0415
    except ImportError:
        return [], [ErrorParseo(fila=0, columna=None, mensaje="openpyxl no instalado")]

    entradas: list[_FilaRaw] = []
    errores: list[ErrorParseo] = []

    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.active
        if ws is None:
            return [], [ErrorParseo(fila=0, columna=None, mensaje="Archivo XLSX sin hoja activa")]

        rows = list(ws.iter_rows(values_only=True))
    except Exception as exc:
        return [], [ErrorParseo(fila=0, columna=None, mensaje=f"Error al leer el archivo XLSX: {exc}")]

    if not rows:
        return [], [ErrorParseo(fila=0, columna=None, mensaje="El archivo XLSX está vacío")]

    raw_headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    header_map = _normalize_headers(raw_headers)

    missing = _REQUIRED_COLUMNS - set(header_map.keys())
    if missing:
        return [], [ErrorParseo(
            fila=1,
            columna=None,
            mensaje=f"Columnas requeridas faltantes: {sorted(missing)}",
        )]

    for fila_num, raw_row in enumerate(rows[1:], start=2):
        row = {raw_headers[i]: (str(v).strip() if v is not None else "") for i, v in enumerate(raw_row)}
        result, error = _parse_row(fila_num, row, header_map)
        if error:
            errores.append(error)
        elif result:
            entradas.append(result)

    return entradas, errores


def _parse_row(
    fila_num: int,
    row: dict[str, str],
    header_map: dict[str, str],
) -> tuple[_FilaRaw | None, ErrorParseo | None]:
    """Validate and normalize one row.

    PII rule: if email is invalid, the error message does NOT echo the value.
    """
    def _get(col_norm: str) -> str:
        orig = header_map.get(col_norm, col_norm)
        return str(row.get(orig, "") or "").strip()

    nombre = _get("nombre")
    apellidos = _get("apellidos")
    email_raw = _get("email")
    comision = _get("comision") or None
    regional = _get("regional") or None

    if not nombre:
        return None, ErrorParseo(fila=fila_num, columna="nombre", mensaje="Nombre vacío")
    if not apellidos:
        return None, ErrorParseo(fila=fila_num, columna="apellidos", mensaje="Apellidos vacío")
    if not email_raw:
        return None, ErrorParseo(fila=fila_num, columna="email", mensaje="Email vacío")

    email_normalized = email_raw.lower()
    if "@" not in email_normalized:
        return None, ErrorParseo(
            fila=fila_num,
            columna="email",
            mensaje="Formato de email inválido en fila",  # no PII echoed
        )

    return (
        _FilaRaw(
            fila=fila_num,
            nombre=nombre,
            apellidos=apellidos,
            email=email_normalized,
            comision=comision,
            regional=regional,
        ),
        None,
    )
