"""
workers/main.py — Entrypoint del worker de activia-trace (placeholder C-01).

Este worker manejará la cola de comunicaciones salientes:
  Pend → Send → OK/Fail
  Pend → Canc (cancelado antes de enviar)

La tecnología real de la cola (asyncio propio / ARQ / Celery) es ADR-003,
aún abierta. Este módulo deja el entrypoint listo para que el servicio
`worker` de docker-compose arranque; la lógica real se implementa al
construir el módulo de comunicaciones.

Implementado: C-01 (placeholder)
Lógica real: changes de comunicaciones (ver CHANGES.md)
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


async def run_worker() -> None:
    """Worker loop placeholder.

    Actualmente es un no-op que sólo logea que arrancó y duerme.
    La implementación real (consumo de cola, dispatch de notificaciones)
    llegará con los changes de comunicaciones.
    """
    logger.info("activia-trace worker starting (placeholder — no tasks yet)")

    while True:
        # No-op loop: keeps the process alive for docker-compose health checks.
        # Replace this with actual queue consumption in communication changes.
        await asyncio.sleep(60)


if __name__ == "__main__":
    # Entry-point for docker CMD: python -m app.workers.main
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())
