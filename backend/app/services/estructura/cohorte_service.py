"""Business logic for Cohorte CRUD with tenant scope."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.estructura.carrera_repository import CarreraRepository
from app.repositories.estructura.cohorte_repository import CohorteRepository


class CohorteService:
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = CohorteRepository(db, tenant_id)
        self.carrera_repo = CarreraRepository(db, tenant_id)

    async def create(self, data: dict):
        carrera = await self.carrera_repo.get(data["carrera_id"])
        if carrera is None or carrera.estado != "Activa":
            raise HTTPException(
                status_code=422, detail="Carrera not found or not active"
            )

        existing = await self.repo.list(
            carrera_id=data["carrera_id"], nombre=data["nombre"]
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail="Nombre already exists for this carrera",
            )

        return await self.repo.create(data)

    async def get(self, id: UUID):
        entity = await self.repo.get(id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Cohorte not found")
        return entity

    async def list(self, carrera_id: UUID | None = None):
        if carrera_id is not None:
            return await self.repo.list(carrera_id=carrera_id)
        return await self.repo.list()

    async def update(self, id: UUID, data: dict):
        entity = await self.repo.get(id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Cohorte not found")

        if "carrera_id" in data and data["carrera_id"] != entity.carrera_id:
            carrera = await self.carrera_repo.get(data["carrera_id"])
            if carrera is None or carrera.estado != "Activa":
                raise HTTPException(
                    status_code=422, detail="New carrera not found or not active"
                )

        return await self.repo.update(id, data)

    async def delete(self, id: UUID):
        entity = await self.repo.get(id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Cohorte not found")
        await self.repo.delete(id)
