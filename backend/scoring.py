"""Honest lead scoring for LeadEngine companies.

``lead_score`` is a 0..1 *fit score over unverified data*: it measures how
complete and contactable a company record looks, using only fields present in
the canonical ``company`` table. It is NOT verified intent, NOT a
propensity model, and must always be labeled "fit score (unverified data)"
in the UI together with the per-signal breakdown.

Signal table (from SPECS/API_CONTRACT.md):

    valid email present ............ +0.25
    linkedin URL present ............ +0.15
    phone number present ............ +0.10
    quality_score >= 0.9 ............ +0.15  (0.70..0.90: +0.08)
    operating_status = active ...... +0.10
    website present ................ +0.10
    employee count known ........... +0.05
    founding year known ............. +0.05
    industry known ................. +0.05

Total is capped at 1.0. ``score_signals`` stores the JSON list of
``{signal, points, detail}`` so the UI can show the breakdown.
"""

from __future__ import annotations

import json
from typing import Any

from backend import database

MAX_SCORE = 1.0

# Columns read from the company table for scoring.
SCORE_COLUMNS = [
    "id",
    "email_valid",
    "linkedin",
    "phone_normalized",
    "quality_score",
    "operating_status",
    "website",
    "employees_min",
    "employees_max",
    "founded_year",
    "industry",
]


def _present(value: Any) -> bool:
    """Non-empty string check for optional text fields."""
    return isinstance(value, str) and value.strip() != ""


def score_company(row: dict) -> tuple[float, list[dict]]:
    """Return (lead_score, signals) for one company row dict."""
    signals: list[dict] = []
    total = 0.0

    def add(signal: str, points: float, detail: str) -> None:
        nonlocal total
        total += points
        signals.append({"signal": signal, "points": points, "detail": detail})

    if row.get("email_valid") is True:
        add("valid_email", 0.25, "record has a syntactically valid email address")

    if _present(row.get("linkedin")):
        add("has_linkedin", 0.15, "record has a LinkedIn URL")

    if _present(row.get("phone_normalized")):
        add("has_phone", 0.10, "record has a phone number")

    quality = row.get("quality_score")
    if isinstance(quality, (int, float)):
        if quality >= 0.9:
            add("high_quality", 0.15, f"data quality score {quality:.2f} >= 0.90")
        elif quality >= 0.7:
            add("medium_quality", 0.08, f"data quality score {quality:.2f} in 0.70..0.90")

    if (row.get("operating_status") or "").strip().lower() == "active":
        add("operating_active", 0.10, "operating status is active")

    if _present(row.get("website")):
        add("has_website", 0.10, "company website present")

    if row.get("employees_min") is not None or row.get("employees_max") is not None:
        add("employees_known", 0.05, "employee count known")

    if row.get("founded_year") is not None:
        add("founded_known", 0.05, "founding year known")

    if _present(row.get("industry")):
        add("industry_known", 0.05, "industry known")

    return min(total, MAX_SCORE), signals


def backfill(db_path=None, batch_size: int = 1000) -> dict:
    """Recompute lead_score/score_signals for every company row.

    Scores are computed in Python (single source of truth: score_company),
    bulk-inserted into a staging table, then applied with ONE
    ``UPDATE ... FROM`` statement. This keeps the whole write in a single
    transaction: thousands of individual UPDATEs are pathologically slow
    on this filesystem (COW + fsync per commit), a single statement is not.

    Returns {"rows": n}.
    """
    cols = ", ".join(f'"{c}"' for c in SCORE_COLUMNS)
    with database.write_connection(db_path) as con:
        rows = con.execute(f"SELECT {cols} FROM company").fetchall()

        staged: list[tuple] = []
        for raw in rows:
            row = dict(zip(SCORE_COLUMNS, raw))
            score, signals = score_company(row)
            staged.append((row["id"], score, json.dumps(signals)))

        con.execute("DROP TABLE IF EXISTS _score_stage")
        con.execute(
            "CREATE TABLE _score_stage ("
            "id TEXT PRIMARY KEY, lead_score DOUBLE, score_signals TEXT)"
        )
        for i in range(0, len(staged), batch_size):
            con.executemany(
                "INSERT INTO _score_stage (id, lead_score, score_signals) "
                "VALUES (?, ?, ?)",
                staged[i:i + batch_size],
            )
        con.execute(
            "UPDATE company "
            "SET lead_score = s.lead_score, score_signals = s.score_signals "
            "FROM _score_stage s WHERE company.id = s.id"
        )
        con.execute("DROP TABLE _score_stage")
        return {"rows": len(staged)}


if __name__ == "__main__":
    import sys

    result = backfill()
    print(f"scored {result['rows']} companies")

    # Spot-check the distribution so a degenerate backfill is obvious.
    with database.read_connection() as con:
        stats = con.execute(
            "SELECT COUNT(*), MIN(lead_score), AVG(lead_score), MAX(lead_score), "
            "SUM(CASE WHEN lead_score IS NULL THEN 1 ELSE 0 END) FROM company"
        ).fetchone()
        print(f"count={stats[0]} min={stats[1]:.3f} avg={stats[2]:.3f} "
              f"max={stats[3]:.3f} nulls={stats[4]}")
        sample = con.execute(
            "SELECT name, lead_score, score_signals FROM company "
            "WHERE lead_score IS NOT NULL ORDER BY lead_score DESC LIMIT 2"
        ).fetchall()
        for name, score, signals in sample:
            print(f"  {name}: {score:.2f} -> {signals[:120]}...")
        if stats[4]:
            sys.exit("backfill left NULL lead_score rows")
    print("scoring.py OK")
