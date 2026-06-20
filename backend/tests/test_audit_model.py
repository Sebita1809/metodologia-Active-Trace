"""
tests/test_audit_model.py — TDD tests for AuditLog SQLAlchemy model (Task 3).

Verifies:
  - AuditLog exposes required columns (id, tenant_id, fecha_hora, actor_id,
    impersonado_id, materia_id, accion, detalle, filas_afectadas, ip, user_agent)
  - AuditLog does NOT define updated_at or deleted_at (immutable by design)

No DB required for pure model/column inspection tests.

TDD cycle:
  RED   — written before implementation
  GREEN — audit_log.py model created
"""
from __future__ import annotations

import pytest
from sqlalchemy import inspect as sa_inspect


def test_audit_log_model_has_required_columns():
    """AuditLog SQLAlchemy model exposes all required columns."""
    from app.models.audit_log import AuditLog  # noqa: PLC0415

    mapper = sa_inspect(AuditLog)
    column_names = {col.key for col in mapper.columns}

    required = {
        "id",
        "tenant_id",
        "fecha_hora",
        "actor_id",
        "impersonado_id",
        "materia_id",
        "accion",
        "detalle",
        "filas_afectadas",
        "ip",
        "user_agent",
    }
    missing = required - column_names
    assert not missing, f"AuditLog is missing columns: {missing}"


def test_audit_log_impersonado_id_is_nullable():
    """impersonado_id is nullable (impersonation is optional)."""
    from sqlalchemy import inspect as sa_inspect  # noqa: PLC0415
    from app.models.audit_log import AuditLog  # noqa: PLC0415

    mapper = sa_inspect(AuditLog)
    col = mapper.columns["impersonado_id"]
    assert col.nullable, "impersonado_id should be nullable"


def test_audit_log_materia_id_is_nullable():
    """materia_id is nullable (not all actions relate to a materia)."""
    from sqlalchemy import inspect as sa_inspect  # noqa: PLC0415
    from app.models.audit_log import AuditLog  # noqa: PLC0415

    mapper = sa_inspect(AuditLog)
    col = mapper.columns["materia_id"]
    assert col.nullable, "materia_id should be nullable"


def test_audit_log_does_not_have_updated_at():
    """AuditLog must NOT define updated_at — the model is immutable."""
    from sqlalchemy import inspect as sa_inspect  # noqa: PLC0415
    from app.models.audit_log import AuditLog  # noqa: PLC0415

    mapper = sa_inspect(AuditLog)
    column_names = {col.key for col in mapper.columns}
    assert "updated_at" not in column_names, (
        "AuditLog must not have updated_at (immutable model)"
    )


def test_audit_log_does_not_have_deleted_at():
    """AuditLog must NOT define deleted_at — append-only, no soft-delete."""
    from sqlalchemy import inspect as sa_inspect  # noqa: PLC0415
    from app.models.audit_log import AuditLog  # noqa: PLC0415

    mapper = sa_inspect(AuditLog)
    column_names = {col.key for col in mapper.columns}
    assert "deleted_at" not in column_names, (
        "AuditLog must not have deleted_at (append-only, no soft-delete)"
    )


def test_audit_log_tablename():
    """AuditLog maps to the 'audit_log' table."""
    from app.models.audit_log import AuditLog  # noqa: PLC0415

    assert AuditLog.__tablename__ == "audit_log"


def test_audit_log_is_not_base_tenant_model():
    """AuditLog must NOT inherit BaseTenantModel (which brings updated_at/deleted_at)."""
    from app.models.audit_log import AuditLog  # noqa: PLC0415
    from app.models.base import BaseTenantModel  # noqa: PLC0415

    assert not issubclass(AuditLog, BaseTenantModel), (
        "AuditLog must not inherit BaseTenantModel"
    )


def test_audit_log_detalle_is_jsonb():
    """detalle column is mapped as JSONB for structured context storage."""
    from sqlalchemy.dialects.postgresql import JSONB  # noqa: PLC0415
    from sqlalchemy import inspect as sa_inspect  # noqa: PLC0415
    from app.models.audit_log import AuditLog  # noqa: PLC0415

    mapper = sa_inspect(AuditLog)
    col = mapper.columns["detalle"]
    assert isinstance(col.type, JSONB), (
        f"detalle should be JSONB, got {type(col.type)}"
    )
