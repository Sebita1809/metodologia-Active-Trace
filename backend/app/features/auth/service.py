"""
app/features/auth/service.py — Authentication service.

All business logic for:
  - login (credentials → access+refresh or partial_token when 2FA active)
  - refresh (token rotation; revoked reuse → revoke all sessions)
  - logout (idempotent revocation)
  - 2FA enrollment, confirmation, and gate verification
  - password recovery (forgot + reset)

No HTTP concerns here — exceptions map to HTTP status in the router layer.

Implemented: C-03 (auth-jwt-2fa)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import CryptoService
from app.core.exceptions import AuthenticationError, InvalidTokenError, TotpError
from app.core.security import (
    create_access_token,
    create_partial_token,
    create_refresh_token,
    generate_totp_secret,
    get_totp_uri,
    hash_token,
    verify_password,
    verify_token,
    verify_totp_code,
    TokenError,
)
from app.features.auth.repository import (
    PasswordResetTokenRepository,
    RefreshTokenRepository,
    TotpSecretRepository,
)
from app.features.auth.schemas import PartialTokenResponse, TotpEnrollResponse, TokenResponse
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.repositories.users import UserRepository

log = logging.getLogger(__name__)


class AuthService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        crypto: CryptoService,
        secret_key: str,
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
        password_reset_expire_minutes: int = 15,
        totp_issuer: str = "activia-trace",
    ) -> None:
        self._session = session
        self._crypto = crypto
        self._secret_key = secret_key
        self._access_expire = access_token_expire_minutes
        self._refresh_expire_days = refresh_token_expire_days
        self._reset_expire_minutes = password_reset_expire_minutes
        self._totp_issuer = totp_issuer

    # ------------------------------------------------------------------
    # Internal helpers — build scoped repositories
    # ------------------------------------------------------------------

    def _user_repo(self, tenant_id: uuid.UUID) -> UserRepository:
        return UserRepository(session=self._session, tenant_id=tenant_id)

    def _usuario_repo(self, tenant_id: uuid.UUID) -> UsuarioRepository:
        return UsuarioRepository(session=self._session, tenant_id=tenant_id)

    def _asignacion_repo(self, tenant_id: uuid.UUID) -> AsignacionRepository:
        return AsignacionRepository(session=self._session, tenant_id=tenant_id)

    async def _load_roles(self, *, email: str, tenant_id: uuid.UUID) -> list[str]:
        """Return the list of active roles for the user identified by email in this tenant.

        Returns an empty list if no matching usuario or asignaciones are found —
        the caller should still allow login (roles affect RBAC but not authentication).
        """
        email_hash = self._crypto.hash_deterministic(email)
        usuario = await self._usuario_repo(tenant_id).get_by_email_hash(email_hash)
        if usuario is None:
            return []
        asignaciones = await self._asignacion_repo(tenant_id).list_by_usuario(
            usuario.id, estado_vigencia="Vigente"
        )
        return list({a.rol for a in asignaciones})

    def _rt_repo(self, tenant_id: uuid.UUID) -> RefreshTokenRepository:
        return RefreshTokenRepository(session=self._session, tenant_id=tenant_id)

    def _prt_repo(self, tenant_id: uuid.UUID) -> PasswordResetTokenRepository:
        return PasswordResetTokenRepository(session=self._session, tenant_id=tenant_id)

    def _totp_repo(self, tenant_id: uuid.UUID) -> TotpSecretRepository:
        return TotpSecretRepository(session=self._session, tenant_id=tenant_id)

    def _issue_full_session(
        self, *, user_id: uuid.UUID, tenant_id: uuid.UUID, roles: list[str]
    ) -> tuple[str, str]:
        """Return (access_token, raw_refresh_token) without persisting the refresh token."""
        access = create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=roles,
            secret_key=self._secret_key,
            expire_minutes=self._access_expire,
        )
        raw_refresh = create_refresh_token()
        return access, raw_refresh

    async def _persist_refresh(
        self, *, user_id: uuid.UUID, tenant_id: uuid.UUID, raw_refresh: str
    ) -> None:
        rt_repo = self._rt_repo(tenant_id)
        expires = datetime.now(tz=timezone.utc) + timedelta(days=self._refresh_expire_days)
        await rt_repo.create(
            user_id=user_id,
            token_hash=hash_token(raw_refresh),
            expires_at=expires,
        )

    # ------------------------------------------------------------------
    # 6.2 GREEN — login
    # ------------------------------------------------------------------

    async def login(
        self,
        *,
        email: str,
        password: str,
        tenant_id: uuid.UUID,
    ) -> TokenResponse | PartialTokenResponse:
        user_repo = self._user_repo(tenant_id)
        user = await user_repo.get_by_email(email)

        # Constant-time failure — never reveal whether email exists
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid credentials")

        if not user.is_active:
            raise AuthenticationError("Account is inactive")

        totp_repo = self._totp_repo(tenant_id)
        totp = await totp_repo.get_for_user(user.id)
        if totp is not None:
            # 2FA gate — issue partial token only
            partial = create_partial_token(
                user_id=user.id,
                tenant_id=tenant_id,
                secret_key=self._secret_key,
            )
            return PartialTokenResponse(partial_token=partial, requires_2fa=True)

        roles = await self._load_roles(email=email, tenant_id=tenant_id)
        access, raw_refresh = self._issue_full_session(
            user_id=user.id, tenant_id=tenant_id, roles=roles
        )
        await self._persist_refresh(user_id=user.id, tenant_id=tenant_id, raw_refresh=raw_refresh)
        return TokenResponse(access_token=access, refresh_token=raw_refresh)

    # ------------------------------------------------------------------
    # 6.4 GREEN — refresh + logout
    # ------------------------------------------------------------------

    async def refresh(
        self,
        *,
        raw_token: str,
        tenant_id: uuid.UUID,
    ) -> TokenResponse:
        rt_repo = self._rt_repo(tenant_id)
        token_hash = hash_token(raw_token)

        # Fetch including revoked so we can detect reuse attacks
        rt_any = await rt_repo.get_any_by_hash(token_hash)

        if rt_any is None:
            raise AuthenticationError("Refresh token is invalid")

        if rt_any.revoked_at is not None:
            # Revoked token reused → attacker may have the old token → revoke all sessions
            await rt_repo.revoke_all_for_user(rt_any.user_id)
            raise AuthenticationError("Refresh token was already revoked")

        if rt_any.expires_at.replace(tzinfo=timezone.utc) < datetime.now(tz=timezone.utc):
            await rt_repo.revoke(token_hash)
            raise AuthenticationError("Refresh token has expired")

        user_id = rt_any.user_id

        # Atomic rotation: revoke old, issue new
        await rt_repo.revoke(token_hash)
        refreshed_user = await self._user_repo(tenant_id).get(user_id)
        roles = await self._load_roles(email=refreshed_user.email, tenant_id=tenant_id) if refreshed_user else []
        access, new_raw = self._issue_full_session(
            user_id=user_id, tenant_id=tenant_id, roles=roles
        )
        await self._persist_refresh(user_id=user_id, tenant_id=tenant_id, raw_refresh=new_raw)
        return TokenResponse(access_token=access, refresh_token=new_raw)

    async def logout(
        self,
        *,
        raw_token: str,
        tenant_id: uuid.UUID,
    ) -> None:
        """Revoke the given refresh token. Idempotent — no error if already revoked."""
        rt_repo = self._rt_repo(tenant_id)
        await rt_repo.revoke(hash_token(raw_token))

    # ------------------------------------------------------------------
    # 6.7 GREEN — 2FA enrollment, confirmation, and gate
    # ------------------------------------------------------------------

    async def enroll_2fa(
        self,
        *,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        email: str,
    ) -> TotpEnrollResponse:
        raw_secret = generate_totp_secret()
        encrypted = self._crypto.encrypt(raw_secret)
        totp_repo = self._totp_repo(tenant_id)
        await totp_repo.create_pending(user_id=user_id, encrypted_secret=encrypted)
        uri = get_totp_uri(secret=raw_secret, email=email, issuer=self._totp_issuer)
        return TotpEnrollResponse(otpauth_uri=uri)

    async def confirm_2fa(
        self,
        *,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        code: str,
    ) -> None:
        totp_repo = self._totp_repo(tenant_id)
        pending = await totp_repo.get_pending_for_user(user_id)
        if pending is None:
            raise TotpError("No pending 2FA enrollment found")

        raw_secret = self._crypto.decrypt(pending.encrypted_secret)
        if not verify_totp_code(secret=raw_secret, code=code):
            raise TotpError("Invalid TOTP code")

        await totp_repo.confirm(pending.id)

    async def verify_2fa_gate(
        self,
        *,
        partial_token: str,
        code: str,
    ) -> TokenResponse:
        try:
            claims = verify_token(
                partial_token,
                secret_key=self._secret_key,
                expected_scope="2fa_pending",
            )
        except TokenError as exc:
            raise AuthenticationError(str(exc)) from exc

        user_id = uuid.UUID(claims["sub"])
        tenant_id = uuid.UUID(claims["tenant_id"])

        totp_repo = self._totp_repo(tenant_id)
        totp = await totp_repo.get_for_user(user_id)
        if totp is None:
            raise AuthenticationError("2FA not configured for this user")

        raw_secret = self._crypto.decrypt(totp.encrypted_secret)
        if not verify_totp_code(secret=raw_secret, code=code):
            raise AuthenticationError("Invalid TOTP code")

        access, raw_refresh = self._issue_full_session(
            user_id=user_id, tenant_id=tenant_id, roles=[]
        )
        await self._persist_refresh(user_id=user_id, tenant_id=tenant_id, raw_refresh=raw_refresh)
        return TokenResponse(access_token=access, refresh_token=raw_refresh)

    # ------------------------------------------------------------------
    # 6.9 GREEN — password recovery
    # ------------------------------------------------------------------

    async def forgot_password(
        self,
        *,
        email: str,
        tenant_id: uuid.UUID,
    ) -> str | None:
        """Issue a password reset token for the user.

        Returns the raw token (for logging/testing) or None if user not found.
        Always succeeds silently to prevent user enumeration.
        """
        user_repo = self._user_repo(tenant_id)
        user = await user_repo.get_by_email(email)
        if user is None:
            return None

        prt_repo = self._prt_repo(tenant_id)
        await prt_repo.invalidate_previous_for_user(user.id)

        raw_token = create_refresh_token()  # URL-safe random 32-byte token
        expires = datetime.now(tz=timezone.utc) + timedelta(minutes=self._reset_expire_minutes)
        await prt_repo.create(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=expires,
        )
        log.info(
            "password_reset_token_created",
            extra={"user_id": str(user.id), "tenant_id": str(tenant_id)},
        )
        return raw_token

    async def reset_password(
        self,
        *,
        raw_token: str,
        new_password: str,
        tenant_id: uuid.UUID,
    ) -> None:
        prt_repo = self._prt_repo(tenant_id)
        prt = await prt_repo.get_valid_by_hash(hash_token(raw_token))
        if prt is None:
            raise InvalidTokenError("Reset token is invalid, expired, or already used")

        user_repo = self._user_repo(tenant_id)
        from app.core.security import hash_password  # noqa: PLC0415
        await user_repo.update_password(prt.user_id, hash_password(new_password))

        await prt_repo.mark_used(hash_token(raw_token))
        await self._rt_repo(tenant_id).revoke_all_for_user(prt.user_id)
