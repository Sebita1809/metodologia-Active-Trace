"""
api/v1/routers/inbox.py — Internal inbox endpoints.

Routes:
  POST /api/inbox                           — send initial message (new thread)
  GET  /api/inbox                           — list threads where user is destinatario
  GET  /api/inbox/{thread_id}               — read full thread (marks received as read)
  POST /api/inbox/{thread_id}/responder     — reply within existing thread

Identity resolved exclusively from JWT via get_current_user.
No business logic in this router — delegated to MensajeService.

Implemented: C-20 (perfil-y-mensajeria-interna)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import CurrentUser
from app.core.dependencies import get_current_user, get_db
from app.schemas.mensaje import (
    MensajeCreate,
    MensajeResponse,
    RespuestaCreate,
    ThreadResponse,
    ThreadSummaryResponse,
)
from app.services.mensaje_service import MensajeDTO, MensajeService, ThreadNotFoundError

router = APIRouter(tags=["inbox"])


def _get_svc(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MensajeService:
    """Build MensajeService scoped to the authenticated user and tenant."""
    return MensajeService(
        session=session,
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
    )


def _msg_to_response(dto: MensajeDTO) -> MensajeResponse:
    return MensajeResponse.model_validate(dto)


@router.post("", response_model=MensajeResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    body: MensajeCreate,
    svc: MensajeService = Depends(_get_svc),
) -> MensajeResponse:
    dto = await svc.enviar(
        destinatario_id=body.destinatario_id,
        asunto=body.asunto,
        cuerpo=body.cuerpo,
    )
    return _msg_to_response(dto)


@router.get("", response_model=list[ThreadSummaryResponse])
async def list_inbox(
    svc: MensajeService = Depends(_get_svc),
) -> list[ThreadSummaryResponse]:
    threads = await svc.listar_inbox()
    return [
        ThreadSummaryResponse(
            thread_id=t.thread_id,
            asunto=t.asunto,
            mensajes=[_msg_to_response(m) for m in t.mensajes],
        )
        for t in threads
    ]


@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: uuid.UUID,
    svc: MensajeService = Depends(_get_svc),
) -> ThreadResponse:
    try:
        thread = await svc.leer_hilo(thread_id)
    except ThreadNotFoundError:
        raise HTTPException(status_code=404, detail="Thread not found")
    return ThreadResponse(
        thread_id=thread.thread_id,
        asunto=thread.asunto,
        mensajes=[_msg_to_response(m) for m in thread.mensajes],
    )


@router.post(
    "/{thread_id}/responder",
    response_model=MensajeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def reply_to_thread(
    thread_id: uuid.UUID,
    body: RespuestaCreate,
    svc: MensajeService = Depends(_get_svc),
) -> MensajeResponse:
    try:
        dto = await svc.responder(thread_id=thread_id, cuerpo=body.cuerpo)
    except ThreadNotFoundError:
        raise HTTPException(status_code=404, detail="Thread not found")
    return _msg_to_response(dto)
