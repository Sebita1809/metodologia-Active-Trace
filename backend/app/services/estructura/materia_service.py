"""Business logic for Materia CRUD with tenant scope."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.estructura.materia_repository import MateriaRepository


class MateriaService:
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = MateriaRepository(db, tenant_id)

    async def create(self, data: dict):
        existing = await self.repo.list(codigo=data["codigo"])
        if existing:
            raise HTTPException(status_code=409, detail="Código already exists")
        return await self.repo.create(data)

    async def get(self, id: UUID):
        entity = await self.repo.get(id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Materia not found")
        return entity

    async def list(self):
        return await self.repo.list()

    async def update(self, id: UUID, data: dict):
        entity = await self.repo.get(id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Materia not found")
        return await self.repo.update(id, data)

    async def delete(self, id: UUID):
        entity = await self.repo.get(id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Materia not found")
        await self.repo.delete(id)
