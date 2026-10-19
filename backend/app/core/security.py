"""Password hashing and JWT token handling.

Passwords are hashed with bcrypt (salted, adaptive, constant-time verified).
Access + refresh tokens are signed JWTs carrying a `jti` and `type` claim.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import settings

TokenType = Literal["access", "refresh"]

# bcrypt truncates at 72 bytes; pre-hashing keeps long passphrases safe and
# avoids the library's silent-truncation warning.
_BCRYPT_MAX_BYTES = 72


class TokenError(Exception):
    """Raised when a token is missing, malformed or expired."""


def _prepare(password: str) -> bytes:
    raw = password.encode("utf-8")
    if len(raw) > _BCRYPT_MAX_BYTES:
        import hashlib

        digest = hashlib.sha256(raw).hexdigest().encode("ascii")
        return digest[:_BCRYPT_MAX_BYTES]
    return raw


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(_prepare(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid.uuid4().hex,
        "typ": "STUDIA",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str | uuid.UUID, extra: dict[str, Any] | None = None) -> str:
    token = _create_token(
        str(subject), "access", timedelta(minutes=settings.access_token_expire_minutes)
    )
    if extra:
        # Re-encode with extra claims (used to carry the email for clients).
        decoded = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        decoded.update(extra)
        return jwt.encode(decoded, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token


def create_refresh_token(subject: str | uuid.UUID) -> str:
    return _create_token(str(subject), "refresh", timedelta(days=settings.refresh_token_expire_days))


def create_token_pair(subject: str | uuid.UUID) -> dict[str, Any]:
    return {
        "access_token": create_access_token(subject),
        "refresh_token": create_refresh_token(subject),
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }


def decode_token(token: str, expected_type: TokenType = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Your session has expired. Please sign in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("The provided token is not valid.") from exc

    if payload.get("type") != expected_type:
        raise TokenError("The provided token is not valid for this operation.")
    if not payload.get("sub"):
        raise TokenError("The provided token is missing its subject.")
    return payload