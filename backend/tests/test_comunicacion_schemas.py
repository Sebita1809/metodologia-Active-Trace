"""
tests/test_comunicacion_schemas.py — TDD tests for comunicacion Pydantic schemas.

Group 2 tasks:
  2.1 — ComunicacionRead and all schemas reject extra fields (extra='forbid')
  2.2 — PreviewRequest / PreviewResponse
  2.3 — EncolarLoteRequest / EncolarLoteResponse
  2.4 — AprobarLoteRequest / AprobarItemRequest / ColaQuery

All tests are pure unit tests — no DB required.

Implemented: C-12 (comunicaciones-cola-worker)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.comunicacion import (
    AprobarItemRequest,
    AprobarLoteRequest,
    CancelarItemRequest,
    CancelarLoteRequest,
    ColaQuery,
    ComunicacionRead,
    DestinatarioLote,
    DestinatarioPreview,
    EncolarLoteRequest,
    EncolarLoteResponse,
    PreviewRequest,
    PreviewResponse,
    RenderResult,
)
from app.models.comunicacion import EstadoComunicacion


# ---------------------------------------------------------------------------
# Task 2.1 — extra='forbid' on all schemas
# ---------------------------------------------------------------------------

def test_comunicacion_read_rejects_extra_field():
    """ComunicacionRead rejects unknown fields."""
    data = {
        "id": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "enviado_por": str(uuid.uuid4()),
        "materia_id": str(uuid.uuid4()),
        "destinatario": "alumno@ejemplo.com",
        "asunto": "Test",
        "cuerpo": "Cuerpo",
        "estado": "Pendiente",
        "lote_id": str(uuid.uuid4()),
        "enviado_at": None,
        "aprobado_at": None,
        "aprobado_por": None,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "campo_extra": "forbidden",   # this must raise
    }
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ComunicacionRead.model_validate(data)


def test_comunicacion_read_valid_field_passes():
    """ComunicacionRead accepts all declared fields without extra."""
    now = datetime.now(tz=timezone.utc)
    data = {
        "id": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "enviado_por": str(uuid.uuid4()),
        "materia_id": str(uuid.uuid4()),
        "destinatario": "alumno@ejemplo.com",
        "asunto": "Test asunto",
        "cuerpo": "Test cuerpo",
        "estado": "Pendiente",
        "lote_id": str(uuid.uuid4()),
        "enviado_at": None,
        "aprobado_at": None,
        "aprobado_por": None,
        "created_at": now.isoformat(),
    }
    obj = ComunicacionRead.model_validate(data)
    assert obj.destinatario == "alumno@ejemplo.com"
    assert obj.estado == "Pendiente"


def test_encolar_lote_request_rejects_extra():
    """EncolarLoteRequest rejects unknown fields."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        EncolarLoteRequest.model_validate({
            "materia_id": str(uuid.uuid4()),
            "asunto": "subj",
            "cuerpo": "body",
            "destinatarios": [],
            "campo_extra": "forbidden",
        })


# ---------------------------------------------------------------------------
# Task 2.2 — PreviewRequest / PreviewResponse
# ---------------------------------------------------------------------------

def test_preview_request_valid():
    """PreviewRequest accepts valid data."""
    req = PreviewRequest(
        materia_id=uuid.uuid4(),
        asunto="Hola {{nombre_alumno}}",
        cuerpo="En {{materia}} tienes {{nota}}",
        destinatarios=[
            DestinatarioPreview(
                email="ana@example.com",
                variables={"nombre_alumno": "Ana", "materia": "Prog I", "nota": "8"},
            )
        ],
    )
    assert len(req.destinatarios) == 1
    assert req.destinatarios[0].email == "ana@example.com"


def test_preview_request_rejects_extra():
    """PreviewRequest rejects extra fields."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PreviewRequest.model_validate({
            "materia_id": str(uuid.uuid4()),
            "asunto": "subj",
            "cuerpo": "body",
            "destinatarios": [],
            "unknownField": True,
        })


def test_preview_response_valid():
    """PreviewResponse accepts a list of RenderResult."""
    resp = PreviewResponse(
        resultados=[
            RenderResult(
                email="ana@example.com",
                asunto_renderizado="Hola Ana",
                cuerpo_renderizado="En Prog I tienes 8",
            )
        ]
    )
    assert resp.resultados[0].asunto_renderizado == "Hola Ana"


# ---------------------------------------------------------------------------
# Task 2.3 — EncolarLoteRequest / EncolarLoteResponse
# ---------------------------------------------------------------------------

def test_encolar_lote_request_valid():
    """EncolarLoteRequest accepts valid data with destinatarios."""
    req = EncolarLoteRequest(
        materia_id=uuid.uuid4(),
        asunto="Hola {{nombre}}",
        cuerpo="Cuerpo {{variable}}",
        destinatarios=[
            DestinatarioLote(email="a@x.com", variables={"nombre": "A", "variable": "v"}),
            DestinatarioLote(email="b@x.com", variables={"nombre": "B", "variable": "w"}),
        ],
    )
    assert len(req.destinatarios) == 2


def test_encolar_lote_response_valid():
    """EncolarLoteResponse contains lote_id and cantidad."""
    lote_id = uuid.uuid4()
    resp = EncolarLoteResponse(lote_id=lote_id, cantidad=3)
    assert resp.lote_id == lote_id
    assert resp.cantidad == 3


def test_encolar_lote_response_rejects_extra():
    """EncolarLoteResponse rejects extra fields."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        EncolarLoteResponse.model_validate({
            "lote_id": str(uuid.uuid4()),
            "cantidad": 1,
            "extra": "nope",
        })


# ---------------------------------------------------------------------------
# Task 2.4 — AprobarLoteRequest / AprobarItemRequest / ColaQuery
# ---------------------------------------------------------------------------

def test_aprobar_lote_request_valid():
    """AprobarLoteRequest accepts a valid lote_id."""
    lote_id = uuid.uuid4()
    req = AprobarLoteRequest(lote_id=lote_id)
    assert req.lote_id == lote_id


def test_aprobar_lote_request_rejects_extra():
    """AprobarLoteRequest rejects extra fields."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AprobarLoteRequest.model_validate({"lote_id": str(uuid.uuid4()), "extra": True})


def test_aprobar_item_request_valid():
    """AprobarItemRequest accepts a valid comunicacion_id."""
    cid = uuid.uuid4()
    req = AprobarItemRequest(comunicacion_id=cid)
    assert req.comunicacion_id == cid


def test_cancelar_lote_request_valid():
    """CancelarLoteRequest accepts a valid lote_id."""
    lote_id = uuid.uuid4()
    req = CancelarLoteRequest(lote_id=lote_id)
    assert req.lote_id == lote_id


def test_cancelar_item_request_valid():
    """CancelarItemRequest accepts a valid comunicacion_id."""
    cid = uuid.uuid4()
    req = CancelarItemRequest(comunicacion_id=cid)
    assert req.comunicacion_id == cid


def test_cola_query_defaults():
    """ColaQuery has lote_id=None and estado=None by default."""
    q = ColaQuery()
    assert q.lote_id is None
    assert q.estado is None


def test_cola_query_with_estado():
    """ColaQuery accepts a valid EstadoComunicacion value."""
    q = ColaQuery(estado=EstadoComunicacion.Pendiente)
    assert q.estado == EstadoComunicacion.Pendiente


def test_cola_query_rejects_extra():
    """ColaQuery rejects extra fields."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ColaQuery.model_validate({"extra": "nope"})
