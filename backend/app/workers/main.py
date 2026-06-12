"""Worker entrypoint — placeholder for C-12 (comunicaciones-cola-worker).

This is a no-op placeholder. The real queue technology will be
determined by ADR-003 and implemented in C-12.
"""

import asyncio
import logging

from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


async def main() -> None:
    """Run the worker loop (placeholder)."""
    logger.info("worker starting (placeholder — no tasks configured)")
    try:
        while True:
            await asyncio.sleep(3600)
            logger.debug("worker heartbeat")
    except asyncio.CancelledError:
        logger.info("worker shutting down")


if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())
