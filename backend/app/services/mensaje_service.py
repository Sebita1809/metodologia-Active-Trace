"""
app/services/mensaje_service.py — MensajeService.

Business logic for internal messaging between registered users.

Rules enforced:
  - remitente_id is ALWAYS fixed from the JWT-derived user_id.
  - Responder validates that the user is a participant of the thread.
  - Responder inherits asunto from the thread root (client cannot override).
  - Tenant isolation is enforced by the repository layer.

Implemented: C-20 (perfil-y-mensajeria-interna)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mensaje import Mensaje
from app.repositories.mensaje_repository import MensajeRepository


@dataclass
class MensajeDTO:
    """Transient DTO for a single message."""
    id: uuid.UUID
    thread_id: uuid.UUID
    tenant_id: uuid.UUID
    remitente_id: uuid.UUID
    destinatario_id: uuid.UUID
    asunto: str | None
    cuerpo: str
    leido_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass
class ThreadDTO:
    """Transient DTO for a conversation thread."""
    thread_id: uuid.UUID
    asunto: str | None
    mensajes: list[MensajeDTO] = field(default_factory=list)


class ThreadNotFoundError(Exception):
    """Raised when a thread does not exist or the user is not a participant."""


class MensajeService:
    """Operations for internal messaging.

    user_id comes from the JWT — callers never supply it via body.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> None:
        self._user_id = user_id
        self._tenant_id = tenant_id
        self._repo = MensajeRepository(session=session, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dto(m: Mensaje) -> MensajeDTO:
        return MensajeDTO(
            id=m.id,
            thread_id=m.thread_id,
            tenant_id=m.tenant_id,
            remitente_id=m.remitente_id,
            destinatario_id=m.destinatario_id,
            asunto=m.asunto,
            cuerpo=m.cuerpo,
            leido_at=m.leido_at,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def enviar(
        self,
        *,
        destinatario_id: uuid.UUID,
        asunto: str | None,
        cuerpo: str,
    ) -> MensajeDTO:
        """Send a new message, creating a new thread.

        remitente_id is fixed from self._user_id (JWT). Any value supplied
        in the body by the caller is ignored.
        thread_id is a fresh UUID generated here.
        """
        thread_id = uuid.uuid4()
        msg = Mensaje(
            tenant_id=self._tenant_id,
            thread_id=thread_id,
            remitente_id=self._user_id,
            destinatario_id=destinatario_id,
            asunto=asunto,
            cuerpo=cuerpo,
        )
        persisted = await self._repo.create(msg)
        return self._to_dto(persisted)

    async def listar_inbox(self) -> list[ThreadDTO]:
        """List threads where the authenticated user is destinatario.

        Returns one ThreadDTO per thread_id, with messages grouped inside.
        """
        mensajes = await self._repo.list_inbox(self._user_id)
        threads: dict[uuid.UUID, ThreadDTO] = {}
        for m in mensajes:
            if m.thread_id not in threads:
                threads[m.thread_id] = ThreadDTO(
                    thread_id=m.thread_id,
                    asunto=m.asunto,
                )
            threads[m.thread_id].mensajes.append(self._to_dto(m))
        return list(threads.values())

    async def leer_hilo(self, thread_id: uuid.UUID) -> ThreadDTO:
        """Return all messages in a thread, marking received ones as read.

        Raises ThreadNotFoundError if the user is not a participant or the
        thread does not exist (router maps this to HTTP 404).
        """
        if not await self._repo.is_participant(thread_id, self._user_id):
            raise ThreadNotFoundError(thread_id)

        await self._repo.mark_thread_read(thread_id, self._user_id)
        mensajes = await self._repo.get_thread(thread_id)

        asunto = mensajes[0].asunto if mensajes else None
        dto = ThreadDTO(thread_id=thread_id, asunto=asunto)
        dto.mensajes = [self._to_dto(m) for m in mensajes]
        return dto

    async def responder(
        self,
        *,
        thread_id: uuid.UUID,
        cuerpo: str,
    ) -> MensajeDTO:
        """Add a reply to an existing thread.

        Validates that the user is a participant. Fixes remitente_id from
        the JWT, sets destinatario_id = the other participant, and inherits
        asunto from the thread root.

        Raises ThreadNotFoundError if the thread does not exist or the user
        is not a participant (router maps this to HTTP 404).
        """
        if not await self._repo.is_participant(thread_id, self._user_id):
            raise ThreadNotFoundError(thread_id)

        other = await self._repo.get_other_participant(thread_id, self._user_id)
        asunto = await self._repo.get_thread_subject(thread_id)

        msg = Mensaje(
            tenant_id=self._tenant_id,
            thread_id=thread_id,
            remitente_id=self._user_id,
            destinatario_id=other,
            asunto=asunto,
            cuerpo=cuerpo,
        )
        persisted = await self._repo.create(msg)
        return self._to_dto(persisted)
