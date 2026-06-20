"""
app/services/encuentro_helpers.py — Pure helper functions for encuentros (C-13).

This module contains ONLY pure functions — no DB access, no side effects.
All functions are directly testable without any fixtures.

Functions:
    generar_fechas_recurrencia — compute N weekly dates aligned to a given weekday
    render_encuentros_html     — generate an HTML fragment for a list of instancias

Decision references:
  D2 — Recurrence dates computed as a pure function (no side effects)
  D5 — HTML is generated as a string by a pure function, no template engine

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Day-of-week constants — single source of truth
# ---------------------------------------------------------------------------

_DIA_SEMANA_TO_WEEKDAY: dict[str, int] = {
    "Lunes":     0,  # Monday    → Python weekday() == 0
    "Martes":    1,  # Tuesday
    "Miércoles": 2,  # Wednesday
    "Jueves":    3,  # Thursday
    "Viernes":   4,  # Friday
    "Sábado":    5,  # Saturday
    "Domingo":   6,  # Sunday
}

_VALID_DIAS: frozenset[str] = frozenset(_DIA_SEMANA_TO_WEEKDAY)


# ---------------------------------------------------------------------------
# Task 2.1 / 2.2 / 2.3 — generar_fechas_recurrencia
# ---------------------------------------------------------------------------

def generar_fechas_recurrencia(
    dia_semana: str,
    fecha_inicio: date,
    cant_semanas: int,
) -> list[date]:
    """Generate *cant_semanas* weekly dates aligned to *dia_semana*.

    Algorithm:
      1. Validate inputs.
      2. If *fecha_inicio* already falls on *dia_semana*, use it as the
         first occurrence; otherwise advance to the next matching weekday.
      3. Yield one date per week for *cant_semanas* iterations.

    Parameters:
        dia_semana   — weekday name in Spanish (e.g. "Lunes", "Miércoles")
        fecha_inicio — earliest possible start date
        cant_semanas — number of weekly occurrences to generate (1 ≤ n ≤ 52)

    Returns:
        List of *cant_semanas* dates, each separated by exactly 7 days.

    Raises:
        ValueError — if *dia_semana* is unknown or *cant_semanas* is out of range.

    Examples:
        >>> from datetime import date
        >>> generar_fechas_recurrencia("Lunes", date(2024, 1, 1), 3)
        [datetime.date(2024, 1, 1), datetime.date(2024, 1, 8), datetime.date(2024, 1, 15)]
        >>> # 2024-01-01 is a Monday — exactly aligned.

        >>> generar_fechas_recurrencia("Miércoles", date(2024, 1, 1), 2)
        [datetime.date(2024, 1, 3), datetime.date(2024, 1, 10)]
        >>> # 2024-01-01 is Monday → advance 2 days to Wednesday 2024-01-03.
    """
    if dia_semana not in _VALID_DIAS:
        raise ValueError(
            f"dia_semana {dia_semana!r} no válido. "
            f"Valores aceptados: {sorted(_VALID_DIAS)}"
        )

    if cant_semanas < 1 or cant_semanas > 52:
        raise ValueError(
            f"cant_semanas debe estar entre 1 y 52 (recibido: {cant_semanas})"
        )

    target_weekday = _DIA_SEMANA_TO_WEEKDAY[dia_semana]
    current_weekday = fecha_inicio.weekday()

    # Days to advance to reach the target weekday (0 if already aligned)
    days_ahead = (target_weekday - current_weekday) % 7
    first_occurrence = fecha_inicio + timedelta(days=days_ahead)

    return [first_occurrence + timedelta(weeks=i) for i in range(cant_semanas)]


# ---------------------------------------------------------------------------
# Task 2.5 — render_encuentros_html
# ---------------------------------------------------------------------------

def render_encuentros_html(instancias: list) -> str:
    """Generate an HTML fragment showing a table of encuentros.

    The fragment is designed for embedding in a Moodle virtual classroom.
    It does NOT include <html>/<body> tags — it is a self-contained <div>.

    Columns rendered:
      - Fecha (date)
      - Hora (time)
      - Título
      - Enlace de clase (meet_url, if present)
      - Grabación (video_url, if present)

    Edge case:
      - Empty list → fragment with a "Sin encuentros programados" message.

    Parameters:
        instancias — list of InstanciaEncuentro ORM objects (or any object with
                     the attributes: fecha, hora, titulo, meet_url, video_url)

    Returns:
        HTML string fragment.
    """
    if not instancias:
        return (
            '<div class="encuentros-calendario">'
            "<p>Sin encuentros programados.</p>"
            "</div>"
        )

    rows: list[str] = []
    for inst in instancias:
        fecha_str = inst.fecha.strftime("%d/%m/%Y") if inst.fecha else ""
        hora_str = inst.hora.strftime("%H:%M") if inst.hora else ""
        titulo_str = _escape_html(str(inst.titulo or ""))

        meet_cell = ""
        if inst.meet_url:
            url = _escape_html(str(inst.meet_url))
            meet_cell = f'<a href="{url}" target="_blank">Unirse</a>'

        video_cell = ""
        if inst.video_url:
            url = _escape_html(str(inst.video_url))
            video_cell = f'<a href="{url}" target="_blank">Ver grabación</a>'

        rows.append(
            f"<tr>"
            f"<td>{fecha_str}</td>"
            f"<td>{hora_str}</td>"
            f"<td>{titulo_str}</td>"
            f"<td>{meet_cell}</td>"
            f"<td>{video_cell}</td>"
            f"</tr>"
        )

    rows_html = "\n".join(rows)
    return (
        '<div class="encuentros-calendario">'
        "<table>"
        "<thead><tr>"
        "<th>Fecha</th><th>Hora</th><th>Título</th>"
        "<th>Clase</th><th>Grabación</th>"
        "</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table>"
        "</div>"
    )


def _escape_html(text: str) -> str:
    """Minimal HTML escaping for safe embedding of user-supplied strings."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
