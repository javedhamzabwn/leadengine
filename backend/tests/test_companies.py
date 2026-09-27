"""Company search, detail, facets, and cursor-pagination tests."""

from __future__ import annotations

import duckdb

from .conftest import sample_company

SUMMARY_KEYS = {
    "id", "name", "domain", "website", "industry", "hq_location",
    "employee_enum", "employees_min", "employees_max", "founded_year",
    "operating_status", "has_email", "has_phone", "has_linkedin",
    "quality_score", "lead_score", "verification_status",
}


def test_list_default_page_shape(client):
    r = client.get("/api/v1/companies")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"items", "next_cursor", "limit"}
    assert body["limit"] == 25
    assert len(body["items"]) == 25
    item = body["items"][0]
    assert set(item) == SUMMARY_KEYS, set(item) ^ SUMMARY_KEYS
    assert "email" not in item, "raw emails must not appear in list view"
    assert item["verification_status"] == "unverified"


def test_q_filter_matches_search_text(client, test_db):
    company = sample_company(test_db)
    name = (company["name"] or "").strip()
    assert len(name) >= 2
    q = name[:6] if len(name) >= 6 else name
    r = client.get("/api/v1/companies", params={"q": q, "limit": 100})
    assert r.status_code == 200, r.text
    ids = [i["id"] for i in r.json()["items"]]
    assert company["id"] in ids


def test_q_too_short_is_422(client):
    r = client.get("/api/v1/companies", params={"q": "x"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_industry_filter(client):
    facets = client.get("/api/v1/companies/facets").json()
    assert facets["industries"], "test db should have industries"
    industry = facets["industries"][0]["value"]
    r = client.get("/api/v1/companies",
                   params=[("industry", industry), ("limit", 100)])
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert items
    assert all(i["industry"] == industry for i in items)


def test_industry_repeatable(client):
    facets = client.get("/api/v1/companies/facets").json()
    values = [f["value"] for f in facets["industries"][:2]]
    r = client.get("/api/v1/companies",
                   params=[("industry", values[0]), ("industry", values[1]),
                           ("limit", 100)])
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert items
    assert all(i["industry"] in values for i in items)


def test_has_email_filter(client):
    r = client.get("/api/v1/companies",
                   params={"has_email": "true", "limit": 100})
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert items
    assert all(i["has_email"] is True for i in items)


def test_has_phone_and_linkedin_filters(client):
    for param in ("has_phone", "has_linkedin"):
        r = client.get("/api/v1/companies", params={param: "true", "limit": 100})
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert items
        key = param  # has_phone / has_linkedin match summary keys
        assert all(i[key] is True for i in items), param


def test_min_quality_filter(client):
    r = client.get("/api/v1/companies",
                   params={"min_quality": 0.9, "limit": 100})
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert items
    assert all((i["quality_score"] or 0) >= 0.9 for i in items)


def test_min_quality_out_of_range_is_422(client):
    r = client.get("/api/v1/companies", params={"min_quality": 1.5})
    assert r.status_code == 422


def test_location_filter(client):
    facets = client.get("/api/v1/companies/facets").json()
    assert facets["locations"]
    loc = facets["locations"][0]["value"]
    r = client.get("/api/v1/companies", params={"location": loc[:8], "limit": 100})
    assert r.status_code == 200, r.text
    assert r.json()["items"]


def test_employees_range_overlap(client, test_db):
    con = duckdb.connect(str(test_db), read_only=True)
    row = con.execute(
        "SELECT employees_min, employees_max FROM company "
        "WHERE employees_min IS NOT NULL AND employees_max IS NOT NULL LIMIT 1"
    ).fetchone()
    con.close()
    assert row, "test db should have a company with known employee range"
    emin, emax = row
    r = client.get("/api/v1/companies",
                   params={"employees_min": emin, "employees_max": emax,
                           "limit": 100})
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert items
    for i in items:
        cmin = i["employees_min"] if i["employees_min"] is not None else 0
        cmax = i["employees_max"] if i["employees_max"] is not None else 2**31 - 1
        assert cmin <= emax and cmax >= emin, "ranges must overlap"


def test_sort_name_asc_orders(client):
    r = client.get("/api/v1/companies",
                   params={"sort": "name", "dir": "asc", "limit": 50})
    assert r.status_code == 200, r.text
    names = [(i["name"] or "") for i in r.json()["items"]]
    assert names == sorted(names, key=str.lower) or names == sorted(names)


def test_invalid_sort_is_422(client):
    r = client.get("/api/v1/companies", params={"sort": "password_hash"})
    assert r.status_code == 422


def test_limit_bounds(client):
    assert client.get("/api/v1/companies", params={"limit": 0}).status_code == 422
    assert client.get("/api/v1/companies", params={"limit": 101}).status_code == 422
    r = client.get("/api/v1/companies", params={"limit": 100})
    assert r.status_code == 200 and r.json()["limit"] == 100


def test_cursor_pagination_pages_forward_without_duplicates(client):
    seen: list[str] = []
    cursor = None
    pages = 0
    while True:
        params = {"limit": 5}
        if cursor:
            params["cursor"] = cursor
        r = client.get("/api/v1/companies", params=params)
        assert r.status_code == 200, r.text
        body = r.json()
        ids = [i["id"] for i in body["items"]]
        assert ids, "each page should have items"
        assert not (set(ids) & set(seen)), "pages must not repeat rows"
        seen.extend(ids)
        pages += 1
        cursor = body["next_cursor"]
        if cursor is None or pages >= 4:
            break
    assert pages >= 3, "should walk several pages"
    assert len(seen) == len(set(seen)) == pages * 5


def test_cursor_pagination_default_sort_is_stable(client):
    # Default sort is quality_score desc; walk two pages and check ordering.
    p1 = client.get("/api/v1/companies", params={"limit": 10}).json()
    p2 = client.get("/api/v1/companies",
                    params={"limit": 10, "cursor": p1["next_cursor"]}).json()
    scores = [(i["quality_score"] if i["quality_score"] is not None else -1)
              for i in p1["items"] + p2["items"]]
    assert scores == sorted(scores, reverse=True)


def test_invalid_cursor_is_422(client):
    r = client.get("/api/v1/companies", params={"cursor": "!!!not-a-cursor!!!"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_cursor"


def test_detail_returns_full_shape(client, test_db):
    company = sample_company(test_db)
    r = client.get(f"/api/v1/companies/{company['id']}")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["id"] == company["id"]
    assert d["verification_status"] == "unverified"
    assert isinstance(d["score_signals"], list)
    assert isinstance(d["industries"], list)
    for key in ("description", "email", "email_valid", "phone", "linkedin",
                "funding_total_usd", "founded_year", "crunchbase_url",
                "source", "observed_at"):
        assert key in d, key


def test_detail_unknown_id_is_404(client):
    r = client.get("/api/v1/companies/does-not-exist")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_facets_shape(client):
    r = client.get("/api/v1/companies/facets")
    assert r.status_code == 200, r.text
    f = r.json()
    assert set(f) == {"industries", "locations", "operating_statuses",
                      "employee_ranges"}
    for key in ("industries", "locations", "operating_statuses"):
        assert f[key], key
        assert set(f[key][0]) == {"value", "count"}
        counts = [x["count"] for x in f[key]]
        assert counts == sorted(counts, reverse=True)
    assert f["employee_ranges"]
    assert set(f["employee_ranges"][0]) == {"value", "label", "count"}


def test_health_reports_db_rows(client, test_db):
    r = client.get("/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "leadengine-api"
    assert body["version"] == "1.0.0"
    con = duckdb.connect(str(test_db), read_only=True)
    expected = con.execute("SELECT COUNT(*) FROM company").fetchone()[0]
    con.close()
    assert body["db_rows"] == expected
