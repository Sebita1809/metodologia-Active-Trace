"""Tests for C-05 audit-log: audit_record, append-only, list_audit_logs filters."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_codes import AuditAction
from app.models.audit_log import AuditLog
from app.models.tenant import Tenant
from app.services.audit.audit_service import audit_record, list_audit_logs

pytestmark = pytest.mark.asyncio


# ═══════════════════════════════════════════════════════════════════
# 2.3 & 2.4  audit_record — full and minimal entries
# ═══════════════════════════════════════════════════════════════════


class TestAuditRecord:
    async def test_audit_record_full(
        self, db_session: AsyncSession, tenant_a: Tenant
    ) -> None:
        """WHEN audit_record is called with ALL fields THEN a complete AuditLog entry is persisted."""
        entry = await audit_record(
            db=db_session,
            actor_id=uuid.uuid4(),
            accion=AuditAction.CALIFICACIONES_IMPORTAR,
            tenant_id=tenant_a.id,
            impersonado_id=uuid.uuid4(),
            materia_id=uuid.uuid4(),
            detalle={"filename": "notas.xlsx", "count": 150},
            filas_afectadas=150,
            ip="192.168.1.1",
            user_agent="pytest/1.0",
        )
        assert entry.id is not None
        assert entry.accion == "CALIFICACIONES_IMPORTAR"
        assert entry.tenant_id == tenant_a.id
        assert entry.actor_id is not None
        assert entry.impersonado_id is not None
        assert entry.materia_id is not None
        assert entry.filas_afectadas == 150
        assert entry.detalle["filename"] == "notas.xlsx"
        assert entry.ip == "192.168.1.1"
        assert entry.user_agent == "pytest/1.0"

    async def test_audit_record_minimal(
        self, db_session: AsyncSession, tenant_a: Tenant
    ) -> None:
        """WHEN audit_record is called with only required fields THEN entry is persisted with NULL optionals."""
        entry = await audit_record(
            db=db_session,
            actor_id=uuid.uuid4(),
            accion=AuditAction.PADRON_CARGAR,
            tenant_id=tenant_a.id,
        )
        assert entry.id is not None
        assert entry.accion == "PADRON_CARGAR"
        assert entry.impersonado_id is None
        assert entry.materia_id is None
        assert entry.detalle is None
        assert entry.filas_afectadas is None
        assert entry.ip is None
        assert entry.user_agent is None


# ═══════════════════════════════════════════════════════════════════
# 4.2 & 4.3  Append-only — no update/delete methods
# ═══════════════════════════════════════════════════════════════════


class TestAppendOnly:
    async def test_no_update_method(
        self, db_session: AsyncSession, tenant_a: Tenant
    ) -> None:
        """WHEN checking audit_log repository THEN no update method exists."""
        from app.repositories.audit_log_repo import AuditLogRepository

        repo = AuditLogRepository()
        assert not hasattr(repo, "update") or not callable(
            getattr(repo, "update", None)
        )

    async def test_no_delete_method(
        self, db_session: AsyncSession, tenant_a: Tenant
    ) -> None:
        """WHEN checking audit_log repository THEN no delete method exists."""
        from app.repositories.audit_log_repo import AuditLogRepository

        repo = AuditLogRepository()
        assert not hasattr(repo, "delete") or not callable(
            getattr(repo, "delete", None)
        )

    async def test_trigger_rejects_update(
        self, db_session: AsyncSession, tenant_a: Tenant
    ) -> None:
        """WHEN UPDATE is executed directly on audit_log THEN trigger raises exception."""
        entry = await audit_record(
            db=db_session,
            actor_id=uuid.uuid4(),
            accion=AuditAction.PADRON_CARGAR,
            tenant_id=tenant_a.id,
        )
        with pytest.raises(Exception):
            await db_session.execute(
                sa_text("UPDATE audit_log SET accion = 'MODIFIED' WHERE id = :id"),
                {"id": entry.id},
            )
            await db_session.commit()

    async def test_trigger_rejects_delete(
        self, db_session: AsyncSession, tenant_a: Tenant
    ) -> None:
        """WHEN DELETE is executed directly on audit_log THEN trigger raises exception."""
        entry = await audit_record(
            db=db_session,
            actor_id=uuid.uuid4(),
            accion=AuditAction.PADRON_CARGAR,
            tenant_id=tenant_a.id,
        )
        with pytest.raises(Exception):
            await db_session.execute(
                sa_text("DELETE FROM audit_log WHERE id = :id"),
                {"id": entry.id},
            )
            await db_session.commit()


# ═══════════════════════════════════════════════════════════════════
# 5.2 — 5.5  list_audit_logs — filters and pagination
# ═══════════════════════════════════════════════════════════════════


class TestListAuditLogs:
    async def test_filter_by_date_range(
        self, db_session: AsyncSession, tenant_a: Tenant
    ) -> None:
        """WHEN filtering by date range THEN only entries in range are returned."""
        e1 = await audit_record(
            db=db_session,
            actor_id=uuid.uuid4(),
            accion=AuditAction.PADRON_CARGAR,
            tenant_id=tenant_a.id,
        )
        e2 = await audit_record(
            db=db_session,
            actor_id=uuid.uuid4(),
            accion=AuditAction.COMUNICACION_ENVIAR,
            tenant_id=tenant_a.id,
        )

        # Use a `fecha_desde` well before the entries were created
        fecha_desde = datetime.now(timezone.utc) - timedelta(hours=1)
        results = await list_audit_logs(
            db=db_session,
            tenant_id=tenant_a.id,
            fecha_desde=fecha_desde,
        )
        assert len(results) >= 2

    async def test_filter_by_actor(
        self, db_session: AsyncSession, tenant_a: Tenant
    ) -> None:
        """WHEN filtering by actor_id THEN only that actor's entries are returned."""
        actor = uuid.uuid4()
        await audit_record(
            db=db_session,
            actor_id=actor,
            accion=AuditAction.PADRON_CARGAR,
            tenant_id=tenant_a.id,
        )
        await audit_record(
            db=db_session,
            actor_id=uuid.uuid4(),
            accion=AuditAction.COMUNICACION_ENVIAR,
            tenant_id=tenant_a.id,
        )

        results = await list_audit_logs(
            db=db_session, tenant_id=tenant_a.id, actor_id=actor
        )
        assert len(results) == 1
        assert results[0].actor_id == actor

    async def test_filter_by_action(
        self, db_session: AsyncSession, tenant_a: Tenant
    ) -> None:
        """WHEN filtering by accion THEN only entries with that action code are returned."""
        actor = uuid.uuid4()
        await audit_record(
            db=db_session,
            actor_id=actor,
            accion=AuditAction.LIQUIDACION_CERRAR,
            tenant_id=tenant_a.id,
        )
        await audit_record(
            db=db_session,
            actor_id=actor,
            accion=AuditAction.PADRON_CARGAR,
            tenant_id=tenant_a.id,
        )

        results = await list_audit_logs(
            db=db_session,
            tenant_id=tenant_a.id,
            accion="LIQUIDACION_CERRAR",
        )
        assert len(results) >= 1
        assert all(r.accion == "LIQUIDACION_CERRAR" for r in results)

    async def test_pagination(
        self, db_session: AsyncSession, tenant_a: Tenant
    ) -> None:
        """WHEN using limit and offset THEN pagination works correctly."""
        actor = uuid.uuid4()
        for _ in range(5):
            await audit_record(
                db=db_session,
                actor_id=actor,
                accion=AuditAction.COMUNICACION_ENVIAR,
                tenant_id=tenant_a.id,
            )

        page1 = await list_audit_logs(
            db=db_session, tenant_id=tenant_a.id, limit=2, offset=0
        )
        page2 = await list_audit_logs(
            db=db_session, tenant_id=tenant_a.id, limit=2, offset=2
        )

        assert len(page1) == 2
        assert len(page2) == 2
        # Verify different entries returned per page
        ids_page1 = {r.id for r in page1}
        ids_page2 = {r.id for r in page2}
        assert len(ids_page1 & ids_page2) == 0
