"""Fix existing admin Usuario record: encrypt plaintext email.

Run from backend/:
    .venv313\Scripts\python -m scripts.fix_admin_encryption
"""

import asyncio
import hmac
import os
import sys
from hashlib import sha256

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.security import AESCipher
from app.models.domain.usuario import Usuario
from app.models.tenant import Tenant


async def main() -> None:
    factory = get_session_factory()
    async with factory() as session:
        # 1. Get demo tenant
        result = await session.execute(
            select(Tenant).where(Tenant.codigo == "DEMO")
        )
        tenant = result.scalar_one_or_none()
        if tenant is None:
            print("[ERR] Demo tenant not found. Run seed_test_data first.")
            return

        # 2. Find admin Usuario by email_hash
        key = get_settings().ENCRYPTION_KEY.encode("utf-8")
        email = "admin@demo.com"
        email_hash = hmac.new(key, email.lower().strip().encode("utf-8"), sha256).hexdigest()

        result = await session.execute(
            select(Usuario).where(
                Usuario.tenant_id == tenant.id,
                Usuario.email_hash == email_hash,
            )
        )
        usuario = result.scalar_one_or_none()
        if usuario is None:
            print("[ERR] Admin Usuario not found by email_hash.")
            return

        # 3. Update email to encrypted version
        encrypted = AESCipher.encrypt(email)
        usuario.email = encrypted
        await session.commit()
        await session.refresh(usuario)

        # 4. Verify decrypt works
        decrypted = AESCipher.decrypt(usuario.email)
        assert decrypted == email, f"Mismatch: {decrypted} != {email}"
        print(f"[OK] Admin Usuario {usuario.id} email updated and verified.")
        print(f"     Decrypt OK => {decrypted}")


if __name__ == "__main__":
    asyncio.run(main())
