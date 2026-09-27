"""Saved-search and favorite CRUD tests."""

from __future__ import annotations

from .conftest import sample_company


# ── Saved searches ────────────────────────────────────────────────────

def test_saved_search_crud(client):
    # Create
    r = client.post("/api/v1/saved-searches", json={
        "name": "SaaS with email",
        "filters": {"industry": ["Software"], "has_email": True},
    })
    assert r.status_code == 201, r.text
    created = r.json()
    assert set(created) == {"id", "name", "filters", "created_at"}
    assert created["filters"] == {"industry": ["Software"], "has_email": True}

    # List
    listed = client.get("/api/v1/saved-searches").json()
    assert len(listed["items"]) == 1
    assert listed["items"][0]["id"] == created["id"]

    # Delete
    d = client.delete(f"/api/v1/saved-searches/{created['id']}")
    assert d.status_code == 204
    assert client.get("/api/v1/saved-searches").json()["items"] == []


def test_saved_search_delete_missing_is_404(client):
    r = client.delete("/api/v1/saved-searches/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_saved_search_name_required(client):
    r = client.post("/api/v1/saved-searches",
                    json={"name": "   ", "filters": {}})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_saved_search_filters_must_be_object(client):
    r = client.post("/api/v1/saved-searches",
                    json={"name": "x", "filters": ["not", "an", "object"]})
    assert r.status_code == 422


# ── Favorites ─────────────────────────────────────────────────────────

def _fav_ids(client, test_db, n=3):
    return [sample_company(test_db, i)["id"] for i in range(n)]


def test_favorite_crud(client, test_db):
    company_id = _fav_ids(client, test_db, 1)[0]

    # Add
    r = client.post(f"/api/v1/companies/{company_id}/favorites")
    assert r.status_code == 201, r.text
    assert r.json()["company_id"] == company_id
    assert r.json()["created_at"] > 0

    # Idempotent re-add
    r2 = client.post(f"/api/v1/companies/{company_id}/favorites")
    assert r2.status_code == 201
    assert r2.json()["created_at"] == r.json()["created_at"]

    # List contains it
    favs = client.get("/api/v1/favorites").json()
    assert [i["id"] for i in favs["items"]] == [company_id]
    assert favs["next_cursor"] is None

    # Remove
    assert client.delete(f"/api/v1/companies/{company_id}/favorites").status_code == 204
    assert client.get("/api/v1/favorites").json()["items"] == []

    # Removing again is 404
    r3 = client.delete(f"/api/v1/companies/{company_id}/favorites")
    assert r3.status_code == 404
    assert r3.json()["error"]["code"] == "not_found"


def test_favorite_unknown_company_is_404(client):
    r = client.post("/api/v1/companies/no-such-id/favorites")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_favorites_pagination(client, test_db):
    ids = _fav_ids(client, test_db, 6)
    for cid in ids:
        assert client.post(f"/api/v1/companies/{cid}/favorites").status_code == 201

    seen: list[str] = []
    cursor = None
    pages = 0
    while True:
        params = {"limit": 2}
        if cursor:
            params["cursor"] = cursor
        body = client.get("/api/v1/favorites", params=params).json()
        page_ids = [i["id"] for i in body["items"]]
        assert page_ids
        assert not (set(page_ids) & set(seen))
        seen.extend(page_ids)
        pages += 1
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert pages == 3
    assert set(seen) == set(ids)
    item = client.get("/api/v1/favorites", params={"limit": 1}).json()["items"][0]
    assert "email" not in item, "favorites list uses the summary shape"
