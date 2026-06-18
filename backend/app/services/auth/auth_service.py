"""AuthService — core authentication logic (login, session, refresh, revoke)."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import UUID

import hmac

from argon2 import PasswordHasher
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token
from app.models.auth_user import AuthUser
from app.models.domain.asignacion import Asignacion
from app.models.domain.usuario import Usuario
from app.models.refresh_token import RefreshToken
from app.repositories.refresh_token_repo import RefreshTokenRepository


class AuthService:
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.ph = PasswordHasher()
        self.refresh_repo = RefreshTokenRepository(db, tenant_id)

    async def authenticate(self, email: str, password: str) -> AuthUser | None:
        """Authenticate by email across all tenants.

        The user object carries its own ``tenant_id`` — the caller
        (``AuthService.__init__`` tenant_id is still set for session
        creation but the lookup itself is tenant-agnostic.
        """
        stmt = (
            select(AuthUser)
            .where(
                AuthUser.email == email,
                AuthUser.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return None
        try:
            self.ph.verify(user.password_hash, password)
        except Exception:
            return None
        # Update our tenant_id from the found user so sessions
        # (refresh tokens etc.) are created in the right tenant.
        self.tenant_id = user.tenant_id
        self.refresh_repo.tenant_id = user.tenant_id
        return user

    async def create_session(
        self, user: AuthUser
    ) -> tuple[str, str, RefreshToken]:
        key = get_settings().ENCRYPTION_KEY.encode("utf-8")
        normalized = user.email.lower().strip().encode("utf-8")
        email_hash = hmac.new(key, normalized, sha256).hexdigest()

        usuario_stmt = select(Usuario).where(
            Usuario.tenant_id == user.tenant_id,
            Usuario.email_hash == email_hash,
            Usuario.deleted_at.is_(None),
        )
        usuario_result = await self.db.execute(usuario_stmt)
        usuario = usuario_result.scalar_one_or_none()

        roles: list[str] = []
        if usuario is not None:
            roles_stmt = (
                select(Asignacion.rol)
                .where(
                    Asignacion.usuario_id == usuario.id,
                    Asignacion.deleted_at.is_(None),
                )
                .distinct()
            )
            roles_result = await self.db.execute(roles_stmt)
            roles = [row[0] for row in roles_result.all()]

        access_token = create_access_token(
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            roles=roles,
        )
        refresh_token_str = create_refresh_token()
        token_hash = sha256(refresh_token_str.encode()).hexdigest()
        expires_at = datetime.now(tz=timezone.utc) + timedelta(
            days=get_settings().REFRESH_TOKEN_EXPIRE_DAYS
        )
        refresh_entity = await self.refresh_repo.create({
            "user_id": user.id,
            "token_hash": token_hash,
            "expires_at": expires_at,
        })
        return access_token, refresh_token_str, refresh_entity

    async def refresh_session(
        self, refresh_token_str: str
    ) -> tuple[str, str, RefreshToken]:
        token_hash = sha256(refresh_token_str.encode()).hexdigest()
        token = await self.refresh_repo.get_by_token_hash(token_hash)
        if token is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        # Resolve tenant from the token record itself.
        if token.tenant_id is not None:
            self.tenant_id = token.tenant_id
            self.refresh_repo.tenant_id = token.tenant_id

        now = datetime.now(tz=timezone.utc)

        if token.revoked_at is not None:
            await self.refresh_repo.revoke_all_for_user(token.user_id)
            raise HTTPException(
                status_code=401,
                detail="Refresh token reuse detected — all sessions revoked",
            )

        if token.expires_at < now:
            raise HTTPException(status_code=401, detail="Refresh token expired")

        new_refresh_str = create_refresh_token()
        new_token_hash = sha256(new_refresh_str.encode()).hexdigest()
        new_expires_at = now + timedelta(
            days=get_settings().REFRESH_TOKEN_EXPIRE_DAYS
        )
        new_token = await self.refresh_repo.create({
            "user_id": token.user_id,
            "token_hash": new_token_hash,
            "expires_at": new_expires_at,
        })
        await self.refresh_repo.revoke(token.id, replaced_by=new_token.id)

        stmt = (
            select(AuthUser)
            .where(
                AuthUser.id == token.user_id,
                AuthUser.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        key = get_settings().ENCRYPTION_KEY.encode("utf-8")
        normalized = user.email.lower().strip().encode("utf-8")
        email_hash = hmac.new(key, normalized, sha256).hexdigest()

        usuario_stmt = select(Usuario).where(
            Usuario.tenant_id == user.tenant_id,
            Usuario.email_hash == email_hash,
            Usuario.deleted_at.is_(None),
        )
        usuario_result = await self.db.execute(usuario_stmt)
        usuario = usuario_result.scalar_one_or_none()

        roles: list[str] = []
        if usuario is not None:
            roles_stmt = (
                select(Asignacion.rol)
                .where(
                    Asignacion.usuario_id == usuario.id,
                    Asignacion.deleted_at.is_(None),
                )
                .distinct()
            )
            roles_result = await self.db.execute(roles_stmt)
            roles = [row[0] for row in roles_result.all()]

        access_token = create_access_token(
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            roles=roles,
        )
        return access_token, new_refresh_str, new_token

    async def revoke_session(self, refresh_token_str: str) -> bool:
        token_hash = sha256(refresh_token_str.encode()).hexdigest()
        token = await self.refresh_repo.get_by_token_hash(token_hash)
        if token is None or token.revoked_at is not None:
            return False
        # Resolve tenant from the token record.
        if token.tenant_id is not None:
            self.tenant_id = token.tenant_id
            self.refresh_repo.tenant_id = token.tenant_id
        await self.refresh_repo.revoke(token.id)
        return True
