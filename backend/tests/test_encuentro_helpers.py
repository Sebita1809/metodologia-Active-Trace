"""
tests/test_encuentro_helpers.py — TDD tests for pure encuentro helper functions.

Group 2 tasks (all pure unit tests — no DB required):
  2.1 RED: generar_fechas_recurrencia with cant_semanas=4 → 4 dates, 7-day step
  2.2 GREEN: implementation (in encuentro_helpers.py)
  2.3 TRIANGULATE:
    - fecha_inicio not on dia_semana → aligns to next correct day
    - cant_semanas=1 → single date
    - dia_semana boundary (Domingo)
    - invalid dia_semana → ValueError
    - cant_semanas out of range → ValueError
  2.4 REFACTOR: covered by implementation
  2.5 RED+GREEN+TRIANGULATE: render_encuentros_html
    - structure (fecha, hora, titulo, meet_url)
    - video_url link appears when set
    - empty list → "Sin encuentros programados" message

Strict TDD Evidence:
  Safety Net: N/A (new file, no existing tests to break)
  RED → GREEN → TRIANGULATE cycle followed for each behavior.

Implemented: C-13 (encuentros-y-guardias)
"""
from __future__ import annotations

from datetime import date, time
from types import SimpleNamespace

import pytest

import uuid

from app.services.encuentro_helpers import generar_fechas_recurrencia, render_encuentros_html


# ---------------------------------------------------------------------------
# Task 2.1 / 2.2 — generar_fechas_recurrencia happy path
# ---------------------------------------------------------------------------

def test_generar_4_fechas_desde_lunes_alineado():
    """RED→GREEN: fecha_inicio is Monday, cant_semanas=4 → 4 dates, 7-day step.

    2024-01-01 is a Monday. Requesting 4 Lunes from that date gives:
    2024-01-01, 2024-01-08, 2024-01-15, 2024-01-22.
    """
    result = generar_fechas_recurrencia("Lunes", date(2024, 1, 1), 4)
    assert len(result) == 4
    assert result[0] == date(2024, 1, 1)
    assert result[1] == date(2024, 1, 8)
    assert result[2] == date(2024, 1, 15)
    assert result[3] == date(2024, 1, 22)
    # Each step is exactly 7 days
    for i in range(1, len(result)):
        assert (result[i] - result[i - 1]).days == 7


def test_generar_paso_7_dias_exacto():
    """GREEN: All generated dates are exactly 7 days apart."""
    result = generar_fechas_recurrencia("Martes", date(2024, 1, 2), 6)
    assert len(result) == 6
    for i in range(1, len(result)):
        assert (result[i] - result[i - 1]).days == 7


# ---------------------------------------------------------------------------
# Task 2.3 — TRIANGULATE
# ---------------------------------------------------------------------------

def test_fecha_inicio_no_alineada_avanza_al_siguiente_dia():
    """TRIANGULATE: fecha_inicio not on dia_semana → advance to next match.

    2024-01-01 is Monday. Requesting Miércoles from that date should advance
    2 days to 2024-01-03 (Wednesday).
    """
    result = generar_fechas_recurrencia("Miércoles", date(2024, 1, 1), 2)
    assert result[0] == date(2024, 1, 3)  # first Wednesday from Monday 2024-01-01
    assert result[1] == date(2024, 1, 10)


def test_cant_semanas_1():
    """TRIANGULATE: cant_semanas=1 → exactly one date."""
    result = generar_fechas_recurrencia("Viernes", date(2024, 1, 5), 1)
    assert len(result) == 1
    assert result[0].weekday() == 4  # Friday


def test_domingo_weekday():
    """TRIANGULATE: Domingo boundary case — Python weekday() == 6."""
    result = generar_fechas_recurrencia("Domingo", date(2024, 1, 1), 2)
    assert result[0].weekday() == 6  # Sunday
    assert (result[1] - result[0]).days == 7


def test_fecha_inicio_ya_es_el_dia_correcto():
    """TRIANGULATE: fecha_inicio already falls on dia_semana → use it directly."""
    # 2024-01-05 is Friday (weekday 4)
    result = generar_fechas_recurrencia("Viernes", date(2024, 1, 5), 3)
    assert result[0] == date(2024, 1, 5)


def test_dia_semana_invalido_lanza_error():
    """TRIANGULATE: unknown dia_semana → ValueError."""
    with pytest.raises(ValueError, match="dia_semana"):
        generar_fechas_recurrencia("Monday", date(2024, 1, 1), 4)


def test_cant_semanas_cero_lanza_error():
    """TRIANGULATE: cant_semanas=0 → ValueError (must be 1..52)."""
    with pytest.raises(ValueError, match="cant_semanas"):
        generar_fechas_recurrencia("Lunes", date(2024, 1, 1), 0)


def test_cant_semanas_53_lanza_error():
    """TRIANGULATE: cant_semanas=53 → ValueError (exceeds max 52)."""
    with pytest.raises(ValueError, match="cant_semanas"):
        generar_fechas_recurrencia("Lunes", date(2024, 1, 1), 53)


def test_cant_semanas_52_ok():
    """TRIANGULATE: cant_semanas=52 is the allowed maximum."""
    result = generar_fechas_recurrencia("Lunes", date(2024, 1, 1), 52)
    assert len(result) == 52


# ---------------------------------------------------------------------------
# Task 2.5 — render_encuentros_html: RED+GREEN+TRIANGULATE
# ---------------------------------------------------------------------------

def _make_instancia(
    fecha=date(2024, 3, 1),
    hora=time(10, 0),
    titulo="Clase de prueba",
    meet_url="https://meet.example.com/room",
    video_url=None,
):
    """Helper: create a SimpleNamespace that mimics an InstanciaEncuentro."""
    return SimpleNamespace(
        fecha=fecha,
        hora=hora,
        titulo=titulo,
        meet_url=meet_url,
        video_url=video_url,
    )


def test_render_lista_vacia():
    """RED→GREEN: empty list → HTML with 'Sin encuentros programados'."""
    html = render_encuentros_html([])
    assert "Sin encuentros programados" in html
    assert "<div" in html


def test_render_contiene_fecha():
    """GREEN: HTML fragment contains the formatted date."""
    inst = _make_instancia(fecha=date(2024, 3, 15))
    html = render_encuentros_html([inst])
    assert "15/03/2024" in html


def test_render_contiene_titulo():
    """GREEN: HTML fragment contains the titulo."""
    inst = _make_instancia(titulo="Módulo 5 — Recursividad")
    html = render_encuentros_html([inst])
    assert "Módulo 5" in html


def test_render_contiene_link_meet():
    """GREEN: meet_url produces an anchor tag."""
    inst = _make_instancia(meet_url="https://meet.google.com/abc-defg")
    html = render_encuentros_html([inst])
    assert "https://meet.google.com/abc-defg" in html
    assert "<a " in html


def test_render_sin_video_url_no_tiene_grabacion():
    """TRIANGULATE: if video_url is None, no recording link appears."""
    inst = _make_instancia(video_url=None)
    html = render_encuentros_html([inst])
    assert "Ver grabación" not in html


def test_render_con_video_url_tiene_grabacion():
    """TRIANGULATE: video_url present → 'Ver grabación' link appears."""
    inst = _make_instancia(video_url="https://drive.google.com/recording/123")
    html = render_encuentros_html([inst])
    assert "Ver grabación" in html
    assert "https://drive.google.com/recording/123" in html


def test_render_multiples_instancias():
    """TRIANGULATE: multiple instancias → all appear in the HTML."""
    instancias = [
        _make_instancia(fecha=date(2024, 3, i), titulo=f"Clase {i}")
        for i in range(1, 4)
    ]
    html = render_encuentros_html(instancias)
    assert "Clase 1" in html
    assert "Clase 2" in html
    assert "Clase 3" in html


def test_render_escapa_html_en_titulo():
    """TRIANGULATE: user-supplied strings with HTML chars are escaped."""
    inst = _make_instancia(titulo="<script>alert('xss')</script>")
    html = render_encuentros_html([inst])
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_render_contiene_estructura_tabla():
    """TRIANGULATE: HTML fragment has table structure with headers."""
    inst = _make_instancia()
    html = render_encuentros_html([inst])
    assert "<table>" in html
    assert "<thead>" in html
    assert "<tbody>" in html


# ---------------------------------------------------------------------------
# Task 8.1 / 8.2 — Pydantic schema extra='forbid' (pure unit, no DB)
# ---------------------------------------------------------------------------

def test_slot_recurrente_request_rechaza_campo_extra():
    """Task 8.1 RED→GREEN: SlotRecurrenteRequest rejects extra fields."""
    import pydantic  # noqa: PLC0415
    from app.schemas.encuentro import SlotRecurrenteRequest  # noqa: PLC0415

    with pytest.raises(pydantic.ValidationError):
        SlotRecurrenteRequest(
            asignacion_id=str(uuid.uuid4()),
            materia_id=str(uuid.uuid4()),
            titulo="Test",
            dia_semana="Lunes",
            fecha_inicio="2024-01-01",
            cant_semanas=4,
            hora="10:00:00",
            campo_extra="no permitido",
        )


def test_editar_instancia_request_rechaza_campo_extra():
    """Task 8.1 TRIANGULATE: EditarInstanciaRequest also rejects extra fields."""
    import pydantic  # noqa: PLC0415
    from app.schemas.encuentro import EditarInstanciaRequest  # noqa: PLC0415

    with pytest.raises(pydantic.ValidationError):
        EditarInstanciaRequest(estado="Realizado", campo_extra="prohibido")


def test_guardia_request_rechaza_campo_extra():
    """Task 8.2 RED→GREEN: GuardiaRequest rejects extra fields."""
    import pydantic  # noqa: PLC0415
    from app.schemas.guardia import GuardiaRequest  # noqa: PLC0415

    with pytest.raises(pydantic.ValidationError):
        GuardiaRequest(
            asignacion_id=str(uuid.uuid4()),
            materia_id=str(uuid.uuid4()),
            carrera_id=str(uuid.uuid4()),
            cohorte_id=str(uuid.uuid4()),
            dia="Lunes",
            horario="14:00–14:45",
            campo_extra="prohibido",
        )


# ---------------------------------------------------------------------------
# Task 4.4 — RN-13 static validation (pure, no DB)
# ---------------------------------------------------------------------------

def test_rn13_ningun_modo_error():
    """Task 4.4 GREEN: neither mode set → DomainError (RN-13)."""
    from app.services.encuentro_service import DomainError, EncuentroService  # noqa: PLC0415

    with pytest.raises(DomainError, match="RN-13"):
        EncuentroService._validar_modo_exclusivo(cant_semanas=0, fecha_unica=None)


def test_rn13_ambos_modos_simultaneos_error():
    """Task 4.4 TRIANGULATE: cant_semanas > 0 + fecha_unica → DomainError."""
    from app.services.encuentro_service import DomainError, EncuentroService  # noqa: PLC0415

    with pytest.raises(DomainError, match="RN-13"):
        EncuentroService._validar_modo_exclusivo(
            cant_semanas=4, fecha_unica=date(2024, 3, 15)
        )


def test_instancia_encuentro_read_rechaza_campo_extra():
    """Task 8.1 TRIANGULATE: InstanciaEncuentroRead also rejects extra fields."""
    import pydantic  # noqa: PLC0415
    from app.schemas.encuentro import InstanciaEncuentroRead  # noqa: PLC0415

    with pytest.raises(pydantic.ValidationError):
        InstanciaEncuentroRead(
            id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
            slot_id=None,
            materia_id=str(uuid.uuid4()),
            fecha="2024-03-01",
            hora="10:00:00",
            titulo="Test",
            estado="Programado",
            meet_url=None,
            video_url=None,
            comentario=None,
            campo_extra="forbid me",
        )
