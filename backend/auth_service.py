"""
LeadEngine Authentication Service.

Standard JWT (RFC 7519) using only the standard library:
  base64url(header) . base64url(payload) . base64url(HMAC-SHA256 signature)

The header and payload are JSON objects serialized with the compact encoding.
Payloads are decoded with ``json.loads`` only. There is deliberately no
dynamic code execution anywhere in the token path.

Passwords: PBKDF2-HMAC-SHA256, 200,000 iterations, 16-byte random salt,
stored as ``salt_hex:derived_key_hex``.

The signing secret comes from the ``LEADENGINE_JWT_SECRET`` environment
variable. When it is unset a hard-coded development secret is used; it must
never be relied on outside local development.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


# ── Config ──────────────────────────────────────────────────────────────

_DEV_FALLBACK_SECRET = "dev-secret-change-me"  # local development only
_ISSUER = "leadengine"
_TOKEN_TTL = 86400 * 7  # 7 days
_PBKDF2_ITERATIONS = 200_000
_SALT_BYTES = 16


def _secret() -> str:
    """Signing secret, read lazily so tests and shells can set the env var."""
    return os.environ.get("LEADENGINE_JWT_SECRET") or _DEV_FALLBACK_SECRET


def is_dev_secret() -> bool:
    """True when the development fallback secret is in effect."""
    return not os.environ.get("LEADENGINE_JWT_SECRET")


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
    iss: str = _ISSUER


# ── Storage ─────────────────────────────────────────────────────────────
# In-memory dict; swap for a persistent store when multi-process.
_users: dict[str, User] = {}       # id -> User
_email_index: dict[str, str] = {}  # email -> id


def _reset_storage() -> None:
    """Clear all users. Intended for tests only."""
    _users.clear()
    _email_index.clear()


# ── Password hashing ────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256, 200k iterations, 16-byte salt -> 'salt_hex:dk_hex'."""
    salt = os.urandom(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return salt.hex() + ":" + dk.hex()


def _check_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
        return hmac.compare_digest(expected.hex(), dk_hex)
    except (ValueError, TypeError, AttributeError):
        return False


# ── JWT (standard base64url JSON, HS256) ────────────────────────────────

def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    if not isinstance(data, str) or not data:
        raise ValueError("empty base64url segment")
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def _encode_jwt(payload: dict) -> str:
    header = _b64url_encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode("utf-8")
    )
    body = _b64url_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{header}.{body}".encode("ascii")
    signature = hmac.new(_secret().encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url_encode(signature)}"


def _decode_jwt(token: str) -> Optional[dict]:
    """Verify signature and expiry; return the JSON payload dict or None."""
    try:
        if not isinstance(token, str):
            return None
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, body_b64, sig_b64 = parts

        signing_input = f"{header_b64}.{body_b64}".encode("ascii")
        expected = hmac.new(_secret().encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected, actual):
            return None

        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
        if not isinstance(header, dict) or header.get("alg") != "HS256":
            return None

        payload = json.loads(_b64url_decode(body_b64).decode("utf-8"))
        if not isinstance(payload, dict):
            return None
        if payload.get("iss") not in (None, _ISSUER):
            return None
        exp = payload.get("exp")
        if exp is None:
            return None
        if float(exp) < time.time():
            return None
        return payload
    except Exception:
        return None


def _public_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "org_id": user.org_id,
        "role": user.role,
        "created_at": user.created_at,
    }


# ── Public API ──────────────────────────────────────────────────────────

def signup(email: str, password: str, name: str) -> dict:
    """Register a new user. Returns the public user dict (no token)."""
    email = (email or "").strip().lower()
    name = (name or "").strip()
    if not email or not password or not name:
        raise ValueError("email, password, and name are required")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("email is not valid")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    if email in _email_index:
        raise ValueError("email already registered")

    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email=email,
        name=name,
        password_hash=_hash_password(password),
    )
    _users[user_id] = user
    _email_index[email] = user_id
    return _public_user(user)


def login(email: str, password: str) -> dict:
    """Authenticate and return a JWT token plus the public user dict."""
    email = (email or "").strip().lower()
    user_id = _email_index.get(email)
    user = _users.get(user_id) if user_id else None
    # Same message for unknown email and wrong password: no user enumeration.
    if user is None or not _check_password(password or "", user.password_hash):
        raise ValueError("invalid email or password")

    now = time.time()
    token = _encode_jwt({
        "sub": user.id,
        "email": user.email,
        "org_id": user.org_id,
        "role": user.role,
        "iss": _ISSUER,
        "iat": now,
        "exp": now + _TOKEN_TTL,
    })
    return {"token": token, "user": _public_user(user)}


def verify_token(token: str) -> dict:
    """Validate a JWT and return the decoded payload, else raise ValueError."""
    payload = _decode_jwt(token)
    if payload is None:
        raise ValueError("invalid or expired token")
    return payload


def get_user(user_id: str) -> Optional[User]:
    return _users.get(user_id)


# ── Self-test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import re

    _reset_storage()

    # 1. Round trip: signup -> login -> verify
    u = signup("alice@example.com", "s3cur3pass", "Alice")
    assert u["email"] == "alice@example.com"
    assert "password_hash" not in u
    result = login("alice@example.com", "s3cur3pass")
    token = result["token"]
    assert isinstance(token, str)

    # 2. Standard JWT shape: three base64url segments, JSON header/payload
    parts = token.split(".")
    assert len(parts) == 3, "token must have 3 dot-separated segments"
    b64url_re = re.compile(r"^[A-Za-z0-9_-]+$")
    assert all(b64url_re.match(p) for p in parts), "segments must be base64url"
    header = json.loads(_b64url_decode(parts[0]).decode("utf-8"))
    assert header == {"alg": "HS256", "typ": "JWT"}, header
    payload = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
    assert isinstance(payload, dict) and payload["sub"] == u["id"]

    payload2 = verify_token(token)
    assert payload2["sub"] == u["id"]

    # 3. Wrong password and unknown email give the same error
    for bad_email, bad_pw in (("alice@example.com", "wrongpass1"), ("nobody@example.com", "s3cur3pass")):
        try:
            login(bad_email, bad_pw)
            raise AssertionError("login should have failed")
        except ValueError as e:
            assert str(e) == "invalid email or password"

    # 4. Duplicate signup rejected
    try:
        signup("alice@example.com", "anotherpass1", "Alice 2")
        raise AssertionError("duplicate signup should have failed")
    except ValueError as e:
        assert str(e) == "email already registered"

    # 5. Tampered token rejected (signature mismatch)
    tampered = parts[0] + "." + parts[1][:-2] + ("AA" if not parts[1].endswith("AA") else "BB") + "." + parts[2]
    assert _decode_jwt(tampered) is None

    # 6. Expired token rejected
    expired = _encode_jwt({"sub": u["id"], "exp": time.time() - 10, "iat": time.time() - 20})
    assert _decode_jwt(expired) is None
    try:
        verify_token(expired)
        raise AssertionError("expired token should have failed")
    except ValueError:
        pass

    # 7. Old hex-token format is rejected (non-JSON payload segment)
    old_style = parts[0] + "." + "{'sub': 'x'}".encode().hex() + "." + parts[2]
    assert _decode_jwt(old_style) is None

    # 8. Password hash format and iteration count sanity
    stored = _users[u["id"]].password_hash
    salt_hex, dk_hex = stored.split(":")
    assert len(bytes.fromhex(salt_hex)) == 16
    assert _check_password("s3cur3pass", stored) and not _check_password("nope", stored)

    # 9. get_user
    assert get_user(u["id"]).email == "alice@example.com"
    assert get_user("missing") is None

    print("auth_service.py OK")
