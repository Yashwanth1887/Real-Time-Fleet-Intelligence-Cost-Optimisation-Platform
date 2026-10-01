"""PBKDF2 password verification and short-lived JWT bearer tokens."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import get_settings

PBKDF2_ITERATIONS = 600_000
TOKEN_LIFETIME_MINUTES = 30


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("password must contain at least 12 characters")
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds)).hex()
        return hmac.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, email: str, fleet_id: str, role: str,
                        secret: str | None = None) -> str:
    key = secret or get_settings().jwt_secret_key
    if not key or len(key) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be configured with at least 32 characters")
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {"sub": user_id, "email": email, "fleet_id": fleet_id,
                               "role": role.upper(), "iat": now,
                               "exp": now + timedelta(minutes=TOKEN_LIFETIME_MINUTES)}
    return jwt.encode(payload, key, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    key = get_settings().jwt_secret_key
    if not key or len(key) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be configured with at least 32 characters")
    return jwt.decode(token, key, algorithms=["HS256"])
