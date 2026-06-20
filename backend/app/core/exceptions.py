"""
core/exceptions.py — Typed domain exceptions.

Each exception maps to a specific HTTP status in the router layer:
  AuthenticationError  → 401 Unauthorized
  InvalidTokenError    → 400 Bad Request
  TotpError            → 400 Bad Request

Implemented: C-03 (auth-jwt-2fa)
"""


class AuthenticationError(Exception):
    """Raised when credentials are wrong or a session token is invalid/expired."""


class InvalidTokenError(Exception):
    """Raised when a one-time token (password reset) is expired, used, or unknown."""


class TotpError(Exception):
    """Raised when a TOTP code fails verification."""
