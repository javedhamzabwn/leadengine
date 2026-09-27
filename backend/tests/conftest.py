"""Shared fixtures for the LeadEngine backend test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

# Make `backend` importable when pytest runs from the repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend import auth_service, database  # noqa: E402
from backend.main import app  # noqa: E402

REAL_DB = REPO_ROOT / "data" / "leadengine.db"
TEST_ROWS = 400


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    """Scratch DuckDB with a slice of the real company table.

    Points backend.database.DB_PATH at it for the duration of the test.
    """
    db_path = tmp_path / "test.db"
    con = duckdb.connect(str(db_path))
    con.execute(f"ATTACH '{REAL_DB}' AS src (READ_ONLY)")
    con.execute(f"CREATE TABLE company AS SELECT * FROM src.company LIMIT {TEST_ROWS}")
    con.execute("DETACH src")
    con.close()
    database.ensure_aux_tables(db_path)
    monkeypatch.setattr(database, "DB_PATH", db_path)
    return db_path


@pytest.fixture(autouse=True)
def _reset_auth():
    auth_service._reset_storage()
    yield
    auth_service._reset_storage()


@pytest.fixture()
def client(test_db):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def authed_client(client):
    """Client that signed up and logged in; returns (client, token, user)."""
    resp = client.post("/api/v1/auth/signup", json={
        "email": "tester@example.com",
        "password": "s3cur3pass",
        "name": "Tester",
    })
    assert resp.status_code == 201, resp.text
    login = client.post("/api/v1/auth/login", json={
        "email": "tester@example.com",
        "password": "s3cur3pass",
    })
    assert login.status_code == 200, login.text
    token = login.json()["token"]
    user = login.json()["user"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, token, user


def sample_company(test_db, index: int = 0) -> dict:
    con = duckdb.connect(str(test_db), read_only=True)
    try:
        row = con.execute(
            "SELECT * FROM company ORDER BY id LIMIT 1 OFFSET ?", [index]
        ).fetchone()
        keys = [d[0] for d in con.description]
        return dict(zip(keys, row))
    finally:
        con.close()
