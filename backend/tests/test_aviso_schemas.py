"""
tests/test_aviso_schemas.py — Unit tests for AvisoCreate/AvisoUpdate validators.

No DB required — purely Pydantic validation tests.

Tests cover:
  - AvisoCreate valid cases
  - AvisoCreate validator: PorMateria requires materia_id
  - AvisoCreate validator: PorCohorte requires cohorte_id
  - AvisoCreate validator: PorRol requires rol_destino
  - AvisoCreate valid Global (no context fields needed)
  - AvisoUpdate with partial fields
  - AvisoUpdate validator: PorMateria requires materia_id
  - extra='forbid' rejects unknown fields
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.avisos import AvisoCreate, AvisoUpdate

_NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)
_LATER = datetime(2026, 12, 31, tzinfo=timezone.utc)


def _base_create(**overrides):
    """Return minimal valid AvisoCreate kwargs."""
    data = {
        "alcance": "Global",
        "severidad": "Info",
        "titulo": "Aviso de prueba",
        "cuerpo": "Cuerpo del aviso",
        "inicio_en": _NOW,
        "fin_en": _LATER,
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# AvisoCreate — valid cases
# ---------------------------------------------------------------------------

def test_aviso_create_global_valid():
    """Global aviso with no context fields → valid"""
    aviso = AvisoCreate(**_base_create())
    assert aviso.alcance == "Global"
    assert aviso.materia_id is None
    assert aviso.cohorte_id is None
    assert aviso.rol_destino is None


def test_aviso_create_por_materia_valid():
    """PorMateria with materia_id → valid"""
    mid = uuid.uuid4()
    aviso = AvisoCreate(**_base_create(alcance="PorMateria", materia_id=mid))
    assert aviso.materia_id == mid


def test_aviso_create_por_cohorte_valid():
    """PorCohorte with cohorte_id → valid"""
    cid = uuid.uuid4()
    aviso = AvisoCreate(**_base_create(alcance="PorCohorte", cohorte_id=cid))
    assert aviso.cohorte_id == cid


def test_aviso_create_por_rol_valid():
    """PorRol with rol_destino → valid"""
    aviso = AvisoCreate(**_base_create(alcance="PorRol", rol_destino="ALUMNO"))
    assert aviso.rol_destino == "ALUMNO"


# ---------------------------------------------------------------------------
# AvisoCreate — validator failures
# ---------------------------------------------------------------------------

def test_aviso_create_por_materia_missing_materia_id():
    """PorMateria without materia_id → ValidationError"""
    with pytest.raises(ValidationError) as exc_info:
        AvisoCreate(**_base_create(alcance="PorMateria"))
    assert "materia_id" in str(exc_info.value).lower()


def test_aviso_create_por_cohorte_missing_cohorte_id():
    """PorCohorte without cohorte_id → ValidationError"""
    with pytest.raises(ValidationError) as exc_info:
        AvisoCreate(**_base_create(alcance="PorCohorte"))
    assert "cohorte_id" in str(exc_info.value).lower()


def test_aviso_create_por_rol_missing_rol_destino():
    """PorRol without rol_destino → ValidationError"""
    with pytest.raises(ValidationError) as exc_info:
        AvisoCreate(**_base_create(alcance="PorRol"))
    assert "rol_destino" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# AvisoCreate — extra='forbid'
# ---------------------------------------------------------------------------

def test_aviso_create_extra_field_rejected():
    """Unknown field rejected → ValidationError"""
    with pytest.raises(ValidationError):
        AvisoCreate(**_base_create(unexpected_field="bad"))


# ---------------------------------------------------------------------------
# AvisoCreate — defaults
# ---------------------------------------------------------------------------

def test_aviso_create_defaults():
    """Default severidad=Info, orden=0, activo=True, requiere_ack=False"""
    aviso = AvisoCreate(**_base_create())
    assert aviso.severidad == "Info"
    assert aviso.orden == 0
    assert aviso.activo is True
    assert aviso.requiere_ack is False


def test_aviso_create_critico_severidad():
    """severidad=Critico is accepted"""
    aviso = AvisoCreate(**_base_create(severidad="Critico"))
    assert aviso.severidad == "Critico"


# ---------------------------------------------------------------------------
# AvisoUpdate — partial update
# ---------------------------------------------------------------------------

def test_aviso_update_empty_is_valid():
    """AvisoUpdate with no fields → valid (all None)"""
    upd = AvisoUpdate()
    assert upd.titulo is None
    assert upd.alcance is None


def test_aviso_update_partial_fields():
    """AvisoUpdate with only titulo → valid"""
    upd = AvisoUpdate(titulo="Nuevo título")
    assert upd.titulo == "Nuevo título"
    assert upd.cuerpo is None


def test_aviso_update_por_materia_missing_id():
    """AvisoUpdate PorMateria without materia_id → ValidationError"""
    with pytest.raises(ValidationError) as exc_info:
        AvisoUpdate(alcance="PorMateria")
    assert "materia_id" in str(exc_info.value).lower()


def test_aviso_update_extra_field_rejected():
    """AvisoUpdate with unknown field → ValidationError"""
    with pytest.raises(ValidationError):
        AvisoUpdate(unknown_field="bad")
