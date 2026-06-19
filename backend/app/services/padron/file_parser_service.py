"""Service for parsing xlsx/csv padron import files."""
from __future__ import annotations

import csv
import io
import uuid
from io import BytesIO
from typing import Any

from fastapi import HTTPException, UploadFile


# Expected columns and their aliases for fuzzy matching
COLUMN_MAP = {
    "nombre": ["nombre", "name", "first_name", "firstname", "nombres"],
    "apellidos": ["apellidos", "apellido", "last_name", "lastname", "surname", "surnames", "apellido_materno", "apellido_paterno"],
    "email": ["email", "e-mail", "mail", "correo", "correo_electronico"],
    "comision": ["comision", "comisión", "commission", "group", "grupo", "comite", "comité"],
    "regional": ["regional", "region", "sede", "campus", "branch"],
}

REQUIRED_COLUMNS = {"nombre", "apellidos", "email"}


class FileParserService:
    """Parse and validate padron import files (xlsx/csv)."""

    async def parse(self, file: UploadFile) -> dict[str, Any]:
        """Detect file format and delegate to appropriate parser.

        Returns a dict with:
        - column_mapping: dict[str, str] (field_name -> header name detected)
        - rows: list[dict] (parsed rows with original headers)
        - total_rows: int
        - sample_rows: list[dict] (first 5)
        - errores: list[str]
        - columnas_faltantes: list[str]
        """
        filename = file.filename or ""
        content = await file.read()

        if filename.lower().endswith(".xlsx"):
            return self._parse_xlsx(content)
        elif filename.lower().endswith(".csv"):
            return self._parse_csv(content)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Formato no soportado: '{filename}'. Use .xlsx o .csv",
            )

    def _parse_xlsx(self, content: bytes) -> dict[str, Any]:
        try:
            import openpyxl

            wb = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)
            ws = wb.active
            if ws is None:
                return {"error": "El archivo xlsx no tiene hojas activas"}

            rows_iter = ws.iter_rows(values_only=True)
            headers = [str(cell).strip() if cell is not None else "" for cell in next(rows_iter, [])]

            column_mapping, missing = self._auto_detect_columns(headers)

            raw_rows = []
            for row in rows_iter:
                row_dict = {}
                for i, val in enumerate(row):
                    if i < len(headers):
                        row_dict[headers[i]] = str(val).strip() if val is not None else ""
                raw_rows.append(row_dict)

            wb.close()
            return self._build_result(column_mapping, missing, raw_rows)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Error al leer archivo xlsx: {str(e)}")

    def _parse_csv(self, content: bytes) -> dict[str, Any]:
        try:
            text = content.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            headers = reader.fieldnames or []

            column_mapping, missing = self._auto_detect_columns(headers)

            raw_rows = []
            for row in reader:
                cleaned = {k.strip(): v.strip() for k, v in row.items()}
                raw_rows.append(cleaned)

            return self._build_result(column_mapping, missing, raw_rows)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Error al leer archivo csv: {str(e)}")

    def _auto_detect_columns(self, headers: list[str]) -> tuple[dict[str, str], list[str]]:
        """Fuzzy-match headers to known fields.

        Returns (column_mapping, missing_columns).
        column_mapping: {canonical_field: detected_header_name}
        """
        mapping = {}
        header_lower = {h: h.lower().replace(" ", "_").replace("-", "_") for h in headers}

        for canonical, aliases in COLUMN_MAP.items():
            matched = None
            for header_orig, header_low in header_lower.items():
                if header_low in aliases or header_low == canonical:
                    matched = header_orig
                    break
                if canonical in header_low:
                    matched = header_orig
                    break
                for alias in aliases:
                    if alias in header_low or header_low in alias:
                        matched = header_orig
                        break
                if matched:
                    break
            if matched:
                mapping[canonical] = matched

        missing = [col for col in REQUIRED_COLUMNS if col not in mapping]
        return mapping, missing

    def _build_result(
        self, column_mapping: dict[str, str], missing: list[str], raw_rows: list[dict]
    ) -> dict[str, Any]:
        errores = []
        if missing:
            errores.append(f"Columnas requeridas faltantes: {', '.join(missing)}")

        for i, row in enumerate(raw_rows):
            row_errors = []
            row_num = i + 2

            if "nombre" in column_mapping:
                header = column_mapping["nombre"]
                if not row.get(header, "").strip():
                    row_errors.append(f"Fila {row_num}: nombre vacío")

            if "apellidos" in column_mapping:
                header = column_mapping["apellidos"]
                if not row.get(header, "").strip():
                    row_errors.append(f"Fila {row_num}: apellidos vacíos")

            if "email" in column_mapping:
                header = column_mapping["email"]
                val = row.get(header, "").strip()
                if not val:
                    row_errors.append(f"Fila {row_num}: email vacío")
                elif "@" not in val:
                    row_errors.append(f"Fila {row_num}: email inválido '{val}'")

            errores.extend(row_errors)

        mapped_rows = []
        for row in raw_rows:
            mapped = {}
            for canonical, header in column_mapping.items():
                mapped[canonical] = row.get(header, "").strip()
            mapped_rows.append(mapped)

        return {
            "column_mapping": column_mapping,
            "total_rows": len(mapped_rows),
            "sample_rows": mapped_rows[:5],
            "errores": errores,
            "columnas_faltantes": missing,
            "rows": mapped_rows,
        }
