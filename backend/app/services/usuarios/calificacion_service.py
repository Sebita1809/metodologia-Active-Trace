"""Service for grade import, threshold management, and approval derivation."""
from __future__ import annotations

import io
import uuid
from uuid import UUID

import openpyxl
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_codes import AuditAction
from app.models.domain.calificacion import Calificacion, OrigenCalificacion
from app.models.domain.entrada_padron import EntradaPadron
from app.models.domain.version_padron import VersionPadron
from app.repositories.padron.version_padron_repository import VersionPadronRepository
from app.repositories.usuarios.calificacion_repository import CalificacionRepository
from app.repositories.usuarios.umbral_materia_repository import (
    UmbralMateriaRepository,
)
from app.services.audit.audit_service import audit_record

# In-memory store for preview data
_preview_store: dict[str, dict] = {}


class CalificacionService:
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.calificacion_repo = CalificacionRepository(db, tenant_id)
        self.umbral_repo = UmbralMateriaRepository(db, tenant_id)

    # ── File parsing helpers ────────────────────────────────────

    def _parse_file(self, file: UploadFile) -> dict:
        """Parse xlsx file, detect columns as numeric or textual activities."""
        filename = file.filename or ""
        if not filename.lower().endswith(".xlsx"):
            raise HTTPException(
                status_code=400,
                detail="Formato de archivo no soportado",
            )

        content = file.file.read()
        try:
            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        except Exception:
            raise HTTPException(
                status_code=422,
                detail="Error al leer archivo xlsx",
            )

        ws = wb.active
        if ws is None:
            raise HTTPException(status_code=422, detail="El archivo xlsx no tiene hojas activas")

        rows_iter = ws.iter_rows(values_only=True)
        headers = [str(c).strip() if c is not None else "" for c in next(rows_iter, [])]

        # Detect column types
        actividades = []
        data_rows = []
        for row in rows_iter:
            row_dict = {}
            for i, val in enumerate(row):
                if i < len(headers):
                    row_dict[headers[i]] = val
            data_rows.append(row_dict)

        wb.close()

        # Detect numeric vs textual columns from first few rows
        sample = data_rows[:10] if len(data_rows) > 10 else data_rows
        for h in headers:
            if not h:
                continue
            values = [r.get(h) for r in sample if r.get(h) is not None and str(r.get(h)).strip()]
            if not values:
                continue
            numeric_count = sum(1 for v in values if self._is_numeric(v))
            textual_count = len(values) - numeric_count
            tipo = "numerica" if numeric_count >= textual_count else "textual"
            actividades.append({
                "nombre": h,
                "tipo": tipo,
            })

        # Map rows
        rows = []
        for row in data_rows:
            mapped = {}
            for h in headers:
                val = row.get(h)
                mapped[h] = str(val).strip() if val is not None else ""
            rows.append(mapped)

        return {
            "headers": headers,
            "actividades": actividades,
            "rows": rows,
            "total_rows": len(rows),
        }

    def _is_numeric(self, val) -> bool:
        try:
            float(val)
            return True
        except (ValueError, TypeError):
            return False

    # ── Approval derivation ──────────────────────────────────────

    def _derive_aprobado(
        self,
        nota_numerica: float | None,
        nota_textual: str | None,
        umbral_pct: int,
        valores_aprobatorios: list[str] | None,
    ) -> bool | None:
        """Derive approval status from grade and threshold config.

        Rules (KB E7):
        - Numeric: nota_numerica >= umbral_pct → True else False
        - Textual: nota_textual in valores_aprobatorios → True else False
        - No grade → None
        - Both numeric and textual present: numeric takes precedence
        """
        if nota_numerica is not None:
            try:
                return float(nota_numerica) >= umbral_pct
            except (ValueError, TypeError):
                pass

        if nota_textual and valores_aprobatorios:
            return nota_textual in valores_aprobatorios

        if nota_textual and not valores_aprobatorios:
            return False

        return None

    # ── Import preview ──────────────────────────────────────────

    async def import_preview(
        self,
        file: UploadFile,
        materia_id: UUID,
        cohorte_id: UUID,
    ) -> dict:
        """Phase 1: Parse file and return detected activities for selection."""
        # Validate padron exists
        vp_repo = VersionPadronRepository(self.db, self.tenant_id)
        active_version = await vp_repo.get_active_by_materia_cohorte(
            materia_id, cohorte_id
        )
        if active_version is None:
            raise HTTPException(
                status_code=400,
                detail="No hay padrón activo para esta materia y cohorte",
            )

        parsed = self._parse_file(file)

        preview_token = str(uuid.uuid4())
        _preview_store[preview_token] = {
            "rows": parsed["rows"],
            "headers": parsed["headers"],
            "actividades": parsed["actividades"],
        }

        sample_rows = parsed["rows"][:5] if parsed["rows"] else []

        return {
            "preview_token": preview_token,
            "actividades_detectadas": parsed["actividades"],
            "total_filas": parsed["total_rows"],
            "sample_rows": sample_rows,
        }

    # ── Import confirm ──────────────────────────────────────────

    async def import_confirm(
        self,
        preview_token: str,
        materia_id: UUID,
        cohorte_id: UUID,
        selected_actividades: list[str],
        actor_id: UUID,
        *,
        impersonado_id: UUID | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Phase 2: Confirm import — create Calificacion records."""
        preview_data = _preview_store.pop(preview_token, None)
        if preview_data is None:
            raise HTTPException(
                status_code=404,
                detail="Preview token not found or expired. Please re-upload the file.",
            )

        rows = preview_data["rows"]
        headers = preview_data["headers"]

        # Validate selected actividades exist
        invalid = [a for a in selected_actividades if a not in headers]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Actividades no encontradas: {', '.join(invalid)}",
            )

        # Get active padron entries
        vp_repo = VersionPadronRepository(self.db, self.tenant_id)
        active_version = await vp_repo.get_active_by_materia_cohorte(
            materia_id, cohorte_id
        )
        if active_version is None:
            raise HTTPException(
                status_code=400,
                detail="No hay padrón activo para esta materia y cohorte",
            )

        from app.repositories.padron.entrada_padron_repository import (
            EntradaPadronRepository,
        )
        ep_repo = EntradaPadronRepository(self.db, self.tenant_id)
        entradas = await ep_repo.get_by_version(active_version.id)
        entrada_by_email = {e.email: e for e in entradas}

        calificaciones_creadas = 0
        estudiantes = 0
        processed_emails: set[str] = set()

        def _get_email(r: dict) -> str:
            for k in r:
                if k.lower().strip() == "email":
                    return r[k]
            return ""

        for row in rows:
            email = _get_email(row).strip().lower()
            if not email or email in processed_emails:
                continue
            processed_emails.add(email)

            entrada = entrada_by_email.get(email)
            if entrada is None:
                continue
            estudiantes += 1

            for actividad in selected_actividades:
                raw_val = row.get(actividad, "").strip()
                if not raw_val:
                    continue

                nota_numerica = None
                nota_textual = None
                if self._is_numeric(raw_val):
                    try:
                        nota_numerica = float(raw_val)
                    except ValueError:
                        nota_textual = raw_val
                else:
                    nota_textual = raw_val

                await self.calificacion_repo.create({
                    "entrada_padron_id": entrada.id,
                    "materia_id": materia_id,
                    "actividad": actividad,
                    "nota_numerica": nota_numerica,
                    "nota_textual": nota_textual,
                    "origen": OrigenCalificacion.IMPORTADO,
                })
                calificaciones_creadas += 1

        # Audit
        await audit_record(
            self.db,
            actor_id=actor_id,
            accion=AuditAction.CALIFICACIONES_IMPORTAR,
            tenant_id=self.tenant_id,
            impersonado_id=impersonado_id,
            materia_id=materia_id,
            detalle={"accion": "importar", "actividades": selected_actividades},
            filas_afectadas=calificaciones_creadas,
            ip=ip,
            user_agent=user_agent,
        )

        return {
            "calificaciones_creadas": calificaciones_creadas,
            "estudiantes": estudiantes,
        }

    # ── List ────────────────────────────────────────────────────

    async def list(
        self, materia_id: UUID, cohorte_id: UUID
    ) -> list[dict]:
        """List calificaciones with derived aprobado for a materia+cohorte."""
        vp_repo = VersionPadronRepository(self.db, self.tenant_id)
        active_version = await vp_repo.get_active_by_materia_cohorte(
            materia_id, cohorte_id
        )
        if active_version is None:
            raise HTTPException(
                status_code=400,
                detail="No hay padrón activo para esta materia y cohorte",
            )

        from app.repositories.padron.entrada_padron_repository import (
            EntradaPadronRepository,
        )
        ep_repo = EntradaPadronRepository(self.db, self.tenant_id)
        entradas = await ep_repo.get_by_version(active_version.id)
        entrada_ids = [e.id for e in entradas]

        calificaciones = await self.calificacion_repo.list_by_materia_cohorte(
            materia_id, entrada_ids
        )

        # Get umbral config from first entrada's asignacion
        umbral = None
        entrada_emails = {e.id: e.email for e in entradas}
        if entrada_ids:
            from app.models.domain.asignacion import Asignacion
            stmt = select(Asignacion.id).where(
                Asignacion.tenant_id == self.tenant_id,
                Asignacion.materia_id == materia_id,
                Asignacion.deleted_at.is_(None),
            )
            result = await self.db.execute(stmt)
            asignacion_ids = [row[0] for row in result.all()]
            if asignacion_ids:
                umbral = await self.umbral_repo.get_by_asignacion(asignacion_ids[0])

        umbral_pct = umbral.umbral_pct if umbral else 60
        valores = umbral.valores_aprobatorios if umbral else []

        result = []
        for c in calificaciones:
            aprobado = self._derive_aprobado(
                float(c.nota_numerica) if c.nota_numerica is not None else None,
                c.nota_textual,
                umbral_pct,
                valores,
            )
            result.append({
                "id": str(c.id),
                "tenant_id": str(c.tenant_id),
                "entrada_padron_id": str(c.entrada_padron_id),
                "materia_id": str(c.materia_id),
                "actividad": c.actividad,
                "nota_numerica": float(c.nota_numerica) if c.nota_numerica is not None else None,
                "nota_textual": c.nota_textual,
                "origen": c.origen.value if hasattr(c.origen, "value") else str(c.origen),
                "importado_at": c.importado_at.isoformat() if c.importado_at else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                "aprobado": aprobado,
            })

        return result

    # ── Clear ───────────────────────────────────────────────────

    async def clear(
        self,
        materia_id: UUID,
        cohorte_id: UUID,
        actor_id: UUID,
        *,
        impersonado_id: UUID | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Hard-delete all calificaciones for a materia+cohorte."""
        vp_repo = VersionPadronRepository(self.db, self.tenant_id)
        active_version = await vp_repo.get_active_by_materia_cohorte(
            materia_id, cohorte_id
        )
        if active_version is None:
            raise HTTPException(
                status_code=400,
                detail="No hay padrón activo para esta materia y cohorte",
            )

        from app.repositories.padron.entrada_padron_repository import (
            EntradaPadronRepository,
        )
        ep_repo = EntradaPadronRepository(self.db, self.tenant_id)
        entradas = await ep_repo.get_by_version(active_version.id)
        entrada_ids = [e.id for e in entradas]

        calificaciones = await self.calificacion_repo.list_by_materia_cohorte(
            materia_id, entrada_ids
        )
        count = len(calificaciones)

        if count > 0:
            await self.calificacion_repo.hard_delete_by_materia(materia_id, entrada_ids)

        # Audit
        await audit_record(
            self.db,
            actor_id=actor_id,
            accion=AuditAction.CALIFICACIONES_IMPORTAR,
            tenant_id=self.tenant_id,
            impersonado_id=impersonado_id,
            materia_id=materia_id,
            detalle={"accion": "clear", "calificaciones_eliminadas": count},
            filas_afectadas=count,
            ip=ip,
            user_agent=user_agent,
        )

        return {"success": True, "calificaciones_eliminadas": count}

    # ── Umbral ──────────────────────────────────────────────────

    async def get_umbral(self, asignacion_id: UUID) -> dict:
        umbral = await self.umbral_repo.get_by_asignacion(asignacion_id)
        if umbral is None:
            raise HTTPException(
                status_code=404,
                detail="Umbral not found for this asignacion",
            )
        return {
            "id": str(umbral.id),
            "asignacion_id": str(umbral.asignacion_id),
            "materia_id": str(umbral.materia_id),
            "umbral_pct": umbral.umbral_pct,
            "valores_aprobatorios": umbral.valores_aprobatorios or [],
        }

    async def update_umbral(self, data: dict) -> dict:
        materia_id = UUID(data["materia_id"])
        asignacion_id = UUID(data["asignacion_id"])

        # Try to find existing umbral
        umbral = await self.umbral_repo.get_by_asignacion(asignacion_id)

        if umbral is None:
            umbral = await self.umbral_repo.create({
                "asignacion_id": asignacion_id,
                "materia_id": materia_id,
                "umbral_pct": data.get("umbral_pct", 60),
                "valores_aprobatorios": data.get("valores_aprobatorios", []),
            })
        else:
            update_data = {}
            if "umbral_pct" in data:
                update_data["umbral_pct"] = data["umbral_pct"]
            if "valores_aprobatorios" in data:
                update_data["valores_aprobatorios"] = data["valores_aprobatorios"]
            if update_data:
                umbral = await self.umbral_repo.update_config(umbral.id, update_data)
                if umbral is None:
                    raise HTTPException(status_code=404, detail="Umbral not found")

        return {
            "id": str(umbral.id),
            "asignacion_id": str(umbral.asignacion_id),
            "materia_id": str(umbral.materia_id),
            "umbral_pct": umbral.umbral_pct,
            "valores_aprobatorios": umbral.valores_aprobatorios or [],
        }
