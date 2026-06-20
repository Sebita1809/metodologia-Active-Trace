"""
app/repositories/acknowledgment_aviso_repository.py — AcknowledgmentAvisoRepository.

Extends BaseRepository[AcknowledgmentAviso] with:
  - create_ack: creates an acknowledgment record, raises LookupError on duplicate
  - get_by_aviso_usuario: find existing ack for a user/aviso pair

Tenant isolation is inherited from BaseRepository (mandatory).

Implemented: C-15 (avisos-y-acknowledgment)
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acknowledgment_aviso import AcknowledgmentAviso
from app.repositories.base import BaseRepository


class AcknowledgmentAvisoRepository(BaseRepository[AcknowledgmentAviso]):
    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(
            model=AcknowledgmentAviso,
            session=session,
            tenant_id=tenant_id,
        )

    async def create_ack(
        self,
        aviso_id: uuid.UUID,
        usuario_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> AcknowledgmentAviso:
        """Create an acknowledgment record.

        Raises
        ------
        LookupError
            When the (aviso_id, usuario_id) combination already exists
            (duplicate acknowledgment attempt).
        """
        ack = AcknowledgmentAviso(
            aviso_id=aviso_id,
            usuario_id=usuario_id,
            tenant_id=tenant_id,
        )
        try:
            self._session.add(ack)
            await self._session.flush()
            await self._session.refresh(ack)
            return ack
        except IntegrityError as exc:
            await self._session.rollback()
            raise LookupError(
                f"Acknowledgment already exists for aviso_id={aviso_id} usuario_id={usuario_id}"
            ) from exc

    async def get_by_aviso_usuario(
        self,
        aviso_id: uuid.UUID,
        usuario_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> AcknowledgmentAviso | None:
        """Return the acknowledgment for the given aviso/usuario pair, or None."""
        stmt = (
            select(AcknowledgmentAviso)
            .where(AcknowledgmentAviso.aviso_id == aviso_id)
            .where(AcknowledgmentAviso.usuario_id == usuario_id)
            .where(AcknowledgmentAviso.tenant_id == tenant_id)
            .where(AcknowledgmentAviso.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
