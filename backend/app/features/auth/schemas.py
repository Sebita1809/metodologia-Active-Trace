"""
app/features/auth/schemas.py — Pydantic request/response DTOs for auth endpoints.

All schemas use extra='forbid' to reject unknown fields (security requirement).

Implemented: C-03 (auth-jwt-2fa)
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str | None = None


class ForgotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class TotpVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=6, max_length=6)


class TotpLoginVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    partial_token: str = Field(min_length=1)
    code: str = Field(min_length=6, max_length=6)


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class PartialTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    partial_token: str
    requires_2fa: bool = True


class TotpEnrollResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    otpauth_uri: str


class MessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
