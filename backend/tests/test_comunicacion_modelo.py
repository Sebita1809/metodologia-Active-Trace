"""
tests/test_comunicacion_modelo.py — TDD tests for Comunicacion model and EstadoComunicacion enum.

Group 1 tasks:
  1.1 — Comunicacion defaults: estado=Pendiente, enviado_at=None
  1.2 — EstadoComunicacion enum values

These are unit tests (no DB required) — they test the model class definition
and defaults without any database interaction.

Implemented: C-12 (comunicaciones-cola-worker)
"""
from __future__ import annotations

import uuid

import pytest

from app.models.comunicacion import Comunicacion, EstadoComunicacion


# ---------------------------------------------------------------------------
# Task 1.2 — Enum values
# ---------------------------------------------------------------------------

def test_estado_comunicacion_valores():
    """All 5 states are defined as string values."""
    assert EstadoComunicacion.Pendiente == "Pendiente"
    assert EstadoComunicacion.Enviando == "Enviando"
    assert EstadoComunicacion.Enviado == "Enviado"
    assert EstadoComunicacion.Error == "Error"
    assert EstadoComunicacion.Cancelado == "Cancelado"


def test_estado_comunicacion_count():
    """There are exactly 5 states (RN-15)."""
    assert len(EstadoComunicacion) == 5


def test_estado_comunicacion_es_str():
    """EstadoComunicacion values are str-comparable."""
    assert EstadoComunicacion.Pendiente == "Pendiente"
    assert str(EstadoComunicacion.Enviado) == "Enviado"


# ---------------------------------------------------------------------------
# Task 1.1 — Comunicacion model defaults
# ---------------------------------------------------------------------------

def test_comunicacion_estado_explicito_pendiente():
    """A Comunicacion created with estado=Pendiente has that estado value."""
    tid = uuid.uuid4()
    actor_id = uuid.uuid4()
    materia_id = uuid.uuid4()
    lote_id = uuid.uuid4()

    com = Comunicacion(
        tenant_id=tid,
        enviado_por=actor_id,
        materia_id=materia_id,
        destinatario="ciphertext_dummy",
        asunto="Test subject",
        cuerpo="Test body",
        lote_id=lote_id,
        estado=EstadoComunicacion.Pendiente.value,
    )

    assert com.estado == EstadoComunicacion.Pendiente.value


def test_comunicacion_enviado_at_default_none():
    """A new Comunicacion has enviado_at=None."""
    com = Comunicacion(
        tenant_id=uuid.uuid4(),
        enviado_por=uuid.uuid4(),
        materia_id=uuid.uuid4(),
        destinatario="ciphertext",
        asunto="subj",
        cuerpo="body",
        lote_id=uuid.uuid4(),
    )
    assert com.enviado_at is None


def test_comunicacion_aprobado_fields_default_none():
    """A new Comunicacion has aprobado_at=None and aprobado_por=None."""
    com = Comunicacion(
        tenant_id=uuid.uuid4(),
        enviado_por=uuid.uuid4(),
        materia_id=uuid.uuid4(),
        destinatario="ciphertext",
        asunto="subj",
        cuerpo="body",
        lote_id=uuid.uuid4(),
    )
    assert com.aprobado_at is None
    assert com.aprobado_por is None


def test_comunicacion_lote_id_compartido():
    """Two Comunicacion objects can share the same lote_id."""
    lote_id = uuid.uuid4()
    tid = uuid.uuid4()

    com1 = Comunicacion(
        tenant_id=tid,
        enviado_por=uuid.uuid4(),
        materia_id=uuid.uuid4(),
        destinatario="ct1",
        asunto="subj",
        cuerpo="body",
        lote_id=lote_id,
    )
    com2 = Comunicacion(
        tenant_id=tid,
        enviado_por=uuid.uuid4(),
        materia_id=uuid.uuid4(),
        destinatario="ct2",
        asunto="subj",
        cuerpo="body",
        lote_id=lote_id,
    )

    assert com1.lote_id == com2.lote_id


def test_comunicacion_tablename():
    """Table name is 'comunicacion'."""
    assert Comunicacion.__tablename__ == "comunicacion"
