"""Business logic for Carrera CRUD with tenant scope."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.estructura.carrera_repository import CarreraRepository
from app.repositories.estructura.cohorte_repository import CohorteRepository


class CarreraService:
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = CarreraRepository(db, tenant_id)
        self.cohorte_repo = CohorteRepository(db, tenant_id)

    async def create(self, data: dict):
        existing = await self.repo.list(codigo=data["codigo"])
        if existing:
            raise HTTPException(status_code=409, detail="Código already exists")
        return await self.repo.create(data)

    async def get(self, id: UUID):
        entity = await self.repo.get(id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Carrera not found")
        return entity

    async def list(self):
        return await self.repo.list()

    async def update(self, id: UUID, data: dict):
        entity = await self.repo.get(id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Carrera not found")

        if data.get("estado") == "Inactiva":
            active_cohorts = await self.cohorte_repo.count_activas_por_carrera(id)
            if active_cohorts > 0:
                raise HTTPException(
                    status_code=409,
                    detail="Cannot deactivate carrera with active cohorts",
                )

        return await self.repo.update(id, data)

    async def delete(self, id: UUID):
        entity = await self.repo.get(id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Carrera not found")

        active_cohorts = await self.cohorte_repo.count_activas_por_carrera(id)
        if active_cohorts > 0:
            raise HTTPException(
                status_code=409,
                detail="Cannot delete carrera with active cohorts",
            )

        await self.repo.delete(id)
