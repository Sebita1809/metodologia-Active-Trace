"""
app/workers/comunicacion_worker.py — Async worker for the communications queue.

This module exposes `procesar_pendientes(db, canal, tenant_id, requiere_aprobacion)`
as the primary entry point. The worker:
  1. Lists dispatchable Pendiente messages (respecting approval gate — D-02).
  2. Conditionally transitions each to Enviando (race-safe vs. cancellation — D-04).
  3. Calls canal.enviar(destinatario_descifrado, asunto, cuerpo).
  4. Transitions to Enviado or Error depending on the result.
  5. On exception from the canal: captures it, transitions to Error, does NOT propagate.

Key design decisions:
  D-04 — Canal interface is injectable for testability; mock the canal, NEVER the DB.
  D-02 — Fail-safe: requiere_aprobacion=True by default when config is absent.
  Risks — A failure in one message does NOT stop processing of the rest.

The canal interface (protocol):
    canal.enviar(destinatario: str, asunto: str, cuerpo: str) -> bool
    Returns True on success, False on failure. May raise exceptions.

Implemented: C-12 (comunicaciones-cola-worker)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import CryptoService
from app.models.comunicacion import EstadoComunicacion
from app.repositories.comunicacion_repository import ComunicacionRepository

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Canal protocol — injectable interface for email/N8N/SMTP dispatch
# ---------------------------------------------------------------------------

class CanalEnvio(Protocol):
    """Protocol for the outgoing channel.

    Implementations: SMTP adapter, N8N webhook, mock for tests.
    The return value indicates success (True) or failure (False).
    May raise exceptions — the worker captures them as Error.
    """

    async def enviar(
        self,
        destinatario: str,   # plaintext email (decrypted before calling)
        asunto: str,
        cuerpo: str,
    ) -> bool:
        """Dispatch a message. Returns True on success, False on failure."""
        ...


# ---------------------------------------------------------------------------
# Core worker function
# ---------------------------------------------------------------------------

async def procesar_pendientes(
    db: AsyncSession,
    canal: CanalEnvio,
    *,
    tenant_id: uuid.UUID,
    crypto: CryptoService,
    requiere_aprobacion: bool = True,   # fail-safe default: True (D-02)
) -> dict[str, int]:
    """Process all dispatchable Pendiente communications for a tenant.

    Parameters:
        db                 — async DB session
        canal              — injectable channel (mock in tests, SMTP/N8N in prod)
        tenant_id          — tenant to process
        crypto             — CryptoService for decrypting destinatario
        requiere_aprobacion — if True, only dispatch messages with aprobado_at set.
                              Default True (fail-safe if config is absent).

    Returns:
        dict with keys: enviados, errores, saltados (messages skipped due to race)
    """
    repo = ComunicacionRepository(session=db, tenant_id=tenant_id)

    # Step 1: Get list of dispatchable messages
    pendientes = await repo.list_despachables(requiere_aprobacion=requiere_aprobacion)

    enviados = 0
    errores = 0
    saltados = 0

    for com in pendientes:
        # Step 2: Conditionally transition to Enviando (race-safe)
        # If cancellation happened concurrently, rowcount == 0 → skip
        rowcount = await repo.aplicar_transicion_condicional(
            com.id,
            desde=EstadoComunicacion.Pendiente,
            hacia=EstadoComunicacion.Enviando,
        )

        if rowcount == 0:
            # Another process (cancellation) already changed the state
            logger.info("Comunicacion %s was already changed (race), skipping", com.id)
            saltados += 1
            continue

        # Step 3: Decrypt destinatario for the canal
        try:
            destinatario_claro = crypto.decrypt(com.destinatario)
        except Exception as exc:
            logger.error("Failed to decrypt destinatario for %s: %s", com.id, exc)
            await repo.aplicar_transicion_condicional(
                com.id,
                desde=EstadoComunicacion.Enviando,
                hacia=EstadoComunicacion.Error,
            )
            errores += 1
            continue

        # Step 4: Dispatch via canal (catch ALL exceptions — D-04 isolation)
        try:
            success = await canal.enviar(destinatario_claro, com.asunto, com.cuerpo)
        except Exception as exc:
            logger.exception("Canal raised exception for comunicacion %s: %s", com.id, exc)
            success = False

        # Step 5: Transition to Enviado or Error
        if success:
            enviado_at = datetime.now(tz=timezone.utc)
            await repo.aplicar_transicion_condicional(
                com.id,
                desde=EstadoComunicacion.Enviando,
                hacia=EstadoComunicacion.Enviado,
                extra_values={"enviado_at": enviado_at},
            )
            enviados += 1
            logger.info("Comunicacion %s enviada exitosamente", com.id)
        else:
            await repo.aplicar_transicion_condicional(
                com.id,
                desde=EstadoComunicacion.Enviando,
                hacia=EstadoComunicacion.Error,
            )
            errores += 1
            logger.warning("Comunicacion %s falló el despacho → Error", com.id)

    return {"enviados": enviados, "errores": errores, "saltados": saltados}
