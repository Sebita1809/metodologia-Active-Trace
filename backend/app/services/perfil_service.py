"""
app/services/perfil_service.py — PerfilService.

Resolves the acting user's identity exclusively from the JWT-derived user_id
and delegates to UsuarioService for read/write operations.

No business logic beyond ID resolution — all encryption, hashing and
validation remain in UsuarioService.

Implemented: C-20 (perfil-y-mensajeria-interna)
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import CryptoService
from app.services.usuario_service import UsuarioDecifrado, UsuarioService


class PerfilService:
    """Self-service profile operations scoped to the authenticated user.

    The user_id comes exclusively from the JWT (CurrentUser.user_id).
    No endpoint can override it via path/body/header.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        crypto: CryptoService,
    ) -> None:
        self._user_id = user_id
        self._svc = UsuarioService(
            session=session,
            tenant_id=tenant_id,
            crypto=crypto,
        )

    async def get_perfil(self) -> UsuarioDecifrado | None:
        """Return the profile of the authenticated user (PII decrypted)."""
        return await self._svc.get(self._user_id)

    async def update_perfil(self, **kwargs) -> UsuarioDecifrado | None:
        """Update the authenticated user's own profile.

        Only passes kwargs provided by the caller — unset fields are unchanged.
        The user_id is fixed from the JWT; callers cannot override it.
        """
        return await self._svc.update(self._user_id, **kwargs)
