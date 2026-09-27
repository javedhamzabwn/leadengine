"""Auth endpoint + token-format tests (SPECS/API_CONTRACT.md)."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path

from backend import auth_service


def _b64url_decode(seg: str) -> bytes:
    return base64.urlsafe_b64decode((seg + "=" * (-len(seg) % 4)).encode())


def test_signup_login_me_roundtrip(authed_client):
    client, token, user = authed_client
    assert set(user) == {"id", "email", "name", "org_id", "role", "created_at"}
    assert user["email"] == "tester@example.com"
    assert "password" not in json.dumps(user)

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200, me.text
    assert me.json()["user"]["id"] == user["id"]


def test_signup_returns_201_and_user_shape(client):
    r = client.post("/api/v1/auth/signup", json={
        "email": "new@example.com", "password": "longenough1", "name": "New",
    })
    assert r.status_code == 201, r.text
    assert r.json()["user"]["email"] == "new@example.com"
    assert "token" not in r.json()


def test_duplicate_signup_is_409_email_taken(client):
    body = {"email": "dup@example.com", "password": "longenough1", "name": "Dup"}
    assert client.post("/api/v1/auth/signup", json=body).status_code == 201
    r = client.post("/api/v1/auth/signup", json=body)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "email_taken"


def test_short_password_is_422(client):
    r = client.post("/api/v1/auth/signup", json={
        "email": "x@example.com", "password": "short", "name": "X",
    })
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_login_bad_password_and_unknown_email_share_401(client):
    client.post("/api/v1/auth/signup", json={
        "email": "u@example.com", "password": "correcthorsebatterystaple1", "name": "U",
    })
    bad_pw = client.post("/api/v1/auth/login", json={
        "email": "u@example.com", "password": "wrongpassword1"})
    unknown = client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com", "password": "correcthorsebatterystaple1"})
    for r in (bad_pw, unknown):
        assert r.status_code == 401, r.text
        err = r.json()["error"]
        assert err["code"] == "invalid_credentials"
    assert bad_pw.json() == unknown.json(), "responses must not allow enumeration"


def test_me_without_token_is_401(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_token"


def test_me_with_garbage_token_is_401(client):
    r = client.get("/api/v1/auth/me",
                   headers={"Authorization": "Bearer not.a.real.token"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_token"


def test_expired_token_is_rejected(client):
    auth_service.signup("exp@example.com", "longenough1", "Exp")
    user_id = auth_service._email_index["exp@example.com"]
    expired = auth_service._encode_jwt(
        {"sub": user_id, "email": "exp@example.com", "org_id": None,
         "role": "member", "iss": "leadengine",
         "iat": time.time() - 100, "exp": time.time() - 10})
    r = client.get("/api/v1/auth/me",
                   headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_token"


def test_tampered_token_is_rejected(client):
    auth_service.signup("t@example.com", "longenough1", "T")
    token = auth_service.login("t@example.com", "longenough1")["token"]
    h, b, s = token.split(".")
    tampered = h + "." + ("A" + b[1:] if not b.startswith("A") else "B" + b[1:]) + "." + s
    assert auth_service._decode_jwt(tampered) is None
    r = client.get("/api/v1/auth/me",
                   headers={"Authorization": f"Bearer {tampered}"})
    assert r.status_code == 401


def test_token_is_standard_jwt_not_hex_eval_format(authed_client):
    _, token, _ = authed_client
    parts = token.split(".")
    assert len(parts) == 3, "JWT must have 3 dot-separated segments"
    # Every segment must be strict base64url (the old code used hex).
    for seg in parts:
        assert seg and all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
                           for c in seg), f"segment is not base64url: {seg[:20]}"
        _b64url_decode(seg)  # must decode without error
    header = json.loads(_b64url_decode(parts[0]).decode())
    assert header == {"alg": "HS256", "typ": "JWT"}
    payload = json.loads(_b64url_decode(parts[1]).decode())
    assert isinstance(payload, dict)
    assert payload["exp"] > time.time()
    # The old implementation parsed the payload with eval(); assert it is gone.
    source = Path(auth_service.__file__).read_text()
    assert "eval(" not in source


def test_password_hash_uses_200k_iterations():
    auth_service.signup("iter@example.com", "longenough1", "Iter")
    stored = auth_service._users[auth_service._email_index["iter@example.com"]].password_hash
    salt_hex, dk_hex = stored.split(":")
    assert len(bytes.fromhex(salt_hex)) == 16
    import hashlib
    expected = hashlib.pbkdf2_hmac(
        "sha256", b"longenough1", bytes.fromhex(salt_hex), 200_000).hex()
    assert expected == dk_hex
