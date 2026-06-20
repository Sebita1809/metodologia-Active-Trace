"""
tests/test_aviso_helpers.py — Unit tests for aviso pure helper functions.

These tests do NOT require a database — they exercise pure logic only.

Tests cover:
  - aviso_es_vigente: checks datetime range logic
  - usuario_en_audiencia: checks audience segmentation logic for all alcance values
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.services.aviso_helpers import aviso_es_vigente, usuario_en_audiencia


# ---------------------------------------------------------------------------
# aviso_es_vigente
# ---------------------------------------------------------------------------

def test_aviso_es_vigente_inside_window():
    """ahora between inicio_en and fin_en → True"""
    inicio = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fin = datetime(2026, 12, 31, tzinfo=timezone.utc)
    ahora = datetime(2026, 6, 15, tzinfo=timezone.utc)
    assert aviso_es_vigente(inicio, fin, ahora) is True


def test_aviso_es_vigente_before_window():
    """ahora before inicio_en → False"""
    inicio = datetime(2026, 7, 1, tzinfo=timezone.utc)
    fin = datetime(2026, 12, 31, tzinfo=timezone.utc)
    ahora = datetime(2026, 6, 15, tzinfo=timezone.utc)
    assert aviso_es_vigente(inicio, fin, ahora) is False


def test_aviso_es_vigente_after_window():
    """ahora after fin_en → False"""
    inicio = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fin = datetime(2026, 3, 31, tzinfo=timezone.utc)
    ahora = datetime(2026, 6, 15, tzinfo=timezone.utc)
    assert aviso_es_vigente(inicio, fin, ahora) is False


def test_aviso_es_vigente_exact_inicio():
    """ahora == inicio_en → True (inclusive)"""
    inicio = datetime(2026, 6, 15, tzinfo=timezone.utc)
    fin = datetime(2026, 12, 31, tzinfo=timezone.utc)
    ahora = datetime(2026, 6, 15, tzinfo=timezone.utc)
    assert aviso_es_vigente(inicio, fin, ahora) is True


def test_aviso_es_vigente_exact_fin():
    """ahora == fin_en → True (inclusive)"""
    inicio = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fin = datetime(2026, 6, 15, tzinfo=timezone.utc)
    ahora = datetime(2026, 6, 15, tzinfo=timezone.utc)
    assert aviso_es_vigente(inicio, fin, ahora) is True


# ---------------------------------------------------------------------------
# usuario_en_audiencia — Global
# ---------------------------------------------------------------------------

def test_audiencia_global_always_true():
    """alcance=Global → always True regardless of other params"""
    assert usuario_en_audiencia(
        alcance="Global",
        rol_destino=None,
        cohorte_id=None,
        materia_id=None,
        usuario_rol="ALUMNO",
        usuario_cohorte_ids=[],
        usuario_materia_ids=[],
    ) is True


def test_audiencia_global_with_different_rol():
    """alcance=Global → True even when user has different rol"""
    assert usuario_en_audiencia(
        alcance="Global",
        rol_destino="COORDINADOR",
        cohorte_id=None,
        materia_id=None,
        usuario_rol="ALUMNO",
        usuario_cohorte_ids=[],
        usuario_materia_ids=[],
    ) is True


# ---------------------------------------------------------------------------
# usuario_en_audiencia — PorRol
# ---------------------------------------------------------------------------

def test_audiencia_por_rol_matching():
    """alcance=PorRol → True when rol_destino == usuario_rol"""
    assert usuario_en_audiencia(
        alcance="PorRol",
        rol_destino="ALUMNO",
        cohorte_id=None,
        materia_id=None,
        usuario_rol="ALUMNO",
        usuario_cohorte_ids=[],
        usuario_materia_ids=[],
    ) is True


def test_audiencia_por_rol_not_matching():
    """alcance=PorRol → False when rol_destino != usuario_rol"""
    assert usuario_en_audiencia(
        alcance="PorRol",
        rol_destino="COORDINADOR",
        cohorte_id=None,
        materia_id=None,
        usuario_rol="ALUMNO",
        usuario_cohorte_ids=[],
        usuario_materia_ids=[],
    ) is False


def test_audiencia_por_rol_profesor():
    """alcance=PorRol with PROFESOR rol matches PROFESOR user"""
    assert usuario_en_audiencia(
        alcance="PorRol",
        rol_destino="PROFESOR",
        cohorte_id=None,
        materia_id=None,
        usuario_rol="PROFESOR",
        usuario_cohorte_ids=[],
        usuario_materia_ids=[],
    ) is True


# ---------------------------------------------------------------------------
# usuario_en_audiencia — PorCohorte
# ---------------------------------------------------------------------------

def test_audiencia_por_cohorte_in_list():
    """alcance=PorCohorte → True when cohorte_id in usuario_cohorte_ids"""
    cid = uuid.uuid4()
    assert usuario_en_audiencia(
        alcance="PorCohorte",
        rol_destino=None,
        cohorte_id=cid,
        materia_id=None,
        usuario_rol="ALUMNO",
        usuario_cohorte_ids=[cid],
        usuario_materia_ids=[],
    ) is True


def test_audiencia_por_cohorte_not_in_list():
    """alcance=PorCohorte → False when cohorte_id NOT in usuario_cohorte_ids"""
    cid = uuid.uuid4()
    other_cid = uuid.uuid4()
    assert usuario_en_audiencia(
        alcance="PorCohorte",
        rol_destino=None,
        cohorte_id=cid,
        materia_id=None,
        usuario_rol="ALUMNO",
        usuario_cohorte_ids=[other_cid],
        usuario_materia_ids=[],
    ) is False


def test_audiencia_por_cohorte_empty_list():
    """alcance=PorCohorte → False when usuario_cohorte_ids is empty"""
    cid = uuid.uuid4()
    assert usuario_en_audiencia(
        alcance="PorCohorte",
        rol_destino=None,
        cohorte_id=cid,
        materia_id=None,
        usuario_rol="ALUMNO",
        usuario_cohorte_ids=[],
        usuario_materia_ids=[],
    ) is False


# ---------------------------------------------------------------------------
# usuario_en_audiencia — PorMateria
# ---------------------------------------------------------------------------

def test_audiencia_por_materia_in_list():
    """alcance=PorMateria → True when materia_id in usuario_materia_ids"""
    mid = uuid.uuid4()
    assert usuario_en_audiencia(
        alcance="PorMateria",
        rol_destino=None,
        cohorte_id=None,
        materia_id=mid,
        usuario_rol="ALUMNO",
        usuario_cohorte_ids=[],
        usuario_materia_ids=[mid],
    ) is True


def test_audiencia_por_materia_not_in_list():
    """alcance=PorMateria → False when materia_id NOT in usuario_materia_ids"""
    mid = uuid.uuid4()
    other_mid = uuid.uuid4()
    assert usuario_en_audiencia(
        alcance="PorMateria",
        rol_destino=None,
        cohorte_id=None,
        materia_id=mid,
        usuario_rol="ALUMNO",
        usuario_cohorte_ids=[],
        usuario_materia_ids=[other_mid],
    ) is False


def test_audiencia_unknown_alcance_returns_false():
    """Unknown alcance → False (safe default)"""
    assert usuario_en_audiencia(
        alcance="UNKNOWN",
        rol_destino=None,
        cohorte_id=None,
        materia_id=None,
        usuario_rol="ALUMNO",
        usuario_cohorte_ids=[],
        usuario_materia_ids=[],
    ) is False
