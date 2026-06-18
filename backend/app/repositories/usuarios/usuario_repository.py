"""Repository for Usuario CRUD with tenant scope."""
import hashlib
import hmac
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.domain.usuario import Usuario
from app.repositories.base import BaseRepository


class UsuarioRepository(BaseRepository[Usuario]):
    """Usuario CRUD with tenant scope and email hash lookup."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(db, tenant_id, Usuario)

    async def get_by_email(self, email: str) -> Usuario | None:
        """Find a user by email using the deterministic email_hash."""
        email_hash = self._compute_email_hash(email)
        return await self.get_by_email_hash(email_hash)

    async def get_by_email_hash(self, email_hash: str) -> Usuario | None:
        """Find a user by pre-computed email hash."""
        stmt = select(Usuario).where(
            Usuario.tenant_id == self.tenant_id,
            Usuario.email_hash == email_hash,
            Usuario.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_email(self, email: str) -> bool:
        """Check if a user with this email exists in the tenant."""
        email_hash = self._compute_email_hash(email)
        stmt = select(Usuario.id).where(
            Usuario.tenant_id == self.tenant_id,
            Usuario.email_hash == email_hash,
            Usuario.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_by_ids(self, ids: list[uuid.UUID]) -> list[Usuario]:
        """Fetch multiple users by IDs (scoped to tenant)."""
        stmt = select(Usuario).where(
            Usuario.tenant_id == self.tenant_id,
            Usuario.id.in_(ids),
            Usuario.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def _compute_email_hash(email: str) -> str:
        """Compute deterministic HMAC-SHA256 hash of an email."""
        key = get_settings().ENCRYPTION_KEY.encode("utf-8")
        normalized = email.lower().strip().encode("utf-8")
        return hmac.new(key, normalized, hashlib.sha256).hexdigest()
