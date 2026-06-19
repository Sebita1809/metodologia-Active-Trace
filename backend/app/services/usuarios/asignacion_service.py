"""Business logic for Asignacion CRUD with validation rules."""
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import EstadoGenerico
from app.repositories.usuarios.asignacion_repository import AsignacionRepository
from app.repositories.usuarios.umbral_materia_repository import UmbralMateriaRepository
from app.repositories.usuarios.usuario_repository import UsuarioRepository


class AsignacionService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = AsignacionRepository(db, tenant_id)
        self.usuario_repo = UsuarioRepository(db, tenant_id)
        self.umbral_repo = UmbralMateriaRepository(db, tenant_id)

    async def create(self, data: dict) -> dict:
        # Validate user exists and is active
        usuario = await self.usuario_repo.get(data["usuario_id"])
        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuario not found")
        if usuario.estado != EstadoGenerico.ACTIVA.value:
            raise HTTPException(
                status_code=422, detail="Cannot assign to inactive user"
            )

        # Validate date range
        desde = data["desde"]
        hasta = data.get("hasta")
        if hasta and desde > hasta:
            raise HTTPException(
                status_code=422,
                detail="desde must be before or equal to hasta",
            )

        # Validate responsable_id if provided
        responsable_id = data.get("responsable_id")
        if responsable_id:
            responsable = await self.usuario_repo.get(responsable_id)
            if responsable is None:
                raise HTTPException(
                    status_code=422,
                    detail="Responsable not found in this tenant",
                )

        create_data = {
            "usuario_id": data["usuario_id"],
            "rol": data["rol"],
            "materia_id": data.get("materia_id"),
            "carrera_id": data.get("carrera_id"),
            "cohorte_id": data.get("cohorte_id"),
            "comisiones": data.get("comisiones") or [],
            "responsable_id": responsable_id,
            "desde": desde,
            "hasta": hasta,
        }

        entity = await self.repo.create(create_data)

        # Auto-create UmbralMateria for teaching roles
        rol = data["rol"]
        materia_id = data.get("materia_id")
        if rol in ("PROFESOR", "TUTOR") and materia_id:
            await self.umbral_repo.create_default(entity.id, materia_id)

        return self._to_response(entity)

    async def get(self, id: uuid.UUID) -> dict:
        entity = await self.repo.get(id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Asignacion not found")
        return self._to_response(entity)

    async def list(
        self,
        usuario_id: uuid.UUID | None = None,
        materia_id: uuid.UUID | None = None,
        solo_vigentes: bool = False,
    ) -> list[dict]:
        if usuario_id:
            if solo_vigentes:
                entities = await self.repo.list_vigentes_por_usuario(usuario_id)
            else:
                entities = await self.repo.list_by_usuario(usuario_id)
        elif materia_id:
            entities = await self.repo.list_by_materia(materia_id)
        elif solo_vigentes:
            entities = await self.repo.list_vigentes()
        else:
            entities = await self.repo.list()
        return [self._to_response(e) for e in entities]

    async def update(self, id: uuid.UUID, data: dict) -> dict:
        entity = await self.repo.get(id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Asignacion not found")

        update_data = {}
        for field in ("rol", "materia_id", "carrera_id", "cohorte_id",
                      "comisiones", "desde", "hasta"):
            if field in data:
                update_data[field] = data[field]

        if "responsable_id" in data:
            responsable_id = data["responsable_id"]
            if responsable_id:
                responsable = await self.usuario_repo.get(responsable_id)
                if responsable is None:
                    raise HTTPException(
                        status_code=422,
                        detail="Responsable not found in this tenant",
                    )
            update_data["responsable_id"] = responsable_id

        updated = await self.repo.update(id, update_data)
        if updated is None:
            raise HTTPException(status_code=404, detail="Asignacion not found")
        return self._to_response(updated)

    async def delete(self, id: uuid.UUID) -> None:
        entity = await self.repo.get(id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Asignacion not found")
        await self.repo.delete(id)

    def _to_response(self, entity) -> dict:
        return {
            "id": entity.id,
            "tenant_id": entity.tenant_id,
            "usuario_id": entity.usuario_id,
            "rol": entity.rol,
            "materia_id": entity.materia_id,
            "carrera_id": entity.carrera_id,
            "cohorte_id": entity.cohorte_id,
            "comisiones": entity.comisiones,
            "responsable_id": entity.responsable_id,
            "desde": entity.desde,
            "hasta": entity.hasta,
            "estado_vigencia": entity.estado_vigencia,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
        }
