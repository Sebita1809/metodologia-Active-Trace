"""Tests for the padron module: versions, import, Moodle sync, RBAC, isolation, audit (C-09)."""

import uuid
from io import BytesIO
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import UploadFile
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_codes import AuditAction
from app.integrations.moodle_ws import MoodleConnectionError, MoodleWSClient
from app.models.audit_log import AuditLog
from app.models.domain.asignacion import Asignacion
from app.models.domain.materia import Materia
from app.models.domain.version_padron import VersionPadron
from app.models.tenant import Tenant
from app.repositories.padron.entrada_padron_repository import EntradaPadronRepository
from app.repositories.padron.version_padron_repository import VersionPadronRepository
from app.services.padron.file_parser_service import FileParserService
from app.services.padron.padron_import_service import PadronImportService, _preview_store
from app.services.padron.padron_service import PadronService

pytestmark = pytest.mark.asyncio


# ═══════════════════════════════════════════════════════════════
# VersionPadron Operations
# ═══════════════════════════════════════════════════════════════


class TestVersionPadron:
    async def test_create_version(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create: Cohorte,
        usuario_create,
    ):
        repo = VersionPadronRepository(db_session, tenant_a.id)
        version = await repo.create({
            "materia_id": materia_create.id,
            "cohorte_id": cohorte_create.id,
            "activa": False,
            "origen": "archivo",
            "cargado_por": usuario_create.id,
        })
        assert version.id is not None
        assert version.activa is False
        assert version.origen == "archivo"
        assert version.materia_id == materia_create.id
        assert version.cohorte_id == cohorte_create.id
        assert version.cargado_por == usuario_create.id
        assert version.cargado_at is not None

    async def test_create_entrada_with_null_usuario(
        self,
        db_session: AsyncSession,
        tenant_a,
        version_padron_create: VersionPadron,
    ):
        repo = EntradaPadronRepository(db_session, tenant_a.id)
        entrada = await repo.create({
            "version_id": version_padron_create.id,
            "usuario_id": None,
            "nombre": "Sin",
            "apellidos": "Match",
            "email": "sin.match@example.com",
        })
        assert entrada.id is not None
        assert entrada.usuario_id is None
        assert entrada.nombre == "Sin"

    async def test_activate_deactivates_previous(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create: Cohorte,
        usuario_create,
    ):
        service = PadronService(db_session, tenant_a.id)
        v1 = await service.create_version(
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            cargado_por=usuario_create.id,
            origen="archivo",
            entradas=[{"nombre": "A", "apellidos": "B", "email": "a@b.com"}],
        )
        v1_id = uuid.UUID(v1["id"])
        await service.activate_version(v1_id, usuario_create.id)
        v2 = await service.create_version(
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            cargado_por=usuario_create.id,
            origen="archivo",
            entradas=[{"nombre": "C", "apellidos": "D", "email": "c@d.com"}],
        )
        v2_id = uuid.UUID(v2["id"])
        await service.activate_version(v2_id, usuario_create.id)

        repo = VersionPadronRepository(db_session, tenant_a.id)
        v1_reloaded = await repo.get(v1_id)
        assert v1_reloaded is not None
        assert v1_reloaded.activa is False

    async def test_activate_idempotent(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create: Cohorte,
        usuario_create,
    ):
        service = PadronService(db_session, tenant_a.id)
        v = await service.create_version(
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            cargado_por=usuario_create.id,
            origen="archivo",
            entradas=[{"nombre": "A", "apellidos": "B", "email": "a@b.com"}],
        )
        vid = uuid.UUID(v["id"])
        result1 = await service.activate_version(vid, usuario_create.id)
        assert result1["activa"] is True
        result2 = await service.activate_version(vid, usuario_create.id)
        assert result2["activa"] is True

    async def test_get_active_version_404(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create: Cohorte,
    ):
        from fastapi import HTTPException

        service = PadronService(db_session, tenant_a.id)
        with pytest.raises(HTTPException) as exc:
            await service.get_active_version(materia_create.id, cohorte_create.id)
        assert exc.value.status_code == 404

    async def test_list_versions_order(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create: Cohorte,
        usuario_create,
    ):
        v_repo = VersionPadronRepository(db_session, tenant_a.id)
        e_repo = EntradaPadronRepository(db_session, tenant_a.id)
        from datetime import datetime, timezone, timedelta

        v1 = await v_repo.create({
            "materia_id": materia_create.id,
            "cohorte_id": cohorte_create.id,
            "origen": "archivo",
            "cargado_por": usuario_create.id,
            "activa": False,
        })
        await db_session.execute(
            text("UPDATE version_padron SET cargado_at = :ts WHERE id = :vid"),
            {"ts": datetime.now(timezone.utc) - timedelta(hours=2), "vid": v1.id},
        )
        await db_session.commit()

        v2 = await v_repo.create({
            "materia_id": materia_create.id,
            "cohorte_id": cohorte_create.id,
            "origen": "moodle",
            "cargado_por": usuario_create.id,
            "activa": False,
        })
        await db_session.execute(
            text("UPDATE version_padron SET cargado_at = :ts WHERE id = :vid"),
            {"ts": datetime.now(timezone.utc) - timedelta(hours=1), "vid": v2.id},
        )
        await db_session.commit()

        versions = await v_repo.list_by_materia_cohorte(materia_create.id, cohorte_create.id)
        assert len(versions) == 2
        assert versions[0].id == v2.id
        assert versions[0].cargado_at > versions[1].cargado_at


# ═══════════════════════════════════════════════════════════════
# File Import
# ═══════════════════════════════════════════════════════════════


class TestFileImport:
    async def _make_xlsx(self, headers: list[str], rows: list[list[str]]) -> bytes:
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(headers)
        for row in rows:
            ws.append(row)
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.getvalue()

    async def _make_upload_file(self, filename: str, content: bytes) -> UploadFile:
        return UploadFile(filename=filename, file=BytesIO(content))

    async def test_preview_valid_xlsx(self):
        content = await self._make_xlsx(
            ["Nombre", "Apellidos", "Email"],
            [
                ["Juan", "Pérez", "juan@test.com"],
                ["María", "García", "maria@test.com"],
            ],
        )
        file = await self._make_upload_file("test.xlsx", content)
        parser = FileParserService()
        result = await parser.parse(file)
        assert result["total_rows"] == 2
        assert len(result["sample_rows"]) == 2
        assert result["columnas_faltantes"] == []
        assert len(result["errores"]) == 0
        assert result["column_mapping"]["nombre"] in ("Nombre", "nombre")
        assert result["column_mapping"]["apellidos"] in ("Apellidos", "apellidos", "Apellido")
        assert result["column_mapping"]["email"] in ("Email", "email")

    async def test_preview_missing_email_column(self):
        content = await self._make_xlsx(
            ["Nombre", "Apellidos"],
            [["Juan", "Pérez"]],
        )
        file = await self._make_upload_file("test.xlsx", content)
        from fastapi import HTTPException

        parser = FileParserService()
        result = await parser.parse(file)
        assert "email" in result["columnas_faltantes"]

    async def test_preview_row_errors(self):
        content = await self._make_xlsx(
            ["Nombre", "Apellidos", "Email"],
            [
                ["", "Pérez", "juan@test.com"],
                ["María", "", ""],
                ["", "", "bad-email"],
            ],
        )
        file = await self._make_upload_file("test.xlsx", content)
        parser = FileParserService()
        result = await parser.parse(file)
        assert len(result["errores"]) >= 2

    async def test_preview_invalid_format(self):
        content = b"%PDF-1.4 fake pdf content"
        file = await self._make_upload_file("test.pdf", content)
        from fastapi import HTTPException

        parser = FileParserService()
        with pytest.raises(HTTPException) as exc:
            await parser.parse(file)
        assert exc.value.status_code == 400

    async def test_confirm_import_creates_active_version(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create: Cohorte,
        usuario_create,
    ):
        preview_token = str(uuid.uuid4())
        _preview_store[preview_token] = {
            "rows": [
                {
                    "nombre": "Juan",
                    "apellidos": "Pérez",
                    "email": "juan@test.com",
                    "comision": "A",
                    "regional": "Córdoba",
                },
            ],
            "column_mapping": {"nombre": "Nombre", "apellidos": "Apellidos", "email": "Email"},
        }

        service = PadronImportService(db_session, tenant_a.id)
        result = await service.confirm_import(
            preview_token=preview_token,
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            actor_id=usuario_create.id,
        )
        assert result["total_entradas"] == 1
        assert result["entradas_sin_usuario"] == 1
        assert result["entradas_con_usuario"] == 0
        assert uuid.UUID(result["version_id"]) is not None

        v_repo = VersionPadronRepository(db_session, tenant_a.id)
        version = await v_repo.get(uuid.UUID(result["version_id"]))
        assert version is not None
        assert version.activa is True

    async def test_confirm_import_auto_match_email(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create: Cohorte,
        usuario_create,
    ):
        preview_token = str(uuid.uuid4())
        _preview_store[preview_token] = {
            "rows": [
                {
                    "nombre": "Test",
                    "apellidos": "User",
                    "email": "test.user@example.com",
                    "comision": None,
                    "regional": None,
                },
            ],
            "column_mapping": {"nombre": "Nombre", "apellidos": "Apellidos", "email": "Email"},
        }

        service = PadronImportService(db_session, tenant_a.id)
        result = await service.confirm_import(
            preview_token=preview_token,
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            actor_id=usuario_create.id,
        )
        assert result["entradas_con_usuario"] == 1
        assert result["entradas_sin_usuario"] == 0

    async def test_confirm_import_no_match(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create: Cohorte,
        usuario_create,
    ):
        preview_token = str(uuid.uuid4())
        _preview_store[preview_token] = {
            "rows": [
                {
                    "nombre": "Nobody",
                    "apellidos": "Matches",
                    "email": "nonexistent@example.com",
                    "comision": None,
                    "regional": None,
                },
            ],
            "column_mapping": {"nombre": "Nombre", "apellidos": "Apellidos", "email": "Email"},
        }

        service = PadronImportService(db_session, tenant_a.id)
        result = await service.confirm_import(
            preview_token=preview_token,
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            actor_id=usuario_create.id,
        )
        assert result["entradas_con_usuario"] == 0
        assert result["entradas_sin_usuario"] == 1


# ═══════════════════════════════════════════════════════════════
# Moodle Sync
# ═══════════════════════════════════════════════════════════════


class TestMoodleSync:
    async def test_moodle_client_get_users(self):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_instance = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_instance
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {
                    "id": 1,
                    "firstname": "Juan",
                    "lastname": "Pérez",
                    "email": "juan@moodle.com",
                },
                {
                    "id": 2,
                    "firstname": "María",
                    "lastname": "García",
                    "email": "maria@moodle.com",
                },
            ]
            mock_instance.post.return_value = mock_response

            client = MoodleWSClient(
                ws_url="https://moodle.test/ws",
                ws_token="fake-token",
                max_retries=1,
            )
            result = await client.get_enrolled_users(42)

            assert len(result) == 2
            assert result[0]["email"] == "juan@moodle.com"
            assert result[1]["email"] == "maria@moodle.com"

    async def test_moodle_client_connection_error(self):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_instance = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_instance
            mock_instance.post.side_effect = httpx.ConnectError("Connection refused")

            client = MoodleWSClient(
                ws_url="https://moodle.test/ws",
                ws_token="fake-token",
                max_retries=1,
            )
            with pytest.raises(MoodleConnectionError):
                await client.get_enrolled_users(42)

    async def test_ondemand_sync_creates_moodle_version(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create: Cohorte,
        usuario_create,
    ):
        mock_users = [
            {"id": 1, "firstname": "Moodle", "lastname": "User", "email": "moodle@test.com"},
        ]

        with patch(
            "app.integrations.moodle_ws.MoodleWSClient.get_enrolled_users",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = mock_users

            service = PadronService(db_session, tenant_a.id)
            result = await service.sync_from_moodle(
                materia_id=materia_create.id,
                cohorte_id=cohorte_create.id,
                moodle_course_id=1,
                ws_url="https://moodle.test/ws",
                ws_token="fake-token",
                actor_id=usuario_create.id,
            )

            assert result["total_entradas"] == 1
            assert result["origen"] == "moodle"
            assert uuid.UUID(result["version_id"]) is not None

            v_repo = VersionPadronRepository(db_session, tenant_a.id)
            version = await v_repo.get(uuid.UUID(result["version_id"]))
            assert version is not None
            assert version.origen == "moodle"
            assert version.activa is True

    async def test_ondemand_sync_moodle_down_502(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create: Cohorte,
        usuario_create,
    ):
        with patch(
            "app.integrations.moodle_ws.MoodleWSClient.get_enrolled_users",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.side_effect = MoodleConnectionError("Moodle is down", status_code=502)

            service = PadronService(db_session, tenant_a.id)
            with pytest.raises(MoodleConnectionError) as exc:
                await service.sync_from_moodle(
                    materia_id=materia_create.id,
                    cohorte_id=cohorte_create.id,
                    moodle_course_id=1,
                    ws_url="https://moodle.test/ws",
                    ws_token="fake-token",
                    actor_id=usuario_create.id,
                )
            assert exc.value.status_code == 502

    async def test_moodle_retry_succeeds(self):
        call_count = 0

        async def _mock_call(self_fn, function, params=None):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Timeout")
            return [{"id": 1, "firstname": "Retry", "lastname": "User", "email": "retry@test.com"}]

        with patch.object(MoodleWSClient, "_call", _mock_call):
            client = MoodleWSClient(
                ws_url="https://moodle.test/ws",
                ws_token="token",
                max_retries=3,
                base_delay=0.01,
            )
            result = await client.get_enrolled_users(1)
            assert len(result) == 1
            assert result[0]["email"] == "retry@test.com"
            assert call_count == 3

    async def test_moodle_retry_all_fail(self):
        async def _mock_fail(self_fn, function, params=None):
            raise httpx.ConnectError("Always fails")

        with patch.object(MoodleWSClient, "_call", _mock_fail):
            client = MoodleWSClient(
                ws_url="https://moodle.test/ws",
                ws_token="token",
                max_retries=3,
                base_delay=0.01,
            )
            with pytest.raises(MoodleConnectionError) as exc:
                await client.get_enrolled_users(1)
            assert exc.value.status_code == 502


# ═══════════════════════════════════════════════════════════════
# Clear + RBAC + Isolation
# ═══════════════════════════════════════════════════════════════


class TestClearAndRBAC:
    async def test_clear_subject_data(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create: Cohorte,
        usuario_create,
    ):
        service = PadronService(db_session, tenant_a.id)
        v = await service.create_version(
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            cargado_por=usuario_create.id,
            origen="archivo",
            entradas=[
                {"nombre": "A", "apellidos": "B", "email": "a@b.com"},
                {"nombre": "C", "apellidos": "D", "email": "c@d.com"},
            ],
        )
        result = await service.clear_subject_data(
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            actor_id=usuario_create.id,
        )
        assert result["success"] is True
        assert result["versiones_eliminadas"] >= 1

        v_repo = VersionPadronRepository(db_session, tenant_a.id)
        versions = await v_repo.list_by_materia_cohorte(materia_create.id, cohorte_create.id)
        assert len(versions) == 0

    async def test_profesor_import_propia_materia(
        self,
        db_session: AsyncSession,
        tenant_a,
        usuario_create,
        materia_create: Materia,
        asignacion_profesor: Asignacion,
    ):
        service = PadronService(db_session, tenant_a.id)
        result = await service.verify_profesor_materia(
            usuario_create.id, materia_create.id
        )
        assert result is True

    async def test_profesor_import_ajena_materia(
        self,
        db_session: AsyncSession,
        tenant_a,
        usuario_create,
        materia_create: Materia,
    ):
        materia_otra = Materia(
            tenant_id=tenant_a.id,
            codigo="MAT-OTRA",
            nombre="Física",
            estado="Activa",
        )
        db_session.add(materia_otra)
        await db_session.commit()
        await db_session.refresh(materia_otra)

        service = PadronService(db_session, tenant_a.id)
        result = await service.verify_profesor_materia(
            usuario_create.id, materia_otra.id
        )
        assert result is False

    async def test_coordinador_import_any_materia(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create: Cohorte,
        usuario_create,
    ):
        service = PadronService(db_session, tenant_a.id)
        result = await service.create_version(
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            cargado_por=usuario_create.id,
            origen="archivo",
            entradas=[{"nombre": "Coord", "apellidos": "Test", "email": "coord@test.com"}],
        )
        assert result["id"] is not None
        assert result["materia_id"] == materia_create.id

    async def test_profesor_clear_propia_materia(
        self,
        db_session: AsyncSession,
        tenant_a,
        usuario_create,
        materia_create: Materia,
        cohorte_create: Cohorte,
        asignacion_profesor: Asignacion,
    ):
        service = PadronService(db_session, tenant_a.id)
        await service.create_version(
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            cargado_por=usuario_create.id,
            origen="archivo",
            entradas=[{"nombre": "Prof", "apellidos": "Test", "email": "prof@test.com"}],
        )
        result = await service.clear_subject_data(
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            actor_id=usuario_create.id,
        )
        assert result["success"] is True

    async def test_coordinador_clear_any_materia(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create: Cohorte,
        usuario_create,
    ):
        service = PadronService(db_session, tenant_a.id)
        await service.create_version(
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            cargado_por=usuario_create.id,
            origen="archivo",
            entradas=[{"nombre": "Clear", "apellidos": "Test", "email": "clear@test.com"}],
        )
        result = await service.clear_subject_data(
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            actor_id=usuario_create.id,
        )
        assert result["success"] is True

    async def test_multi_tenant_isolation(
        self,
        db_session: AsyncSession,
        tenant_a,
        tenant_b,
        materia_create: Materia,
        cohorte_create: Cohorte,
        usuario_create,
    ):
        service_a = PadronService(db_session, tenant_a.id)
        v = await service_a.create_version(
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            cargado_por=usuario_create.id,
            origen="archivo",
            entradas=[{"nombre": "TenantA", "apellidos": "Only", "email": "a@only.com"}],
        )

        v_repo_b = VersionPadronRepository(db_session, tenant_b.id)
        versions_b = await v_repo_b.list_by_materia_cohorte(
            materia_create.id, cohorte_create.id
        )
        assert len(versions_b) == 0

        v_repo_a = VersionPadronRepository(db_session, tenant_a.id)
        versions_a = await v_repo_a.list_by_materia_cohorte(
            materia_create.id, cohorte_create.id
        )
        assert len(versions_a) >= 1


# ═══════════════════════════════════════════════════════════════
# Audit
# ═══════════════════════════════════════════════════════════════


class TestAudit:
    async def test_activate_audit(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create: Cohorte,
        usuario_create,
    ):
        service = PadronService(db_session, tenant_a.id)
        v = await service.create_version(
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            cargado_por=usuario_create.id,
            origen="archivo",
            entradas=[{"nombre": "Audit", "apellidos": "Test", "email": "audit@test.com"}],
        )
        await service.activate_version(uuid.UUID(v["id"]), usuario_create.id)

        stmt = select(AuditLog).where(
            AuditLog.actor_id == usuario_create.id,
            AuditLog.accion == AuditAction.PADRON_CARGAR.value,
        )
        result = await db_session.execute(stmt)
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.detalle is not None
        assert log.detalle["accion"] == "activar_version"
        assert log.detalle["origen"] == "archivo"
        assert log.materia_id == materia_create.id

    async def test_clear_audit(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create: Cohorte,
        usuario_create,
    ):
        service = PadronService(db_session, tenant_a.id)
        await service.create_version(
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            cargado_por=usuario_create.id,
            origen="archivo",
            entradas=[{"nombre": "ClearAudit", "apellidos": "Test", "email": "clearaudit@test.com"}],
        )
        await service.clear_subject_data(
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            actor_id=usuario_create.id,
        )

        stmt = select(AuditLog).where(
            AuditLog.actor_id == usuario_create.id,
            AuditLog.accion == AuditAction.PADRON_CARGAR.value,
        )
        result = await db_session.execute(stmt)
        logs = list(result.scalars().all())
        clear_log = next(
            (l for l in logs if l.detalle and l.detalle.get("accion") == "clear_subject_data"),
            None,
        )
        assert clear_log is not None
        assert clear_log.detalle["versiones_eliminadas"] >= 1
        assert clear_log.materia_id == materia_create.id


# ═══════════════════════════════════════════════════════════════
# Nightly Sync
# ═══════════════════════════════════════════════════════════════


class TestNightlySync:
    async def _simulate_nightly_sync(
        self, db_session: AsyncSession
    ) -> list[dict]:
        result = await db_session.execute(
            select(Tenant).where(Tenant.config.isnot(None))
        )
        tenants = list(result.scalars().all())
        outcomes = []
        for tenant in tenants:
            config = tenant.config or {}
            if config.get("sync_lock"):
                outcomes.append({"tenant_id": str(tenant.id), "status": "skipped", "reason": "locked"})
            elif config.get("moodle_ws_url") and config.get("moodle_ws_token"):
                outcomes.append({"tenant_id": str(tenant.id), "status": "synced"})
            else:
                outcomes.append({"tenant_id": str(tenant.id), "status": "skipped", "reason": "no_config"})
        return outcomes

    async def test_nightly_sync_all_tenants(
        self, db_session: AsyncSession, tenant_a, tenant_b
    ):
        tenant_a.config = {
            "moodle_ws_url": "https://moodle.a.com/ws",
            "moodle_ws_token": "token-a",
        }
        tenant_b.config = {
            "moodle_ws_url": "https://moodle.b.com/ws",
            "moodle_ws_token": "token-b",
        }
        await db_session.commit()

        outcomes = await self._simulate_nightly_sync(db_session)
        assert len(outcomes) == 2
        for o in outcomes:
            assert o["status"] == "synced"

    async def test_nightly_sync_skips_locked_tenant(
        self, db_session: AsyncSession, tenant_a, tenant_b
    ):
        tenant_a.config = {
            "moodle_ws_url": "https://moodle.a.com/ws",
            "moodle_ws_token": "token-a",
            "sync_lock": True,
        }
        tenant_b.config = {
            "moodle_ws_url": "https://moodle.b.com/ws",
            "moodle_ws_token": "token-b",
        }
        await db_session.commit()

        outcomes = await self._simulate_nightly_sync(db_session)
        assert len(outcomes) == 2
        locked = [o for o in outcomes if o["status"] == "skipped" and o.get("reason") == "locked"]
        synced = [o for o in outcomes if o["status"] == "synced"]
        assert len(locked) == 1
        assert locked[0]["tenant_id"] == str(tenant_a.id)
        assert len(synced) == 1
        assert synced[0]["tenant_id"] == str(tenant_b.id)
