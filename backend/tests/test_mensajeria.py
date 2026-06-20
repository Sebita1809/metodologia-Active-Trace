"""
tests/test_mensajeria.py — Integration tests for internal messaging API.

Covers:
  5.2 list_inbox returns only threads where user is destinatario, within tenant
  6.1 enviar fixes remitente_id from JWT; generates new thread_id
  6.2 responder on foreign/non-existent thread → ThreadNotFoundError; asunto inherited
  8.1 GET /api/inbox lists only user's received threads
  8.2 GET /api/inbox/{thread_id} → 200 ordered; marks leido_at
  8.3 GET /api/inbox/{thread_id} non-participant → 404; other tenant → 404
  8.4 POST /api/inbox/{thread_id}/responder → 201, same thread, inherited asunto
  8.5 Reply to foreign/other-tenant thread → 404, no new message
  8.6 GET /api/inbox without token → 401

Requires TEST_DATABASE_URL (PostgreSQL).
"""
from __future__ import annotations

import os
import uuid
from datetime import timedelta

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.database import Base, build_engine

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping mensajeria tests",
)

_TEST_KEY = "a" * 64


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def msg_engine() -> AsyncEngine:
    import app.models  # noqa: F401

    url = os.environ["TEST_DATABASE_URL"]
    engine = build_engine(url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(_drop_enums)
        await conn.run_sync(_create_enums)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(_drop_enums)

    await engine.dispose()


def _create_enums(conn):
    try:
        conn.execute(sa.text("CREATE TYPE alcance_enum AS ENUM ('global', 'propio')"))
    except Exception:
        pass


def _drop_enums(conn):
    try:
        conn.execute(sa.text("DROP TYPE IF EXISTS alcance_enum CASCADE"))
    except Exception:
        pass


@pytest_asyncio.fixture
async def msg_session(msg_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(msg_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def msg_client(msg_engine: AsyncEngine) -> AsyncClient:
    from app.main import create_app  # noqa: PLC0415
    from app.core.dependencies import get_db  # noqa: PLC0415

    application = create_app()
    factory = async_sessionmaker(msg_engine, expire_on_commit=False)

    async def override_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    application.dependency_overrides[get_db] = override_db

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_tenant(session: AsyncSession, slug_suffix: str = "") -> uuid.UUID:
    from app.models.tenant import Tenant  # noqa: PLC0415
    t = Tenant(slug=f"t-{uuid.uuid4().hex[:8]}{slug_suffix}", nombre="Tenant", activo=True)
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t.id


async def _seed_usuario(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    from app.core.crypto import CryptoService  # noqa: PLC0415
    from app.models.usuario import Usuario  # noqa: PLC0415

    crypto = CryptoService(_TEST_KEY)
    email = f"user-{uuid.uuid4().hex[:8]}@msg.com"
    u = Usuario(
        tenant_id=tenant_id,
        nombre="Msg",
        apellidos="User",
        email=crypto.encrypt(email),
        email_hash=crypto.hash_deterministic(email),
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u.id


async def _seed_mensaje(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    remitente_id: uuid.UUID,
    destinatario_id: uuid.UUID,
    asunto: str | None = "Test",
    cuerpo: str = "Hola",
    thread_id: uuid.UUID | None = None,
) -> uuid.UUID:
    from app.models.mensaje import Mensaje  # noqa: PLC0415

    tid = thread_id or uuid.uuid4()
    m = Mensaje(
        tenant_id=tenant_id,
        thread_id=tid,
        remitente_id=remitente_id,
        destinatario_id=destinatario_id,
        asunto=asunto,
        cuerpo=cuerpo,
    )
    session.add(m)
    await session.commit()
    await session.refresh(m)
    return tid


def _make_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    from app.core.config import get_settings  # noqa: PLC0415
    from app.core.security import create_access_token  # noqa: PLC0415

    settings = get_settings()
    return create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=[],
        secret_key=settings.secret_key,
        expire_minutes=30,
    )


# ---------------------------------------------------------------------------
# Task 5.2: list_inbox returns only user's received messages within tenant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_inbox_only_destinatario(msg_session: AsyncSession):
    from app.repositories.mensaje_repository import MensajeRepository  # noqa: PLC0415

    tenant_id = await _seed_tenant(msg_session)
    user_a = await _seed_usuario(msg_session, tenant_id)
    user_b = await _seed_usuario(msg_session, tenant_id)
    user_c = await _seed_usuario(msg_session, tenant_id)

    # B → A (should appear in A's inbox)
    await _seed_mensaje(msg_session, tenant_id=tenant_id, remitente_id=user_b, destinatario_id=user_a)
    # B → C (should NOT appear in A's inbox)
    await _seed_mensaje(msg_session, tenant_id=tenant_id, remitente_id=user_b, destinatario_id=user_c)

    repo = MensajeRepository(session=msg_session, tenant_id=tenant_id)
    inbox = await repo.list_inbox(user_a)

    assert len(inbox) == 1
    assert inbox[0].destinatario_id == user_a


@pytest.mark.asyncio
async def test_list_inbox_tenant_isolation(msg_session: AsyncSession):
    from app.repositories.mensaje_repository import MensajeRepository  # noqa: PLC0415

    tenant1 = await _seed_tenant(msg_session, "-t1")
    tenant2 = await _seed_tenant(msg_session, "-t2")

    user_a = await _seed_usuario(msg_session, tenant1)
    user_b = await _seed_usuario(msg_session, tenant1)
    user_c = await _seed_usuario(msg_session, tenant2)
    user_d = await _seed_usuario(msg_session, tenant2)

    # Message in tenant1 to user_a
    await _seed_mensaje(msg_session, tenant_id=tenant1, remitente_id=user_b, destinatario_id=user_a)
    # Message in tenant2 (should not appear in tenant1 repo)
    await _seed_mensaje(msg_session, tenant_id=tenant2, remitente_id=user_c, destinatario_id=user_d)

    repo_t1 = MensajeRepository(session=msg_session, tenant_id=tenant1)
    inbox = await repo_t1.list_inbox(user_a)
    assert len(inbox) == 1

    # tenant2 repo sees its own message, not tenant1's
    repo_t2 = MensajeRepository(session=msg_session, tenant_id=tenant2)
    inbox_t2 = await repo_t2.list_inbox(user_d)
    assert len(inbox_t2) == 1
    assert inbox_t2[0].tenant_id == tenant2


# ---------------------------------------------------------------------------
# Task 6.1: enviar fixes remitente_id from service user_id; new thread_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enviar_fixes_remitente_from_jwt(msg_session: AsyncSession):
    from app.services.mensaje_service import MensajeService  # noqa: PLC0415

    tenant_id = await _seed_tenant(msg_session)
    user_a = await _seed_usuario(msg_session, tenant_id)
    user_b = await _seed_usuario(msg_session, tenant_id)

    svc = MensajeService(session=msg_session, user_id=user_a, tenant_id=tenant_id)
    dto = await svc.enviar(destinatario_id=user_b, asunto="Hola", cuerpo="Mundo")
    await msg_session.commit()

    assert dto.remitente_id == user_a
    assert dto.destinatario_id == user_b
    assert dto.thread_id is not None

    # A second enviar creates a different thread_id
    dto2 = await svc.enviar(destinatario_id=user_b, asunto="Otro", cuerpo="msg")
    await msg_session.commit()
    assert dto2.thread_id != dto.thread_id


# ---------------------------------------------------------------------------
# Task 6.2: responder on foreign thread raises ThreadNotFoundError; asunto inherited
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_responder_foreign_thread_raises(msg_session: AsyncSession):
    from app.services.mensaje_service import MensajeService, ThreadNotFoundError  # noqa: PLC0415

    tenant_id = await _seed_tenant(msg_session)
    user_a = await _seed_usuario(msg_session, tenant_id)
    user_b = await _seed_usuario(msg_session, tenant_id)
    user_c = await _seed_usuario(msg_session, tenant_id)

    # Create a thread between B and C (user_a is not a participant)
    thread_id = await _seed_mensaje(
        msg_session, tenant_id=tenant_id, remitente_id=user_b, destinatario_id=user_c
    )
    await msg_session.commit()

    svc = MensajeService(session=msg_session, user_id=user_a, tenant_id=tenant_id)
    with pytest.raises(ThreadNotFoundError):
        await svc.responder(thread_id=thread_id, cuerpo="intruso")


@pytest.mark.asyncio
async def test_responder_nonexistent_thread_raises(msg_session: AsyncSession):
    from app.services.mensaje_service import MensajeService, ThreadNotFoundError  # noqa: PLC0415

    tenant_id = await _seed_tenant(msg_session)
    user_a = await _seed_usuario(msg_session, tenant_id)

    svc = MensajeService(session=msg_session, user_id=user_a, tenant_id=tenant_id)
    with pytest.raises(ThreadNotFoundError):
        await svc.responder(thread_id=uuid.uuid4(), cuerpo="nobody")


@pytest.mark.asyncio
async def test_responder_inherits_asunto(msg_session: AsyncSession):
    from app.services.mensaje_service import MensajeService  # noqa: PLC0415

    tenant_id = await _seed_tenant(msg_session)
    user_a = await _seed_usuario(msg_session, tenant_id)
    user_b = await _seed_usuario(msg_session, tenant_id)

    # A sends the root message with an asunto
    svc_a = MensajeService(session=msg_session, user_id=user_a, tenant_id=tenant_id)
    root = await svc_a.enviar(destinatario_id=user_b, asunto="Subject original", cuerpo="Root")
    await msg_session.commit()

    # B replies — asunto is inherited, not from client
    svc_b = MensajeService(session=msg_session, user_id=user_b, tenant_id=tenant_id)
    reply = await svc_b.responder(thread_id=root.thread_id, cuerpo="Reply")
    await msg_session.commit()

    assert reply.asunto == "Subject original"
    assert reply.thread_id == root.thread_id


# ---------------------------------------------------------------------------
# Task 8.1: GET /api/inbox lists only user's received threads
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_inbox_lists_received_threads(
    msg_session: AsyncSession, msg_client: AsyncClient
):
    tenant_id = await _seed_tenant(msg_session)
    user_a = await _seed_usuario(msg_session, tenant_id)
    user_b = await _seed_usuario(msg_session, tenant_id)
    user_c = await _seed_usuario(msg_session, tenant_id)

    # B → A (should appear)
    await _seed_mensaje(msg_session, tenant_id=tenant_id, remitente_id=user_b, destinatario_id=user_a, asunto="Para A")
    # B → C (should NOT appear in A's inbox)
    await _seed_mensaje(msg_session, tenant_id=tenant_id, remitente_id=user_b, destinatario_id=user_c, asunto="Para C")
    await msg_session.commit()

    token = _make_token(user_a, tenant_id)
    resp = await msg_client.get("/api/inbox", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["mensajes"][0]["destinatario_id"] == str(user_a)


# ---------------------------------------------------------------------------
# Task 8.2: GET /api/inbox/{thread_id} → 200 ordered; marks leido_at
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_thread_ordered_and_marks_read(
    msg_session: AsyncSession, msg_client: AsyncClient
):
    tenant_id = await _seed_tenant(msg_session)
    user_a = await _seed_usuario(msg_session, tenant_id)
    user_b = await _seed_usuario(msg_session, tenant_id)

    # Create two messages in the same thread
    thread_id = uuid.uuid4()
    await _seed_mensaje(
        msg_session, tenant_id=tenant_id,
        remitente_id=user_b, destinatario_id=user_a,
        asunto="Hilo", cuerpo="Primer", thread_id=thread_id,
    )
    await _seed_mensaje(
        msg_session, tenant_id=tenant_id,
        remitente_id=user_a, destinatario_id=user_b,
        asunto="Hilo", cuerpo="Segundo", thread_id=thread_id,
    )
    await msg_session.commit()

    token_a = _make_token(user_a, tenant_id)
    resp = await msg_client.get(
        f"/api/inbox/{thread_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["mensajes"]) == 2
    # Messages ordered ascending by created_at
    first, second = data["mensajes"]
    assert first["cuerpo"] == "Primer"
    assert second["cuerpo"] == "Segundo"

    # Read receipt: only message addressed to user_a (Primer) should be marked
    assert first["leido_at"] is not None
    # second was sent by user_a (not received by user_a), leido_at stays None
    assert second["leido_at"] is None


# ---------------------------------------------------------------------------
# Task 8.3: Non-participant and other-tenant → 404
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_thread_non_participant_404(
    msg_session: AsyncSession, msg_client: AsyncClient
):
    tenant_id = await _seed_tenant(msg_session)
    user_a = await _seed_usuario(msg_session, tenant_id)
    user_b = await _seed_usuario(msg_session, tenant_id)
    user_c = await _seed_usuario(msg_session, tenant_id)

    thread_id = await _seed_mensaje(
        msg_session, tenant_id=tenant_id, remitente_id=user_a, destinatario_id=user_b
    )
    await msg_session.commit()

    # user_c is not a participant
    token_c = _make_token(user_c, tenant_id)
    resp = await msg_client.get(
        f"/api/inbox/{thread_id}",
        headers={"Authorization": f"Bearer {token_c}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_thread_other_tenant_404(
    msg_session: AsyncSession, msg_client: AsyncClient
):
    tenant1 = await _seed_tenant(msg_session, "-ta")
    tenant2 = await _seed_tenant(msg_session, "-tb")
    user_t1a = await _seed_usuario(msg_session, tenant1)
    user_t1b = await _seed_usuario(msg_session, tenant1)
    user_t2a = await _seed_usuario(msg_session, tenant2)
    user_t2b = await _seed_usuario(msg_session, tenant2)

    thread_t2 = await _seed_mensaje(
        msg_session, tenant_id=tenant2, remitente_id=user_t2a, destinatario_id=user_t2b
    )
    await msg_session.commit()

    # user_t1a tries to access a thread from tenant2 → 404
    token = _make_token(user_t1a, tenant1)
    resp = await msg_client.get(
        f"/api/inbox/{thread_t2}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Task 8.4: POST /api/inbox/{thread_id}/responder → 201, same thread, inherited asunto
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reply_creates_in_same_thread(
    msg_session: AsyncSession, msg_client: AsyncClient
):
    tenant_id = await _seed_tenant(msg_session)
    user_a = await _seed_usuario(msg_session, tenant_id)
    user_b = await _seed_usuario(msg_session, tenant_id)

    thread_id = await _seed_mensaje(
        msg_session, tenant_id=tenant_id,
        remitente_id=user_a, destinatario_id=user_b,
        asunto="Asunto del hilo", cuerpo="Root",
    )
    await msg_session.commit()

    token_b = _make_token(user_b, tenant_id)
    resp = await msg_client.post(
        f"/api/inbox/{thread_id}/responder",
        json={"cuerpo": "Respuesta de B"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["thread_id"] == str(thread_id)
    assert data["remitente_id"] == str(user_b)
    assert data["destinatario_id"] == str(user_a)
    assert data["asunto"] == "Asunto del hilo"


# ---------------------------------------------------------------------------
# Task 8.5: Reply to foreign/other-tenant thread → 404, no message created
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reply_to_foreign_thread_404(
    msg_session: AsyncSession, msg_client: AsyncClient
):
    tenant_id = await _seed_tenant(msg_session)
    user_a = await _seed_usuario(msg_session, tenant_id)
    user_b = await _seed_usuario(msg_session, tenant_id)
    user_c = await _seed_usuario(msg_session, tenant_id)

    thread_id = await _seed_mensaje(
        msg_session, tenant_id=tenant_id, remitente_id=user_a, destinatario_id=user_b
    )
    await msg_session.commit()

    # user_c is not in the thread
    token_c = _make_token(user_c, tenant_id)
    resp = await msg_client.post(
        f"/api/inbox/{thread_id}/responder",
        json={"cuerpo": "intruso"},
        headers={"Authorization": f"Bearer {token_c}"},
    )
    assert resp.status_code == 404

    # Verify no new message was created
    from app.repositories.mensaje_repository import MensajeRepository  # noqa: PLC0415
    repo = MensajeRepository(session=msg_session, tenant_id=tenant_id)
    thread_msgs = await repo.get_thread(thread_id)
    assert len(thread_msgs) == 1  # only original


@pytest.mark.asyncio
async def test_reply_to_other_tenant_thread_404(
    msg_session: AsyncSession, msg_client: AsyncClient
):
    tenant1 = await _seed_tenant(msg_session, "-t1x")
    tenant2 = await _seed_tenant(msg_session, "-t2x")
    user_t1 = await _seed_usuario(msg_session, tenant1)
    user_t1b = await _seed_usuario(msg_session, tenant1)
    user_t2a = await _seed_usuario(msg_session, tenant2)
    user_t2b = await _seed_usuario(msg_session, tenant2)

    thread_t2 = await _seed_mensaje(
        msg_session, tenant_id=tenant2, remitente_id=user_t2a, destinatario_id=user_t2b
    )
    await msg_session.commit()

    token = _make_token(user_t1, tenant1)
    resp = await msg_client.post(
        f"/api/inbox/{thread_t2}/responder",
        json={"cuerpo": "cross-tenant intrusion"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Task 8.6: GET /api/inbox without token → 401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_inbox_no_token(msg_client: AsyncClient):
    resp = await msg_client.get("/api/inbox")
    assert resp.status_code == 401
