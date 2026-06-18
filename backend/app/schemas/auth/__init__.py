"""Auth schemas — request/response models for authentication endpoints."""

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    email: str
    password: str
    model_config = ConfigDict(extra="forbid")


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    model_config = ConfigDict(extra="forbid")


class Login2FARequiredResponse(BaseModel):
    requires_2fa: bool = True
    session_token: str
    model_config = ConfigDict(extra="forbid")


class RefreshRequest(BaseModel):
    refresh_token: str
    model_config = ConfigDict(extra="forbid")


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    model_config = ConfigDict(extra="forbid")


class LogoutRequest(BaseModel):
    refresh_token: str
    model_config = ConfigDict(extra="forbid")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    model_config = ConfigDict(extra="forbid")


class ErrorResponse(BaseModel):
    detail: str
    model_config = ConfigDict(extra="forbid")


class ForgotRequest(BaseModel):
    email: str
    model_config = ConfigDict(extra="forbid")


class ForgotResponse(BaseModel):
    message: str
    token: str | None = None
    model_config = ConfigDict(extra="forbid")


class ResetRequest(BaseModel):
    token: str
    new_password: str
    model_config = ConfigDict(extra="forbid")


class EnrollResponse(BaseModel):
    uri: str
    secret: str
    model_config = ConfigDict(extra="forbid")


class Verify2FARequest(BaseModel):
    code: str
    session_token: str
    model_config = ConfigDict(extra="forbid")


__all__ = [
    "LoginRequest",
    "LoginResponse",
    "Login2FARequiredResponse",
    "RefreshRequest",
    "RefreshResponse",
    "LogoutRequest",
    "TokenResponse",
    "ErrorResponse",
    "ForgotRequest",
    "ForgotResponse",
    "ResetRequest",
    "EnrollResponse",
    "Verify2FARequest",
]
