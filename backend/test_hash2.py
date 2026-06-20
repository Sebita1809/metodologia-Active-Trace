"""Test hash roundtrip using Session (same pattern as seed_dev.py)."""
import asyncio
import os
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from app.core.security import hash_password

pw = hash_password("Admin1234!")
print("Generated:", repr(pw[:50]))

url = os.environ.get("DATABASE_URL")
engine = create_async_engine(url)
Session = async_sessionmaker(engine, expire_on_commit=False)
tid = str(uuid.uuid4())


async def main():
    async with Session() as s:
        await s.execute(
            text("INSERT INTO tenants (id, slug, nombre, activo) VALUES (:id, 'test2', 'Test2', true)"),
            {"id": tid},
        )
        uid = str(uuid.uuid4())
        await s.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, password_hash, is_active) "
                "VALUES (:id, :tid, 'test2@test.com', :pw, true)"
            ),
            {"id": uid, "tid": tid, "pw": pw},
        )
        await s.commit()

        r = await s.execute(text("SELECT password_hash FROM users WHERE id = :id"), {"id": uid})
        stored = r.fetchone()[0]
        print("Stored:  ", repr(stored[:50]))
        print("Match:", pw == stored)
        print("Valid argon2:", stored.startswith("$argon2id"))


asyncio.run(main())
