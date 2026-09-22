"""Security utilities for password hashing and JWT access token generation."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a plaintext password securely using bcrypt with auto-generated salt.

    Args:
        password: Raw plaintext password string.

    Returns:
        str: Bcrypt-hashed password string.
    """
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """Verify a plaintext password against a stored bcrypt hash.

    Args:
        plain_password: Plaintext password provided during authentication.
        hashed_password: Stored bcrypt password hash string.

    Returns:
        bool: True if password matches hash, False otherwise.
    """
    if not hashed_password or not plain_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: Union[str, Any],
    role: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a signed JWT access token containing subject, role, and expiration claims.

    Args:
        subject: Unique identifier of the authenticated user (e.g. user UUID).
        role: Primary role of the user (e.g. APPLICANT, REVIEWER, ADMIN).
        expires_delta: Optional explicit validity duration.
        extra_claims: Optional supplementary non-sensitive token claims.

    Returns:
        str: Encoded JWT access token.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "role": str(role),
        "type": "access",
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token.

    Verifies signature integrity, token expiration, and token type claim.

    Args:
        token: Raw JWT access token string.

    Returns:
        Dict[str, Any]: Decoded payload claims dictionary.

    Raises:
        jwt.PyJWTError: If the token is invalid, expired, or corrupted.
        ValueError: If token type is not 'access' or subject is missing.
    """
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["exp", "sub", "iat"]},
    )

    if payload.get("type") != "access":
        raise ValueError("Invalid token type: expected access token")

    if not payload.get("sub"):
        raise ValueError("Token subject claim is missing")

    return payload
