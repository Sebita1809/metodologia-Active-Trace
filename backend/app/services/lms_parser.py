"""
app/services/lms_parser.py — Pure file parser for LMS grade exports.

Stateless helper: parses .xlsx (openpyxl) and .csv (stdlib) grade files
from Moodle into normalized ParsedLmsGrades and FilaFinalizacion rows.

Detection rules:
  - Email column: any header matching "email" (case-insensitive)
  - Numeric columns: headers ending with "(Real)" (case-insensitive)
  - Textual columns: all other non-ID, non-empty headers
  - Finalization columns: looks for headers indicating completion (finalized/completado)

Raises ValueError with descriptive messages for invalid format.

Implemented: C-10 (calificaciones-y-umbral)
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field


@dataclass
class FilaCalificacion:
    """Intermediate representation of a single grade for a student on an activity."""

    email: str
    actividad: str
    nota_numerica: float | None  # None if textual activity
    nota_textual: str | None     # None if numeric activity


@dataclass
class ParsedLmsGrades:
    """Result of parsing an LMS grades export file."""

    actividades_numericas: list[str]  # column names ending with (Real)
    actividades_textuales: list[str]  # other non-ID columns
    filas: list[dict]  # list of {email: str, actividad: str, nota_numerica, nota_textual}

    # Convenience: set of all unique emails found in the file
    emails: list[str] = field(default_factory=list)


@dataclass
class FilaFinalizacion:
    """Intermediate representation of a single LMS finalization record."""

    alumno_email: str
    actividad: str
    finalizado: bool


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_lms_grades(file_bytes: bytes, filename: str) -> ParsedLmsGrades:
    """Parse an LMS grades export file and return structured grade data.

    Accepts .xlsx and .csv files.
    Detects email column (case-insensitive "email" match).
    Detects numeric columns (header ending in "(Real)" case-insensitive).
    All other non-ID, non-system columns are treated as textual.

    Raises ValueError for:
      - unsupported file format
      - missing email column
      - empty file

    Parameters:
        file_bytes — raw file bytes
        filename   — original filename (used to detect extension)
    """
    ext = _get_extension(filename)

    if ext == ".xlsx":
        headers, rows = _parse_xlsx_to_rows(file_bytes)
    elif ext == ".csv":
        headers, rows = _parse_csv_to_rows(file_bytes)
    else:
        raise ValueError(f"Formato de archivo no soportado: {filename!r}. Use .xlsx o .csv")

    if not headers:
        raise ValueError("El archivo no tiene encabezados")

    # Find email column (case-insensitive)
    email_col = _find_email_column(headers)
    if email_col is None:
        raise ValueError(
            f"Columna de email no encontrada. Encabezados detectados: {headers}"
        )

    # Classify activity columns
    actividades_numericas: list[str] = []
    actividades_textuales: list[str] = []

    # System/ID columns to skip (case-insensitive)
    _SKIP_PATTERNS = {"nombre", "apellido", "id", "nombre completo", "nombre del usuario"}

    for header in headers:
        if header == email_col:
            continue
        header_lower = header.strip().lower()
        if header_lower in _SKIP_PATTERNS:
            continue
        if header_lower.endswith("(real)"):
            actividades_numericas.append(header)
        else:
            # Only include as textual if it's not empty and not a system column
            if header.strip():
                actividades_textuales.append(header)

    # Build filas: one dict per (student, activity) pair
    filas: list[dict] = []
    emails_seen: set[str] = set()

    for row in rows:
        email_raw = str(row.get(email_col, "") or "").strip().lower()
        if not email_raw or "@" not in email_raw:
            continue

        emails_seen.add(email_raw)

        for actividad in actividades_numericas:
            val_raw = str(row.get(actividad, "") or "").strip()
            nota_num = _parse_numeric(val_raw)
            filas.append({
                "email": email_raw,
                "actividad": actividad,
                "nota_numerica": nota_num,
                "nota_textual": None,
            })

        for actividad in actividades_textuales:
            val_raw = str(row.get(actividad, "") or "").strip()
            nota_txt = val_raw if val_raw else None
            filas.append({
                "email": email_raw,
                "actividad": actividad,
                "nota_numerica": None,
                "nota_textual": nota_txt,
            })

    return ParsedLmsGrades(
        actividades_numericas=actividades_numericas,
        actividades_textuales=actividades_textuales,
        filas=filas,
        emails=list(emails_seen),
    )


def detect_activities(parsed: ParsedLmsGrades) -> dict:
    """Return a dict summarizing detected activity types.

    Returns:
        {"numericas": [...], "textuales": [...]}
    """
    return {
        "numericas": parsed.actividades_numericas,
        "textuales": parsed.actividades_textuales,
    }


def parse_finalizacion(file_bytes: bytes, filename: str) -> list[FilaFinalizacion]:
    """Parse an LMS finalization/completion report.

    Expects columns: email/student identifier, activity name, finalized/completed boolean.
    Column detection is flexible (case-insensitive).

    Raises ValueError for invalid format or missing required columns.

    Returns a list of FilaFinalizacion records.
    """
    ext = _get_extension(filename)

    if ext == ".xlsx":
        headers, rows = _parse_xlsx_to_rows(file_bytes)
    elif ext == ".csv":
        headers, rows = _parse_csv_to_rows(file_bytes)
    else:
        raise ValueError(f"Formato de archivo no soportado: {filename!r}. Use .xlsx o .csv")

    if not headers:
        raise ValueError("El archivo de finalización no tiene encabezados")

    email_col = _find_email_column(headers)
    if email_col is None:
        raise ValueError(
            f"Columna de email no encontrada en archivo de finalización. Encabezados: {headers}"
        )

    # Find activity and completion columns
    activity_col = _find_column(headers, {"actividad", "activity", "nombre actividad", "nombre de actividad"})
    completed_col = _find_column(
        headers,
        {"finalizado", "completado", "estado", "finalized", "completed", "completion"},
    )

    if activity_col is None:
        raise ValueError(
            f"Columna de actividad no encontrada. Encabezados: {headers}"
        )
    if completed_col is None:
        raise ValueError(
            f"Columna de finalización no encontrada. Encabezados: {headers}"
        )

    result: list[FilaFinalizacion] = []

    for row in rows:
        email_raw = str(row.get(email_col, "") or "").strip().lower()
        if not email_raw or "@" not in email_raw:
            continue

        actividad = str(row.get(activity_col, "") or "").strip()
        if not actividad:
            continue

        completed_raw = str(row.get(completed_col, "") or "").strip().lower()
        finalizado = completed_raw in ("true", "1", "sí", "si", "yes", "finalizado", "completado")

        result.append(FilaFinalizacion(
            alumno_email=email_raw,
            actividad=actividad,
            finalizado=finalizado,
        ))

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_extension(filename: str) -> str:
    """Return the lowercased file extension including the dot."""
    parts = filename.rsplit(".", 1)
    if len(parts) < 2:
        return ""
    return f".{parts[-1].lower()}"


def _find_email_column(headers: list[str]) -> str | None:
    """Find the email column among headers (case-insensitive exact match or contains 'email')."""
    for h in headers:
        if h.strip().lower() == "email":
            return h
    # Fallback: partial match
    for h in headers:
        if "email" in h.strip().lower():
            return h
    return None


def _find_column(headers: list[str], candidates: set[str]) -> str | None:
    """Find the first header that matches any of the candidate names (case-insensitive)."""
    for h in headers:
        if h.strip().lower() in candidates:
            return h
    return None


def _parse_numeric(value: str) -> float | None:
    """Try to parse a string as float; return None if blank or unparseable."""
    if not value or value.strip() in ("-", "N/A", "n/a", ""):
        return None
    try:
        return float(value.replace(",", "."))
    except (ValueError, AttributeError):
        return None


def _parse_csv_to_rows(data: bytes) -> tuple[list[str], list[dict]]:
    """Parse CSV bytes into (headers, rows).

    Tries utf-8-sig first, then latin-1.
    Returns (list_of_header_strings, list_of_dicts).
    """
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = data.decode("latin-1")
        except Exception as exc:
            raise ValueError(f"No se pudo decodificar el archivo CSV: {exc}") from exc

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return [], []

    headers = [str(h).strip() for h in reader.fieldnames if h is not None]
    rows = [dict(row) for row in reader]
    return headers, rows


def _parse_xlsx_to_rows(data: bytes) -> tuple[list[str], list[dict]]:
    """Parse XLSX bytes into (headers, rows) using openpyxl (read-only mode).

    Raises ValueError on format errors.
    """
    try:
        import openpyxl  # noqa: PLC0415
    except ImportError as exc:
        raise ValueError("openpyxl no instalado — requerido para archivos .xlsx") from exc

    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.active
        if ws is None:
            raise ValueError("Archivo XLSX sin hoja activa")

        raw_rows = list(ws.iter_rows(values_only=True))
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Error al leer el archivo XLSX: {exc}") from exc

    if not raw_rows:
        raise ValueError("El archivo XLSX está vacío")

    headers = [str(h).strip() if h is not None else "" for h in raw_rows[0]]

    rows: list[dict] = []
    for raw_row in raw_rows[1:]:
        row = {headers[i]: (str(v).strip() if v is not None else "") for i, v in enumerate(raw_row)}
        rows.append(row)

    return headers, rows
