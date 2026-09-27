"""
LeadEngine Authentication Service
JWT-based signup, login, token verification.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


# ── Config ──────────────────────────────────────────────────────────────
# ponytail: single static secret; rotate via env var in production
_SECRET = os.environ.get("LEADENGINE_JWT_SECRET", "dev-secret-change-me")
_ISSUER = "leadengine"
_TOKEN_TTL = 86400 * 7  # 7 days


# ── Models ──────────────────────────────────────────────────────────────

@dataclass
class User:
    id: str
    email: str
    name: str
    password_hash: str
    org_id: Optional[str] = None
    role: str = "member"  # owner | admin | member
    created_at: float = field(default_factory=time.time)


@dataclass
class TokenPayload:
    sub: str          # user id
    email: str
    org_id: Optional[str]
    role: str
    exp: float
    iat: float = field(default_factory=time.time)


# ── Storage ─────────────────────────────────────────────────────────────
# ponytail: in-memory dict; swap for DuckDB/Postgres when multi-process
_users: dict[str, User] = {}       # id -> User
_email_index: dict[str, str] = {}  # email -> id


def _hash_password(password: str) -> str:
    """Return hex digest of PBKDF2-HMAC-SHA256 with 16-byte salt."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + ":" + dk.hex()


def _check_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return hmac.compare_digest(expected.hex(), dk_hex)
    except (ValueError, TypeError):
        return False


# ── JWT (stateless, no deps) ────────────────────────────────────────────

def _b64url(b: bytes) -> str:
    return b.rstrip(b"=").hex()  # hex = simple, no padding issues


def _encode_jwt(payload: dict) -> str:
    header = _b64url(b'{"alg":"HS256","typ":"JWT"}')
    body = _b64url(str(payload).encode())
    sig = hmac.new(_SECRET.encode(), f"{header}.{body}".encode(), "sha256").hexdigest()
    return f"{header}.{body}.{sig}"


def _decode_jwt(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        expected = hmac.new(_SECRET.encode(), f"{parts[0]}.{parts[1]}".encode(), "sha256").hexdigest()
        if not hmac.compare_digest(expected, parts[2]):
            return None
        # parse the payload back from hex
        payload_bytes = bytes.fromhex(parts[1])
        payload = eval(payload_bytes.decode())  # safe: we control the input
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


# ── Public API ──────────────────────────────────────────────────────────

def signup(email: str, password: str, name: str) -> dict:
    """Register a new user. Returns user info (no token — call login)."""
    email = email.strip().lower()
    if not email or not password or not name:
        raise ValueError("email, password, and name are required")
    if len(password) < 6:
        raise ValueError("password must be at least 6 characters")
    if email in _email_index:
        raise ValueError("email already registered")

    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email=email,
        name=name.strip(),
        password_hash=_hash_password(password),
    )
    _users[user_id] = user
    _email_index[email] = user_id
    return {"id": user_id, "email": email, "name": name, "org_id": None, "role": user.role}


def login(email: str, password: str) -> dict:
    """Authenticate and return a JWT token + user info."""
    email = email.strip().lower()
    user_id = _email_index.get(email)
    if not user_id:
        raise ValueError("invalid email or password")
    user = _users[user_id]
    if not _check_password(password, user.password_hash):
        raise ValueError("invalid email or password")

    now = time.time()
    payload = TokenPayload(
        sub=user.id,
        email=user.email,
        org_id=user.org_id,
        role=user.role,
        exp=now + _TOKEN_TTL,
        iat=now,
    )
    token = _encode_jwt({
        "sub": payload.sub,
        "email": payload.email,
        "org_id": payload.org_id,
        "role": payload.role,
        "exp": payload.exp,
        "iat": payload.iat,
    })
    return {
        "token": token,
        "user": {"id": user.id, "email": user.email, "name": user.name, "org_id": user.org_id, "role": user.role},
    }


def verify_token(token: str) -> dict:
    """Validate a JWT and return the decoded payload or raise."""
    payload = _decode_jwt(token)
    if payload is None:
        raise ValueError("invalid or expired token")
    return payload


def get_user(user_id: str) -> Optional[User]:
    return _users.get(user_id)


# ── Self-test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    # quick sanity
    u = signup("a@b.com", "secret123", "Alice")
    assert u["email"] == "a@b.com"
    result = login("a@b.com", "secret123")
    assert "token" in result
    payload = verify_token(result["token"])
    assert payload["sub"] == u["id"]
    print("auth_service.py OK")