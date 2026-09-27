"""Export endpoint tests (GET filters export + POST bulk-id export)."""

from __future__ import annotations

import csv
import io
import json

import duckdb
import pytest

from backend import main as app_main

from .conftest import sample_company


def test_export_csv_attachment_and_header(client):
    r = client.get("/api/v1/companies/export",
                   params={"format": "csv", "has_email": "true"})
    assert r.status_code == 200, r.text
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd and cd.endswith('.csv"')
    assert r.headers["content-type"].startswith("text/csv")
    lines = r.text.splitlines()
    assert lines, "csv must not be empty"
    header = next(csv.reader([lines[0]]))
    assert header[0] == "id" and "name" in header
    # Every data row has the same column count as the header.
    for line in lines[1:]:
        assert len(next(csv.reader([line]))) == len(header)


def test_export_csv_default_columns_allowlisted(client):
    r = client.get("/api/v1/companies/export", params={"format": "csv"})
    header = next(csv.reader([r.text.splitlines()[0]]))
    assert set(header) <= set(app_main.EXPORT_COLUMNS)
    assert "email" in header  # exports may include contact fields


def test_export_csv_custom_columns(client):
    r = client.get("/api/v1/companies/export",
                   params=[("format", "csv"), ("columns", "id"),
                           ("columns", "name"), ("columns", "domain")])
    assert r.status_code == 200, r.text
    header = next(csv.reader([r.text.splitlines()[0]]))
    assert header == ["id", "name", "domain"]


def test_export_csv_bad_column_is_422(client):
    r = client.get("/api/v1/companies/export",
                   params=[("format", "csv"), ("columns", "password_hash")])
    assert r.status_code == 422


def test_export_json_shape(client):
    r = client.get("/api/v1/companies/export", params={"format": "json"})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/json")
    body = json.loads(r.text)
    assert {"exported_at", "count", "items"} <= set(body)
    assert body["count"] == len(body["items"]) > 0


def test_export_xlsx_magic_bytes(client):
    r = client.get("/api/v1/companies/export", params={"format": "xlsx"})
    assert r.status_code == 200, r.text
    assert "spreadsheetml" in r.headers["content-type"]
    assert r.content[:2] == b"PK", "xlsx must be a zip container"
    assert 'attachment; filename="leadengine-companies-' in r.headers["content-disposition"]


def test_export_invalid_format_is_422(client):
    r = client.get("/api/v1/companies/export", params={"format": "pdf"})
    assert r.status_code == 422


def test_export_too_large_returns_400(client, monkeypatch):
    monkeypatch.setattr(app_main, "EXPORT_MAX_ROWS", 2)
    r = client.get("/api/v1/companies/export", params={"format": "csv"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "export_too_large"


def test_bulk_export_by_ids(client, test_db):
    ids = [sample_company(test_db, i)["id"] for i in range(3)]
    r = client.post("/api/v1/companies/export",
                    json={"ids": ids, "format": "csv"})
    assert r.status_code == 200, r.text
    assert "attachment" in r.headers["content-disposition"]
    lines = [ln for ln in r.text.splitlines() if ln.strip()]
    assert len(lines) == 4, "header + 3 selected rows"
    body_ids = {next(csv.reader([ln]))[0] for ln in lines[1:]}
    assert body_ids == set(ids)


def test_bulk_export_json(client, test_db):
    ids = [sample_company(test_db, i)["id"] for i in range(2)]
    r = client.post("/api/v1/companies/export",
                    json={"ids": ids, "format": "json",
                          "columns": ["id", "name"]})
    assert r.status_code == 200, r.text
    body = json.loads(r.text)
    assert body["count"] == 2
    assert {i["id"] for i in body["items"]} == set(ids)
    assert set(body["items"][0]) == {"id", "name"}


def test_bulk_export_empty_ids_is_422(client):
    r = client.post("/api/v1/companies/export",
                    json={"ids": [], "format": "csv"})
    assert r.status_code == 422


def test_bulk_export_unknown_ids_yield_header_only(client):
    r = client.post("/api/v1/companies/export",
                    json={"ids": ["nope-1", "nope-2"], "format": "csv"})
    assert r.status_code == 200, r.text
    lines = [ln for ln in r.text.splitlines() if ln.strip()]
    assert len(lines) == 1, "only the header row when no ids match"
