"""Test hash roundtrip - verify password hashing works correctly with DB."""
import asyncio
import os
import uuid
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.security import hash_password


async def test():
    url = os.environ.get("DATABASE_URL")
    e = create_async_engine(url)
    tid = str(uuid.uuid4())

    async with e.begin() as c:
        await c.execute(
            text("INSERT INTO tenants (id, slug, nombre, activo) VALUES (:id, 'test', 'Test', true)"),
            {"id": tid},
        )

    pw_hash = hash_password("Test1234!")
    print("Generated hash:", repr(pw_hash))
    print("Starts with $argon2id:", pw_hash.startswith("$argon2id$v=19$"))

    uid = str(uuid.uuid4())
    async with e.begin() as c:
        await c.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, password_hash, is_active) "
                "VALUES (:id, :tid, :email, :pw, true)"
            ),
            {"id": uid, "tid": tid, "email": "test@test.com", "pw": pw_hash},
        )

    async with e.connect() as c:
        r = await c.execute(text("SELECT password_hash FROM users WHERE id = :id"), {"id": uid})
        stored = r.fetchone()[0]
        print("Stored hash: ", repr(stored))
        print("Match:", pw_hash == stored)
        print("Stored starts with $argon2id:", stored.startswith("$argon2id$v=19$"))

    await e.dispose()


asyncio.run(test())
