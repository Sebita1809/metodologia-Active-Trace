"""Service for file-based padron import (preview + confirm flow)."""
from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_codes import AuditAction
from app.repositories.usuarios.usuario_repository import UsuarioRepository
from app.services.audit.audit_service import audit_record
from app.services.padron.file_parser_service import FileParserService

# In-memory store for preview data (temporary — will be replaced by Redis/cache in production)
_preview_store: dict[str, dict] = {}


class PadronImportService:
    """Service for two-phase file import: preview → confirm."""

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.parser = FileParserService()
        self.usuario_repo = UsuarioRepository(db, tenant_id)

    async def preview_file(self, file: UploadFile) -> dict:
        """Phase 1: Parse file and return preview without persisting.

        Returns preview data with a preview_token that the client uses in confirm step.
        """
        parsed = await self.parser.parse(file)

        # Check for missing columns
        if parsed.get("columnas_faltantes"):
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "Faltan columnas requeridas",
                    "columnas_faltantes": parsed["columnas_faltantes"],
                    "columnas_detectadas": parsed.get("column_mapping", {}),
                },
            )

        # Generate preview token (UUID)
        preview_token = str(uuid.uuid4())

        # Store parsed data temporarily (will be consumed by confirm)
        _preview_store[preview_token] = {
            "rows": parsed.get("rows", []),
            "column_mapping": parsed.get("column_mapping", {}),
        }

        return {
            "preview_token": preview_token,
            "column_mapping": parsed.get("column_mapping", {}),
            "total_rows": parsed.get("total_rows", 0),
            "sample_rows": parsed.get("sample_rows", []),
            "errores": parsed.get("errores", []),
            "columnas_faltantes": parsed.get("columnas_faltantes", []),
        }

    async def confirm_import(
        self,
        preview_token: str,
        materia_id: UUID,
        cohorte_id: UUID,
        actor_id: UUID,
    ) -> dict:
        """Phase 2: Confirm import — persist VersionPadron from preview data.

        Auto-matches email to existing Usuario records. Delegates to PadronService
        for domain logic (validation, deactivate previous, activate, audit).
        """
        # Retrieve and consume preview data
        preview_data = _preview_store.pop(preview_token, None)
        if preview_data is None:
            raise HTTPException(
                status_code=404,
                detail="Preview token not found or expired. Please re-upload the file.",
            )

        rows = preview_data["rows"]

        # Auto-match usuarios by email
        entradas_con_match = 0
        entradas_sin_match = 0
        entradas: list[dict] = []

        for row in rows:
            email = row.get("email", "").strip().lower()
            usuario = await self.usuario_repo.get_by_email(email) if email else None
            entradas.append({
                "nombre": row.get("nombre", ""),
                "apellidos": row.get("apellidos", ""),
                "email": email,
                "comision": row.get("comision"),
                "regional": row.get("regional"),
                "usuario_id": usuario.id if usuario else None,
            })
            if usuario is not None:
                entradas_con_match += 1
            else:
                entradas_sin_match += 1

        # Use PadronService for domain logic (lazy import to avoid circular dependency)
        from app.services.padron.padron_service import PadronService

        padron_service = PadronService(self.db, self.tenant_id)

        result = await padron_service.create_version(
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=actor_id,
            origen="archivo",
            entradas=entradas,
        )

        # Auto-activate (handles deactivate previous + audit)
        activated = await padron_service.activate_version(
            UUID(result["id"]), actor_id
        )

        return {
            "version_id": activated["id"],
            "total_entradas": len(entradas),
            "entradas_con_usuario": entradas_con_match,
            "entradas_sin_usuario": entradas_sin_match,
        }
