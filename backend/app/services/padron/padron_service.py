"""Domain service for padron management operations."""
from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_codes import AuditAction
from app.models.domain.version_padron import VersionPadron
from app.repositories.estructura.materia_repository import MateriaRepository
from app.repositories.estructura.cohorte_repository import CohorteRepository
from app.repositories.padron.entrada_padron_repository import EntradaPadronRepository
from app.repositories.padron.version_padron_repository import VersionPadronRepository
from app.repositories.usuarios.asignacion_repository import AsignacionRepository
from app.repositories.usuarios.usuario_repository import UsuarioRepository
from app.services.audit.audit_service import audit_record


class PadronService:
    """Service for managing padron versions and entries."""

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.version_repo = VersionPadronRepository(db, tenant_id)
        self.entrada_repo = EntradaPadronRepository(db, tenant_id)
        self.materia_repo = MateriaRepository(db, tenant_id)
        self.cohorte_repo = CohorteRepository(db, tenant_id)
        self.asignacion_repo = AsignacionRepository(db, tenant_id)
        self.usuario_repo = UsuarioRepository(db, tenant_id)

    async def create_version(
        self,
        materia_id: UUID,
        cohorte_id: UUID,
        cargado_por: UUID,
        origen: str,
        entradas: list[dict],
    ) -> dict:
        """Create a new VersionPadron with EntradaPadron entries (not active by default)."""
        materia = await self.materia_repo.get(materia_id)
        if materia is None:
            raise HTTPException(status_code=404, detail="Materia not found")

        cohorte = await self.cohorte_repo.get(cohorte_id)
        if cohorte is None:
            raise HTTPException(status_code=404, detail="Cohorte not found")

        if origen not in ("archivo", "moodle"):
            raise HTTPException(status_code=422, detail="origen must be 'archivo' or 'moodle'")

        if not entradas:
            raise HTTPException(status_code=422, detail="At least one entrada is required")

        version_data = {
            "materia_id": materia_id,
            "cohorte_id": cohorte_id,
            "activa": False,
            "origen": origen,
            "cargado_por": cargado_por,
        }
        version = await self.version_repo.create(version_data)

        entrada_data_list = []
        for e in entradas:
            entrada_data = {
                "version_id": version.id,
                "usuario_id": e.get("usuario_id"),
                "nombre": e["nombre"],
                "apellidos": e["apellidos"],
                "email": e["email"],
                "comision": e.get("comision"),
                "regional": e.get("regional"),
            }
            entrada_data_list.append(entrada_data)

        entradas_creadas = await self.entrada_repo.bulk_create(entrada_data_list)

        return self._version_to_response(version, len(entradas_creadas))

    async def activate_version(self, version_id: UUID, actor_id: UUID) -> dict:
        """Activate a version, deactivating any previous active version."""
        version = await self.version_repo.get(version_id)
        if version is None:
            raise HTTPException(status_code=404, detail="Version not found")

        if version.activa:
            result = self._version_to_response(version)
            return result

        await self.version_repo.deactivate_previous_active(version.materia_id, version.cohorte_id)

        activated = await self.version_repo.activate(version_id)
        if activated is None:
            raise HTTPException(status_code=500, detail="Failed to activate version")

        await audit_record(
            self.db, actor_id, AuditAction.PADRON_CARGAR,
            tenant_id=self.tenant_id,
            materia_id=version.materia_id,
            detalle={
                "accion": "activar_version",
                "version_id": str(version_id),
                "origen": version.origen,
            },
        )

        return self._version_to_response(activated)

    async def get_active_version(self, materia_id: UUID, cohorte_id: UUID) -> dict:
        """Get the active VersionPadron with all EntradaPadron entries."""
        version = await self.version_repo.get_active_by_materia_cohorte(materia_id, cohorte_id)
        if version is None:
            raise HTTPException(status_code=404, detail="No active version found for this materia+cohorte")

        entradas = await self.entrada_repo.get_by_version(version.id)
        return {
            **self._version_to_response(version, len(entradas)),
            "entradas": [self._entrada_to_response(e) for e in entradas],
        }

    async def list_versions(self, materia_id: UUID, cohorte_id: UUID) -> list[dict]:
        """List all versions for a materia+cohorte, ordered by date desc."""
        versions = await self.version_repo.list_by_materia_cohorte(materia_id, cohorte_id)
        result = []
        for v in versions:
            count = await self.entrada_repo.count_by_version(v.id)
            result.append(self._version_to_response(v, count))
        return result

    async def clear_subject_data(self, materia_id: UUID, cohorte_id: UUID, actor_id: UUID) -> dict:
        """Hard delete all padron data for a materia+cohorte (F1.5, RN-04)."""
        versions = await self.version_repo.list_by_materia_cohorte(materia_id, cohorte_id)
        version_ids = [v.id for v in versions]

        for vid in version_ids:
            await self.entrada_repo.hard_delete_by_version(vid)

        count = await self.version_repo.hard_delete_by_materia_cohorte(materia_id, cohorte_id)

        await audit_record(
            self.db, actor_id, AuditAction.PADRON_CARGAR,
            tenant_id=self.tenant_id,
            materia_id=materia_id,
            detalle={
                "accion": "clear_subject_data",
                "cohorte_id": str(cohorte_id),
                "versiones_eliminadas": count,
            },
            filas_afectadas=count,
        )

        return {
            "success": True,
            "materia_id": str(materia_id),
            "cohorte_id": str(cohorte_id),
            "versiones_eliminadas": count,
        }

    async def sync_from_moodle(
        self,
        materia_id: UUID,
        cohorte_id: UUID,
        moodle_course_id: int,
        ws_url: str,
        ws_token: str,
        actor_id: UUID,
    ) -> dict:
        """Sync padron from Moodle for a materia+cohorte.

        Creates a new VersionPadron with origen="moodle" from Moodle enrolled users.
        """
        from app.integrations.moodle_ws import MoodleWSClient

        client = MoodleWSClient(ws_url=ws_url, ws_token=ws_token)
        moodle_users = await client.get_enrolled_users(moodle_course_id)

        entradas = []
        for mu in moodle_users:
            entradas.append({
                "nombre": mu.get("firstname", ""),
                "apellidos": mu.get("lastname", ""),
                "email": mu.get("email", ""),
                "comision": None,
                "regional": None,
                "usuario_id": None,
            })

        result = await self.create_version(
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=actor_id,
            origen="moodle",
            entradas=entradas,
        )

        activated = await self.activate_version(UUID(result["id"]), actor_id)

        return {
            "version_id": activated["id"],
            "total_entradas": len(entradas),
            "origen": "moodle",
        }

    async def verify_profesor_materia(self, usuario_id: UUID, materia_id: UUID) -> bool:
        """Check if a PROFESOR is assigned to a materia (for scope 'propio' guard)."""
        asignaciones = await self.asignacion_repo.list_vigentes_por_usuario(usuario_id)
        return any(
            a.materia_id == materia_id and a.rol == "PROFESOR"
            for a in asignaciones
        )

    def _version_to_response(self, v: VersionPadron, total_entradas: int | None = None) -> dict:
        return {
            "id": v.id,
            "tenant_id": v.tenant_id,
            "materia_id": v.materia_id,
            "cohorte_id": v.cohorte_id,
            "activa": v.activa,
            "origen": v.origen,
            "cargado_por": v.cargado_por,
            "cargado_at": v.cargado_at,
            "total_entradas": total_entradas,
            "created_at": v.created_at,
            "updated_at": v.updated_at,
        }

    def _entrada_to_response(self, e) -> dict:
        return {
            "id": e.id,
            "version_id": e.version_id,
            "usuario_id": e.usuario_id,
            "nombre": e.nombre,
            "apellidos": e.apellidos,
            "email": e.email,
            "comision": e.comision,
            "regional": e.regional,
        }
