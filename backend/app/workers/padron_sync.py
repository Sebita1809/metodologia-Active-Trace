"""Nightly padron sync worker — iterates tenants and syncs from Moodle."""
from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select

from app.core.database import get_session_factory
from app.integrations.moodle_ws import MoodleWSClient
from app.models.domain.asignacion import Asignacion
from app.models.domain.materia import Materia
from app.models.tenant import Tenant, TenantEstado
from app.repositories.padron.entrada_padron_repository import EntradaPadronRepository
from app.repositories.padron.version_padron_repository import VersionPadronRepository

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SECONDS = 86400  # 24 hours


async def run_nightly_sync() -> None:
    """Main sync loop — run once on startup, then sleep between iterations.

    Call this from the lifespan event or run as a standalone script.
    """
    while True:
        try:
            await _sync_all_tenants()
        except Exception as e:
            logger.exception("Unhandled error in nightly sync: %s", e)

        logger.info("Nightly sync complete. Sleeping %s seconds...", SYNC_INTERVAL_SECONDS)
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)


async def _sync_all_tenants() -> None:
    """Iterate all active tenants with Moodle config and sync each."""
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(
            select(Tenant).where(Tenant.estado == TenantEstado.ACTIVO.value)
        )
        tenants = list(result.scalars().all())

    for tenant in tenants:
        if not tenant.config or not tenant.config.get("moodle_ws_url"):
            logger.info("Tenant %s: no Moodle WS config, skipping", tenant.id)
            continue

        if not tenant.config.get("moodle_ws_token"):
            logger.info("Tenant %s: no Moodle WS token, skipping", tenant.id)
            continue

        try:
            await _sync_tenant(tenant)
        except Exception as e:
            logger.exception("Tenant %s: sync failed: %s", tenant.id, e)


async def _get_materia_cohorte_pairs(
    db: AsyncSession,  # noqa: F821 — type imported via sqlalchemy
    tenant_id: UUID,
) -> list[tuple[UUID, UUID]]:
    """Get distinct (materia_id, cohorte_id) pairs with active asignaciones in a tenant."""
    from sqlalchemy.ext.asyncio import AsyncSession  # noqa: F811

    stmt = (
        select(Asignacion.materia_id, Asignacion.cohorte_id)
        .distinct()
        .where(
            Asignacion.tenant_id == tenant_id,
            Asignacion.vig_hasta.is_(None),  # Current assignments
        )
    )
    result = await db.execute(stmt)
    return list(result.all())


async def _get_system_actor_id(db, tenant_id: UUID) -> UUID | None:
    """Find first active admin user in the tenant to use as system actor."""
    from app.models.domain.usuario import Usuario
    from app.repositories.usuarios.asignacion_repository import AsignacionRepository

    # Look for any admin user
    result = await db.execute(
        select(Usuario.id).where(
            Usuario.tenant_id == tenant_id,
            Usuario.deleted_at.is_(None),
        ).limit(1)
    )
    return result.scalar_one_or_none()


async def _sync_tenant(tenant: Tenant) -> None:
    """Sync all active materia-cohorte pairs for a single tenant."""
    config = tenant.config or {}

    if config.get("moodle_sync_lock"):
        logger.warning("Tenant %s: sync lock active, skipping", tenant.id)
        return

    ws_url = config["moodle_ws_url"]
    ws_token = config["moodle_ws_token"]
    course_map = config.get("moodle_course_map", {})

    if not course_map:
        logger.info("Tenant %s: no moodle_course_map in config, skipping", tenant.id)
        return

    factory = get_session_factory()

    # Acquire lock
    async with factory() as db:
        tenant_in_db = await db.get(Tenant, tenant.id)
        if tenant_in_db is None:
            logger.warning("Tenant %s: not found in DB, skipping", tenant.id)
            return
        tenant_in_db.config["moodle_sync_lock"] = True
        await db.commit()

    synced_count = 0
    error_count = 0

    try:
        async with factory() as db:
            pairs = await _get_materia_cohorte_pairs(db, tenant.id)
            system_actor_id = await _get_system_actor_id(db, tenant.id)

        if not pairs:
            logger.info("Tenant %s: no materia-cohorte pairs found, skipping", tenant.id)
            return

        if system_actor_id is None:
            logger.warning("Tenant %s: no system user to record as cargado_por, skipping", tenant.id)
            return

        for materia_id, cohorte_id in pairs:
            course_id = course_map.get(str(materia_id))
            if course_id is None:
                logger.info(
                    "Tenant %s, materia %s: no moodle_course_id mapping, skipping",
                    tenant.id, materia_id,
                )
                continue

            try:
                async with factory() as db:
                    version_repo = VersionPadronRepository(db, tenant.id)
                    entrada_repo = EntradaPadronRepository(db, tenant.id)
                    client = MoodleWSClient(ws_url=ws_url, ws_token=ws_token)

                    moodle_users = await client.get_enrolled_users(course_id)

                    version = await version_repo.create({
                        "materia_id": materia_id,
                        "cohorte_id": cohorte_id,
                        "activa": False,
                        "origen": "moodle",
                        "cargado_por": system_actor_id,
                    })

                    entradas = [
                        {
                            "version_id": version.id,
                            "usuario_id": None,
                            "nombre": u.get("firstname", ""),
                            "apellidos": u.get("lastname", ""),
                            "email": u.get("email", ""),
                            "comision": None,
                            "regional": None,
                        }
                        for u in moodle_users
                    ]
                    await entrada_repo.bulk_create(entradas)

                    await version_repo.deactivate_previous_active(materia_id, cohorte_id)
                    await version_repo.activate(version.id)

                    logger.info(
                        "Tenant %s, materia %s, cohorte %s: synced %d students",
                        tenant.id, materia_id, cohorte_id, len(entradas),
                    )
                    synced_count += 1

            except Exception as e:
                logger.exception(
                    "Tenant %s, materia %s: sync error: %s",
                    tenant.id, materia_id, e,
                )
                error_count += 1

    except Exception as e:
        logger.exception("Tenant %s: sync phase error: %s", tenant.id, e)

    finally:
        # Release lock
        async with factory() as db:
            tenant_in_db = await db.get(Tenant, tenant.id)
            if tenant_in_db and tenant_in_db.config:
                tenant_in_db.config["moodle_sync_lock"] = False
                await db.commit()

        logger.info(
            "Tenant %s: sync finished (%d synced, %d errors), lock released",
            tenant.id, synced_count, error_count,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_nightly_sync())
