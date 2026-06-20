"""
app/repositories/mensaje_repository.py — MensajeRepository.

Tenant isolation is inherited from BaseRepository (filters tenant_id + deleted_at).
Additional filters by participant (remitente_id or destinatario_id) prevent
cross-user leakage within the same tenant.

Implemented: C-20 (perfil-y-mensajeria-interna)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mensaje import Mensaje
from app.repositories.base import BaseRepository


class MensajeRepository(BaseRepository[Mensaje]):
    """Repository for Mensaje with tenant + participant isolation."""

    def __init__(self, *, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(model=Mensaje, session=session, tenant_id=tenant_id)

    async def list_inbox(self, destinatario_id: uuid.UUID) -> list[Mensaje]:
        """Return all messages where user is the destinatario, within this tenant.

        Each message belongs to a thread. The caller can group by thread_id.
        Ordered by created_at ascending so threads display chronologically.
        """
        stmt = (
            self._base_query()
            .where(Mensaje.destinatario_id == destinatario_id)
            .order_by(Mensaje.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_thread(self, thread_id: uuid.UUID) -> list[Mensaje]:
        """Return all messages in a thread, ordered by created_at ascending.

        Does NOT filter by participant — caller is responsible for checking
        via is_participant() before calling this.
        """
        stmt = (
            self._base_query()
            .where(Mensaje.thread_id == thread_id)
            .order_by(Mensaje.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def is_participant(self, thread_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Return True if user_id is remitente or destinatario of any message in thread."""
        stmt = (
            self._base_query()
            .where(Mensaje.thread_id == thread_id)
            .where(
                (Mensaje.remitente_id == user_id) | (Mensaje.destinatario_id == user_id)
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def mark_thread_read(self, thread_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Set leido_at = now() on messages in thread where destinatario_id = user_id."""
        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(Mensaje)
            .where(Mensaje.tenant_id == self._tenant_id)
            .where(Mensaje.thread_id == thread_id)
            .where(Mensaje.destinatario_id == user_id)
            .where(Mensaje.leido_at.is_(None))
            .where(Mensaje.deleted_at.is_(None))
            .values(leido_at=now)
        )
        await self._session.execute(stmt)

    async def get_other_participant(
        self, thread_id: uuid.UUID, user_id: uuid.UUID
    ) -> uuid.UUID | None:
        """Return the UUID of the other participant in the thread (not user_id)."""
        stmt = (
            self._base_query()
            .where(Mensaje.thread_id == thread_id)
            .where(
                (Mensaje.remitente_id == user_id) | (Mensaje.destinatario_id == user_id)
            )
        )
        result = await self._session.execute(stmt)
        msg = result.scalar_one_or_none()
        if msg is None:
            return None
        if msg.remitente_id == user_id:
            return msg.destinatario_id
        return msg.remitente_id

    async def get_thread_subject(self, thread_id: uuid.UUID) -> str | None:
        """Return the asunto of the root message (first message) of a thread."""
        stmt = (
            self._base_query()
            .where(Mensaje.thread_id == thread_id)
            .order_by(Mensaje.created_at.asc())
        )
        result = await self._session.execute(stmt)
        first = result.scalars().first()
        return first.asunto if first else None
