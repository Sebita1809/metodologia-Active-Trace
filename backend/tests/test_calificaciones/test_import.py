"""Tests for grade import functionality (C-10)."""
from __future__ import annotations

import uuid
from io import BytesIO

import pytest
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.calificacion import Calificacion, OrigenCalificacion
from app.models.domain.materia import Materia
from app.repositories.usuarios.calificacion_repository import CalificacionRepository
from app.services.usuarios.calificacion_service import (
    CalificacionService,
    _preview_store,
)
from app.core.audit_codes import AuditAction

pytestmark = pytest.mark.asyncio


class TestDerivacionAprobado:
    """Test approval derivation via CalificacionService."""

    async def test_service_derive_numeric_above(
        self, db_session: AsyncSession, tenant_a
    ):
        service = CalificacionService(db_session, tenant_a.id)
        result = service._derive_aprobado(75, None, 60, [])
        assert result is True

    async def test_service_derive_numeric_below(
        self, db_session: AsyncSession, tenant_a
    ):
        service = CalificacionService(db_session, tenant_a.id)
        result = service._derive_aprobado(45, None, 60, [])
        assert result is False

    async def test_service_derive_textual_match(
        self, db_session: AsyncSession, tenant_a
    ):
        service = CalificacionService(db_session, tenant_a.id)
        result = service._derive_aprobado(None, "Aprobado", 60, ["Aprobado"])
        assert result is True

    async def test_service_derive_textual_no_match(
        self, db_session: AsyncSession, tenant_a
    ):
        service = CalificacionService(db_session, tenant_a.id)
        result = service._derive_aprobado(None, "Regular", 60, ["Aprobado"])
        assert result is False

    async def test_service_derive_no_grade(
        self, db_session: AsyncSession, tenant_a
    ):
        service = CalificacionService(db_session, tenant_a.id)
        result = service._derive_aprobado(None, None, 60, [])
        assert result is None


class TestCalificacionCRUD:
    async def test_create_calificacion(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        entrada_padron_data,
    ):
        repo = CalificacionRepository(db_session, tenant_a.id)
        calif = await repo.create({
            "entrada_padron_id": entrada_padron_data[0].id,
            "materia_id": materia_create.id,
            "actividad": "Examen Parcial",
            "nota_numerica": 85,
            "origen": OrigenCalificacion.IMPORTADO,
        })
        assert calif.id is not None
        assert calif.actividad == "Examen Parcial"
        assert float(calif.nota_numerica) == 85
        assert calif.origen.value == "Importado"

    async def test_list_by_materia_cohorte(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        entrada_padron_data,
        calificacion_data,
    ):
        repo = CalificacionRepository(db_session, tenant_a.id)
        entrada_ids = [e.id for e in entrada_padron_data]
        results = await repo.list_by_materia_cohorte(materia_create.id, entrada_ids)
        assert len(results) >= 1
        assert all(c.materia_id == materia_create.id for c in results)

    async def test_hard_delete_by_materia(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        entrada_padron_data,
        calificacion_data,
    ):
        repo = CalificacionRepository(db_session, tenant_a.id)
        entrada_ids = [e.id for e in entrada_padron_data]
        await repo.hard_delete_by_materia(materia_create.id, entrada_ids)
        remaining = await repo.list_by_materia_cohorte(materia_create.id, entrada_ids)
        assert len(remaining) == 0

    async def test_multi_tenant_isolation(
        self,
        db_session: AsyncSession,
        tenant_a,
        tenant_b,
        materia_create: Materia,
        entrada_padron_data,
        calificacion_data,
    ):
        repo_a = CalificacionRepository(db_session, tenant_a.id)
        repo_b = CalificacionRepository(db_session, tenant_b.id)
        entrada_ids = [e.id for e in entrada_padron_data]
        results_a = await repo_a.list_by_materia_cohorte(materia_create.id, entrada_ids)
        results_b = await repo_b.list_by_materia_cohorte(materia_create.id, entrada_ids)
        assert len(results_a) >= 1
        assert len(results_b) == 0


class TestImportFlow:
    async def _make_xlsx(self, headers: list[str], rows: list[list]) -> bytes:
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

    async def test_preview_rejects_invalid_format(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create,
        version_padron_activa,
    ):
        service = CalificacionService(db_session, tenant_a.id)
        content = b"%PDF-1.4 fake pdf content"
        file = await self._make_upload_file("test.pdf", content)
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await service.import_preview(file, materia_create.id, cohorte_create.id)
        assert exc.value.status_code == 400
        assert "no soportado" in exc.value.detail.lower()

    async def test_preview_rejects_no_active_padron(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create,
    ):
        service = CalificacionService(db_session, tenant_a.id)
        content = await self._make_xlsx(
            ["Nombre", "Apellidos", "Email"],
            [["Juan", "Pérez", "juan@test.com"]],
        )
        file = await self._make_upload_file("test.xlsx", content)
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await service.import_preview(file, materia_create.id, cohorte_create.id)
        assert exc.value.status_code == 400
        assert "padrón activo" in exc.value.detail.lower()

    async def test_preview_detects_actividades(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create,
        version_padron_activa,
    ):
        service = CalificacionService(db_session, tenant_a.id)
        content = await self._make_xlsx(
            ["Nombre", "Apellidos", "Email", "Examen Parcial", "Trabajo Práctico"],
            [
                ["Juan", "Pérez", "juan@test.com", "85", "Aprobado"],
                ["María", "García", "maria@test.com", "70", "Satisfactorio"],
            ],
        )
        file = await self._make_upload_file("test.xlsx", content)
        result = await service.import_preview(file, materia_create.id, cohorte_create.id)
        assert "preview_token" in result
        assert "actividades_detectadas" in result
        assert result["total_filas"] == 2
        nombres = [a["nombre"] for a in result["actividades_detectadas"]]
        assert "Examen Parcial" in nombres
        assert "Trabajo Práctico" in nombres

    async def test_confirm_creates_calificaciones(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create,
        version_padron_activa,
        entrada_padron_data,
        usuario_create,
    ):
        service = CalificacionService(db_session, tenant_a.id)
        preview_token = str(uuid.uuid4())
        _preview_store[preview_token] = {
            "rows": [
                {
                    "Nombre": "Juan",
                    "Apellidos": "Pérez",
                    "Email": "juan.perez@example.com",
                    "Examen Parcial": "85",
                    "Trabajo Práctico": "Aprobado",
                },
                {
                    "Nombre": "María",
                    "Apellidos": "García",
                    "Email": "maria.garcia@example.com",
                    "Examen Parcial": "70",
                    "Trabajo Práctico": "Satisfactorio",
                },
            ],
            "headers": ["Nombre", "Apellidos", "Email", "Examen Parcial", "Trabajo Práctico"],
            "actividades": [
                {"nombre": "Examen Parcial", "tipo": "numerica"},
                {"nombre": "Trabajo Práctico", "tipo": "textual"},
            ],
        }

        result = await service.import_confirm(
            preview_token=preview_token,
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            selected_actividades=["Examen Parcial", "Trabajo Práctico"],
            actor_id=usuario_create.id,
        )
        assert result["calificaciones_creadas"] >= 2
        assert result["estudiantes"] >= 1

    async def test_confirm_rejects_expired_token(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create,
        usuario_create,
    ):
        service = CalificacionService(db_session, tenant_a.id)
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await service.import_confirm(
                preview_token="non-existent-token",
                materia_id=materia_create.id,
                cohorte_id=cohorte_create.id,
                selected_actividades=["Examen"],
                actor_id=usuario_create.id,
            )
        assert exc.value.status_code == 404

    async def test_clear_calificaciones(
        self,
        db_session: AsyncSession,
        tenant_a,
        materia_create: Materia,
        cohorte_create,
        version_padron_activa,
        entrada_padron_data,
        calificacion_data,
        usuario_create,
    ):
        service = CalificacionService(db_session, tenant_a.id)
        result = await service.clear(
            materia_id=materia_create.id,
            cohorte_id=cohorte_create.id,
            actor_id=usuario_create.id,
        )
        assert result["success"] is True
        assert result["calificaciones_eliminadas"] >= 1
