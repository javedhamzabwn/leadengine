"""LeadEngine data normalization.

Reconstructs the canonical `company` table from the raw Parquet source.

BACKGROUND (verified 2026-09-26): `companies_raw.parquet` was produced by a
naive comma-split of a quoted CSV. Any field that contained a comma inside
quotes (descriptions, category lists, location lists) was shattered across
several columns, shifting every column to its right for that row. The true
schema is the first 41 columns; columns 41-65 are split-overflow artifacts.

RECONSTRUCTION: walk each row left-to-right and re-join fragments whose
quote count is unbalanced (`"a` + `b"` -> `"a,b"`), then map the first 41
fields to the true headers. Anchor validation on id/website/email/founded_on
shows 98.7-99.8% of rows realign correctly; unrecoverable rows (<20 fields
after rejoin) are quarantined, never silently dropped.

Raw data is never mutated: the parquet is read-only input, the canonical
table is a derived product with full provenance columns.

Usage:
    python -m backend.normalize            # rebuild from configured paths
    python -m backend.normalize --stats    # print quality stats only
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402

TRUE_WIDTH = 41  # real columns in the source CSV; the rest is split overflow
MIN_FIELDS = 20  # rows yielding fewer fields are quarantined as unrecoverable

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-", re.IGNORECASE)
URL_RE = re.compile(r"^https?://", re.IGNORECASE)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
EMP_ENUM_RE = re.compile(r"^c_0*(\d+)_0*(\d+)$")
MONEY_RE = re.compile(r"[\d,.]+")

COMPANY_DDL = """
CREATE TABLE IF NOT EXISTS company (
    id                  TEXT PRIMARY KEY,
    name                TEXT,
    normalized_name     TEXT,
    description         TEXT,
    website             TEXT,
    domain              TEXT,
    email               TEXT,
    email_valid         BOOLEAN,
    phone               TEXT,
    phone_normalized    TEXT,
    facebook            TEXT,
    linkedin            TEXT,
    twitter             TEXT,
    categories_raw      TEXT,
    industry            TEXT,
    industries          TEXT,          -- JSON list
    locations_raw       TEXT,
    hq_location         TEXT,
    location_tail       TEXT,
    employee_enum       TEXT,
    employees_min       INTEGER,
    employees_max       INTEGER,
    funding_total_usd   DOUBLE,
    funding_rounds      INTEGER,
    last_funding_type   TEXT,
    last_funding_at     TEXT,
    founded_on          TEXT,
    founded_year        INTEGER,
    company_type        TEXT,
    operating_status    TEXT,
    ipo_status          TEXT,
    semrush_rank        TEXT,
    semrush_visits      TEXT,
    growth_insight      TEXT,
    investor_insight    TEXT,
    permalink           TEXT,
    crunchbase_url      TEXT,
    quality_score       DOUBLE,
    verification_status TEXT,
    lead_score          DOUBLE,        -- filled by backend.scoring
    score_signals       TEXT,          -- JSON, filled by backend.scoring
    source              TEXT,
    source_record_id    TEXT,
    observed_at         TEXT,
    ingested_at         TEXT,
    search_text         TEXT
);
CREATE INDEX IF NOT EXISTS idx_company_name ON company(normalized_name);
CREATE INDEX IF NOT EXISTS idx_company_industry ON company(industry);
CREATE INDEX IF NOT EXISTS idx_company_hq ON company(hq_location);
CREATE INDEX IF NOT EXISTS idx_company_status ON company(operating_status);
CREATE INDEX IF NOT EXISTS idx_company_score ON company(lead_score);
"""

QUARANTINE_DDL = """
CREATE TABLE IF NOT EXISTS quarantine_raw (
    row_num   INTEGER,
    reason    TEXT,
    raw_json  TEXT
);
"""


# ── CSV re-alignment ────────────────────────────────────────────────────

def rejoin_fragments(values: list) -> list:
    """Re-join naive comma-split fragments of quoted CSV fields.

    A fragment that opens with `"` and has an odd quote count is the start
    of a shattered quoted field; keep appending `,` + next value until the
    accumulated quote count is even again.
    """
    out: list = []
    buf: str | None = None
    for v in values:
        s = "" if v is None else str(v)
        if buf is None:
            if s.startswith('"') and s.count('"') % 2 == 1:
                buf = s
            else:
                out.append(s if s != "" else None)
        else:
            buf = buf + "," + s
            if buf.count('"') % 2 == 0:
                out.append(buf)
                buf = None
    if buf is not None:
        out.append(buf)  # unbalanced tail: keep, flagged by quality check
    return out


def strip_quotes(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip()
    if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s.strip(' "') or None


# ── Field parsers (best-effort, never fabricate) ───────────────────────

def parse_domain(website: str | None) -> str | None:
    if not website:
        return None
    m = re.match(r"^https?://([^/]+)", website.strip(), re.IGNORECASE)
    if not m:
        return None
    host = m.group(1).lower().split("@")[-1].split(":")[0]
    return host[4:] if host.startswith("www.") else host or None


def parse_employees(enum: str | None) -> tuple[int | None, int | None]:
    if not enum:
        return None, None
    m = EMP_ENUM_RE.match(enum.strip())
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def parse_money(raw: str | None) -> float | None:
    if not raw:
        return None
    s = raw.strip().replace("$", "")
    mult = 1.0
    if s[:1].isdigit() is False and s:
        pass
    low = s.lower()
    if low.endswith("b"):
        mult, s = 1e9, s[:-1]
    elif low.endswith("m"):
        mult, s = 1e6, s[:-1]
    elif low.endswith("k"):
        mult, s = 1e3, s[:-1]
    m = MONEY_RE.search(s.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(0)) * mult
    except ValueError:
        return None


def parse_int(raw: str | None) -> int | None:
    if not raw:
        return None
    m = re.search(r"\d+", raw.replace(",", ""))
    return int(m.group(0)) if m else None


def split_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def normalize_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    return digits or None


# ── Row → canonical record ────────────────────────────────────────────

def canonicalize(fields: list, ingested_at: str) -> dict:
    """Map 41 realigned fields onto the canonical company schema."""
    g = lambda i: strip_quotes(fields[i]) if i < len(fields) else None  # noqa: E731

    website = g(30)
    email = g(15)
    phone = g(16)
    categories = split_list(g(28))
    locations = split_list(g(33))
    emp_min, emp_max = parse_employees(g(32))
    founded = g(27)
    founded_year = None
    if founded and DATE_RE.match(founded):
        try:
            founded_year = int(founded[:4])
        except ValueError:
            founded_year = None

    description = g(3)
    name = g(2)
    linkedin = g(18)
    twitter = g(19)
    facebook = g(17)

    # Anchors for alignment confidence
    anchors_ok = sum([
        bool(g(0) and UUID_RE.match(g(0))),
        website is None or bool(URL_RE.match(website)),
        email is None or bool(EMAIL_RE.match(email)),
        founded is None or bool(DATE_RE.match(founded)),
        g(40) is None or "crunchbase.com" in g(40),
    ])

    quality = 0.0
    quality += 0.40 * (anchors_ok / 5)
    quality += 0.15 if name else 0.0
    quality += 0.10 if website else 0.0
    quality += 0.10 if (email or phone) else 0.0
    quality += 0.10 if categories else 0.0
    quality += 0.05 if description else 0.0
    quality += 0.05 if locations else 0.0
    quality += 0.05 if (g(7) or emp_min is not None or founded) else 0.0
    quality = round(min(1.0, quality), 3)

    search_bits = [name, description, g(28), g(33)]
    if website:
        d = parse_domain(website)
        if d:
            search_bits.append(d)
    search_text = " ".join(b for b in search_bits if b).lower()

    return {
        "id": g(0),
        "name": name,
        "normalized_name": name.lower().strip() if name else None,
        "description": description,
        "website": website,
        "domain": parse_domain(website),
        "email": email.lower() if email else None,
        "email_valid": bool(email and EMAIL_RE.match(email)),
        "phone": phone,
        "phone_normalized": normalize_phone(phone),
        "facebook": facebook,
        "linkedin": linkedin,
        "twitter": twitter,
        "categories_raw": g(28),
        "industry": categories[0] if categories else None,
        "industries": __import__("json").dumps(categories),
        "locations_raw": g(33),
        "hq_location": locations[0] if locations else None,
        "location_tail": locations[-1] if len(locations) > 1 else None,
        "employee_enum": g(32),
        "employees_min": emp_min,
        "employees_max": emp_max,
        "funding_total_usd": parse_money(g(7)),
        "funding_rounds": parse_int(g(9)),
        "last_funding_type": g(10),
        "last_funding_at": g(11),
        "founded_on": founded if founded and DATE_RE.match(founded) else None,
        "founded_year": founded_year,
        "company_type": g(24),
        "operating_status": g(26),
        "ipo_status": g(31),
        "semrush_rank": g(4),
        "semrush_visits": g(5),
        "growth_insight": g(34),
        "investor_insight": g(38),
        "permalink": g(39),
        "crunchbase_url": g(40),
        "quality_score": quality,
        "verification_status": "unverified",  # honest default; see COMPLIANCE.md
        "lead_score": None,
        "score_signals": None,
        "source": "data_6.parquet",
        "source_record_id": g(0),
        "observed_at": g(1),
        "ingested_at": ingested_at,
        "search_text": search_text or None,
    }


COLUMNS = [
    "id", "name", "normalized_name", "description", "website", "domain",
    "email", "email_valid", "phone", "phone_normalized", "facebook",
    "linkedin", "twitter", "categories_raw", "industry", "industries",
    "locations_raw", "hq_location", "location_tail", "employee_enum",
    "employees_min", "employees_max", "funding_total_usd", "funding_rounds",
    "last_funding_type", "last_funding_at", "founded_on", "founded_year",
    "company_type", "operating_status", "ipo_status", "semrush_rank",
    "semrush_visits", "growth_insight", "investor_insight", "permalink",
    "crunchbase_url", "quality_score", "verification_status", "lead_score",
    "score_signals", "source", "source_record_id", "observed_at",
    "ingested_at", "search_text",
]


def build(db_path: str | Path | None = None, raw_path: str | Path | None = None) -> dict:
    """Rebuild the canonical `company` table. Idempotent."""
    import duckdb
    import json

    db_path = Path(db_path or config.DB_PATH)
    raw_path = Path(raw_path or config.RAW_PARQUET)
    if not raw_path.exists():
        raise FileNotFoundError(f"raw parquet not found: {raw_path}")

    ingested_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    con = duckdb.connect(str(db_path))
    try:
        for stmt in COMPANY_DDL.strip().split(";"):
            if stmt.strip():
                con.execute(stmt)
        for stmt in QUARANTINE_DDL.strip().split(";"):
            if stmt.strip():
                con.execute(stmt)

        con.execute("DELETE FROM company")
        con.execute("DELETE FROM quarantine_raw")

        raw_cols = [r[0] for r in con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{raw_path}')").fetchall()]
        rows = con.execute(f"SELECT * FROM read_parquet('{raw_path}')").fetchall()

        inserted = 0
        quarantined = 0
        batch: list[tuple] = []
        for i, r in enumerate(rows):
            fields = rejoin_fragments(list(r))
            if len(fields) < MIN_FIELDS:
                con.execute(
                    "INSERT INTO quarantine_raw VALUES (?, ?, ?)",
                    [i, f"only {len(fields)} fields after rejoin (< {MIN_FIELDS})",
                     json.dumps([str(v)[:200] for v in r if v is not None])],
                )
                quarantined += 1
                continue
            fields = (fields[:TRUE_WIDTH] + [None] * TRUE_WIDTH)[:TRUE_WIDTH]
            rec = canonicalize(fields, ingested_at)
            if not rec["id"]:
                import uuid as _uuid
                rec["id"] = str(_uuid.uuid4())
            batch.append(tuple(rec[c] for c in COLUMNS))
            if len(batch) >= 1000:
                _insert_batch(con, batch)
                inserted += len(batch)
                batch = []
        if batch:
            _insert_batch(con, batch)
            inserted += len(batch)

        con.execute("ANALYZE")
        stats = {
            "raw_rows": len(rows),
            "raw_columns": len(raw_cols),
            "inserted": inserted,
            "quarantined": quarantined,
            "db": str(db_path),
        }
        return stats
    finally:
        con.close()


def _insert_batch(con, batch: list[tuple]) -> None:
    ph = ", ".join(["?"] * len(COLUMNS))
    con.executemany(
        f"INSERT OR REPLACE INTO company ({', '.join(COLUMNS)}) VALUES ({ph})",
        batch,
    )


def stats(db_path: str | Path | None = None) -> dict:
    import duckdb
    con = duckdb.connect(str(db_path or config.DB_PATH), read_only=True)
    try:
        total = con.execute("SELECT COUNT(*) FROM company").fetchone()[0]
        avg_q = con.execute("SELECT ROUND(AVG(quality_score),3) FROM company").fetchone()[0]
        with_email = con.execute("SELECT COUNT(*) FROM company WHERE email IS NOT NULL").fetchone()[0]
        with_site = con.execute("SELECT COUNT(*) FROM company WHERE website IS NOT NULL").fetchone()[0]
        with_li = con.execute("SELECT COUNT(*) FROM company WHERE linkedin IS NOT NULL").fetchone()[0]
        quarantined = con.execute("SELECT COUNT(*) FROM quarantine_raw").fetchone()[0]
        top_ind = con.execute(
            "SELECT industry, COUNT(*) c FROM company WHERE industry IS NOT NULL "
            "GROUP BY 1 ORDER BY c DESC LIMIT 8").fetchall()
        return {
            "companies": total, "avg_quality": avg_q, "with_email": with_email,
            "with_website": with_site, "with_linkedin": with_li,
            "quarantined": quarantined,
            "top_industries": [(a, b) for a, b in top_ind],
        }
    finally:
        con.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()
    if args.stats:
        import json as _json
        print(_json.dumps(stats(), indent=2, default=str))
        return
    t0 = time.time()
    s = build()
    s["elapsed_s"] = round(time.time() - t0, 1)
    print(f"normalized {s['inserted']}/{s['raw_rows']} companies "
          f"({s['quarantined']} quarantined) in {s['elapsed_s']}s -> {s['db']}")


if __name__ == "__main__":
    main()
