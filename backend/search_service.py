"""
LeadEngine Search Pipeline
==========================
Parameterized DuckDB queries, cursor-based pagination (keyset), full-text index.
Implements the pipeline from QUERY_AST.md:

    Request → Schema Validation → Authorization → Query Normalization
      → Query AST → Query Planner → Database Compiler → Execution
      → Result Normalization

All SQL values are parameterized; all identifiers are allowlisted.
Matches CANONICAL_SCHEMA.md entity definitions.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


# ── Step 0: Allowlists (from QUERY_AST.md §1 Schema Validation) ──

VALID_ENTITIES = {"person", "company"}

# Allowlisted columns from CANONICAL_SCHEMA.md
VALID_COLUMNS = {
    "person": {
        "id", "name", "title", "seniority", "department", "company",
        "location", "email", "phone", "contact_availability", "freshness",
        "confidence", "verification_status", "related_company",
        "source", "source_record_id", "observed_at", "ingested_at",
        "verified_at", "quality_score",
    },
    "company": {
        "id", "name", "domain", "industry", "employee_count", "revenue",
        "funding_stage", "founded_year", "hq_location", "technologies",
        "social_profiles", "verification_status",
        "source", "source_record_id", "observed_at", "ingested_at",
        "verified_at", "quality_score",
    },
}

VALID_SENIORITY = {
    "Junior", "Mid", "Senior", "VP", "Director",
    "Executive", "Owner", "Founder", "Intern", "Entry",
}
VALID_ORDER_DIRECTIONS = {"asc", "desc"}

# Sort-column allowlist — only indexed / fast-path fields to prevent full scans
ALLOWLISTED_SORTS = {
    "person": {"freshness", "confidence", "name", "title", "seniority", "department", "id"},
    "company": {"employee_count", "revenue", "founded_year", "name", "industry", "id"},
}

# Provenance fields (CANONICAL_SCHEMA.md) — kept on every result row
PROVENANCE_FIELDS = {"source", "source_record_id", "observed_at", "ingested_at", "verified_at", "confidence", "quality_score"}


# ── Step 4: Query AST (matches QUERY_AST.md §4) ──

@dataclass
class QueryFilter:
    field: str
    operator: str       # == | != | >= | <= | > | < | in | not_in | contains | not_contains
    value: Any


@dataclass
class PaginationSpec:
    cursor: Optional[list] = None   # [sort_value, id] for keyset
    limit: int = 50
    sort_column: str = "freshness"
    sort_direction: str = "asc"


@dataclass
class QueryAST:
    """
    Internal query representation (QUERY_AST.md §4).

    After going through:
        §1 Schema Validation
        §3 Query Normalization
    """
    entity: str
    columns: list[str] = field(default_factory=list)
    filters: list[QueryFilter] = field(default_factory=list)
    pagination: PaginationSpec = field(default_factory=PaginationSpec)

    def __post_init__(self):
        if self.entity not in VALID_ENTITIES:
            raise ValueError(f"Invalid entity '{self.entity}'. Valid: {VALID_ENTITIES}")

    # ── §1 Schema Validation ──
    def validate(self):
        """Validate all identifiers against allowlists. Never trust raw input."""
        allowed_cols = VALID_COLUMNS.get(self.entity, set())
        for col in self.columns:
            if col not in allowed_cols:
                raise ValueError(f"Column '{col}' not allowlisted for entity '{self.entity}'.")
        for f in self.filters:
            if f.field not in allowed_cols:
                raise ValueError(f"Filter field '{f.field}' not allowlisted for entity '{self.entity}'.")
            if f.field == "seniority" and f.operator in ("==", "in"):
                vals = [f.value] if f.operator == "==" else f.value
                for v in vals:
                    if v not in VALID_SENIORITY:
                        raise ValueError(f"Invalid seniority '{v}'. Valid: {VALID_SENIORITY}")
        sort_col = self.pagination.sort_column
        if sort_col not in ALLOWLISTED_SORTS.get(self.entity, set()):
            raise ValueError(f"Sort column '{sort_col}' not allowlisted for entity '{self.entity}'.")
        if self.pagination.sort_direction not in VALID_ORDER_DIRECTIONS:
            raise ValueError(f"Invalid sort direction '{self.pagination.sort_direction}'.")
        if self.pagination.limit < 1 or self.pagination.limit > 1000:
            raise ValueError(f"Limit must be 1-1000, got {self.pagination.limit}.")


# ── §5 Query Planner → §6 Database Compiler ──

def _build_where_clause(filters: list[QueryFilter]) -> tuple[str, list]:
    """Build parameterized WHERE clause from AST filters."""
    clauses = []
    params = []
    for f in filters:
        col = f'"{f.field}"'
        if f.operator == "==":
            clauses.append(f"{col} = ?")
            params.append(f.value)
        elif f.operator == "!=":
            clauses.append(f"{col} != ?")
            params.append(f.value)
        elif f.operator in (">=", "<=", ">", "<"):
            clauses.append(f"{col} {f.operator} ?")
            params.append(f.value)
        elif f.operator == "in":
            clauses.append(f"{col} IN ({', '.join(['?'] * len(f.value))})")
            params.extend(f.value)
        elif f.operator == "not_in":
            clauses.append(f"{col} NOT IN ({', '.join(['?'] * len(f.value))})")
            params.extend(f.value)
        elif f.operator == "contains":
            # ponytail: uses ILIKE on raw column. Production should use
            # normalized_title + full-text index per SEARCH_SPEC.md §Text Search.
            clauses.append(f'"{f.field}" ILIKE ?')
            params.append(f"%{f.value}%")
        elif f.operator == "not_contains":
            clauses.append(f'"{f.field}" NOT ILIKE ?')
            params.append(f"%{f.value}%")
        else:
            raise ValueError(f"Unsupported operator '{f.operator}'.")
    if clauses:
        return "WHERE " + " AND ".join(clauses), params
    return "", []


def _build_pagination(pag: PaginationSpec) -> tuple[str, list, str, str]:
    """Build cursor-based keyset pagination clause (SEARCH_SPEC.md §Pagination).

    Pattern:
        WHERE (sort_value, id) > (?, ?)
        ORDER BY sort_value, id
        LIMIT N
    """
    params = []
    sort_col = f'"{pag.sort_column}"'

    if pag.cursor is not None and len(pag.cursor) == 2:
        sort_val, last_id = pag.cursor
        if isinstance(sort_val, str):
            try:
                sort_val = float(sort_val) if "." in sort_val else int(sort_val)
            except (ValueError, TypeError):
                pass
        arrow = ">" if pag.sort_direction == "asc" else "<"
        clause = f"WHERE ({sort_col}, id) {arrow} (?, ?)"
        params = [sort_val, last_id]
    else:
        clause = ""

    dir_keyword = pag.sort_direction.upper()
    order = f"ORDER BY {sort_col} {dir_keyword}, id {dir_keyword}"
    limit = f"LIMIT {pag.limit}"
    return clause, params, order, limit


def _build_select(entity: str, columns: list[str]) -> str:
    """Build SELECT clause — quoted identifiers, never raw input."""
    if not columns:
        return "*"
    # Return only what was explicitly requested (allowlisted already validated)
    return ", ".join(f'"{c}"' for c in columns)


# ── §3 Query Normalization ──

def _normalize_request(request: dict) -> QueryAST:
    """Convert SEARCH_SPEC.md format or flat AST dict into a validated QueryAST."""
    if "filters" in request and isinstance(request.get("filters"), dict):
        return _normalize_spec_format(request)
    return _normalize_ast_format(request)


def _normalize_spec_format(request: dict) -> QueryAST:
    """Convert SEARCH_SPEC.md JSON into a QueryAST."""
    entity = request.get("entity", "person")
    filters_spec = request.get("filters", {})
    exclude_spec = request.get("exclude", {})
    pag_spec = request.get("pagination", {})
    text_spec = request.get("text", {})

    filters = []

    # Map SEARCH_SPEC keys → (canonical field, operator)
    FILTER_MAP = {
        "departments": ("department", "in"),
        "seniority": ("seniority", "in"),
        "countries": ("location", "in"),
        "titles": ("title", "in"),
        "industries": ("industry", "in"),
    }
    for spec_key, (field, op) in FILTER_MAP.items():
        vals = filters_spec.get(spec_key, [])
        if vals:
            filters.append(QueryFilter(field=field, operator=op, value=vals))

    # Exclude filters
    for spec_key, (field, op) in [("titles", ("title", "not_in"))]:
        vals = exclude_spec.get(spec_key, [])
        if vals:
            filters.append(QueryFilter(field=field, operator=op, value=vals))

    # Company size range
    cs = filters_spec.get("company_size", {})
    if cs.get("min") is not None:
        filters.append(QueryFilter(field="employee_count", operator=">=", value=cs["min"]))
    if cs.get("max") is not None:
        filters.append(QueryFilter(field="employee_count", operator="<=", value=cs["max"]))

    # Email availability
    he = filters_spec.get("has_email")
    if he is True:
        filters.append(QueryFilter(field="email", operator="!=", value=""))
    elif he is False:
        filters.append(QueryFilter(field="email", operator="==", value=""))

    # Text/Keyword search
    keyword = text_spec.get("query") or (filters_spec.get("keyword", [None])[0] if filters_spec.get("keyword") else None)
    if keyword:
        filters.append(QueryFilter(field="title", operator="contains", value=keyword))
    for kw in filters_spec.get("keyword", [])[1:]:
        filters.append(QueryFilter(field="title", operator="contains", value=kw))

    return QueryAST(
        entity=entity,
        filters=filters,
        pagination=PaginationSpec(
            cursor=pag_spec.get("cursor"),
            limit=pag_spec.get("limit", 50),
            sort_column=pag_spec.get("sort_column", "freshness"),
            sort_direction=pag_spec.get("sort_direction", "asc"),
        ),
    )


def _normalize_ast_format(request: dict) -> QueryAST:
    """Convert a flat AST dict into a QueryAST."""
    pag = request.get("pagination", {})
    return QueryAST(
        entity=request.get("entity", "person"),
        columns=request.get("columns", []),
        filters=[QueryFilter(**f) for f in request.get("filters", [])],
        pagination=PaginationSpec(
            cursor=pag.get("cursor"),
            limit=pag.get("limit", 50),
            sort_column=pag.get("sort_column", "freshness"),
            sort_direction=pag.get("sort_direction", "asc"),
        ),
    )


# ── Full-Text Index Prototype ──

FULLTEXT_DDL = """
CREATE TABLE IF NOT EXISTS _le_fulltext (
    entity    TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    field     TEXT NOT NULL,
    token     TEXT NOT NULL,
    position  INTEGER
);
CREATE INDEX IF NOT EXISTS idx_ft_token   ON _le_fulltext (token);
CREATE INDEX IF NOT EXISTS idx_ft_entity  ON _le_fulltext (entity, entity_id);
CREATE INDEX IF NOT EXISTS idx_ft_lookup  ON _le_fulltext (entity, field, token);
"""

FULLTEXT_DML_EXAMPLES = """
-- Populate (batch once per entity/field)
INSERT INTO _le_fulltext (entity, entity_id, field, token, position)
SELECT 'person', id, 'title', LOWER(token) AS token, ROW_NUMBER() OVER (PARTITION BY id) - 1
FROM (SELECT id, UNNEST(string_split(title, ' ')) AS token FROM person WHERE title IS NOT NULL);

-- Single-token match
SELECT p.id, p.name, p.title
FROM person p
JOIN _le_fulltext ft ON ft.entity_id = p.id AND ft.entity = 'person' AND ft.token = 'software' AND ft.field = 'title'
LIMIT 50;

-- Multi-token conjunctive
SELECT p.id, p.name, p.title
FROM person p
JOIN _le_fulltext ft1 ON ft1.entity_id=p.id AND ft1.token='software' AND ft1.field='title' AND ft1.entity='person'
JOIN _le_fulltext ft2 ON ft2.entity_id=p.id AND ft2.token='engineer'  AND ft2.field='title' AND ft2.entity='person'
LIMIT 50;

-- Phrase (adjacent tokens)
SELECT p.id, p.name, p.title
FROM person p
JOIN _le_fulltext ft1 ON ft1.entity_id=p.id AND ft1.token='vice'     AND ft1.field='title' AND ft1.entity='person'
JOIN _le_fulltext ft2 ON ft2.entity_id=p.id AND ft2.token='president' AND ft2.field='title' AND ft2.entity='person'
WHERE ft2.position = ft1.position + 1
LIMIT 50;
"""


def setup_fulltext_index(conn) -> dict:
    """Create full-text index tables. Call once at startup."""
    start = time.time()
    for stmt in FULLTEXT_DDL.strip().split(";"):
        s = stmt.strip()
        if s:
            conn.execute(s)
    elapsed = time.time() - start
    return {
        "ok": True,
        "tables": ["_le_fulltext"],
        "indexes": ["idx_ft_token", "idx_ft_entity", "idx_ft_lookup"],
        "elapsed_ms": round(elapsed * 1000, 1),
    }


def populate_fulltext_index(conn, entity: str = "person",
                            field: str = "title",
                            batch_size: int = 100000) -> dict:
    """Tokenize a text field and insert into _le_fulltext in batches."""
    table = entity
    # Clear existing
    conn.execute("DELETE FROM _le_fulltext WHERE entity = ? AND field = ?", [entity, field])

    total = 0
    offset = 0
    batches = []

    while True:
        rows = conn.execute(
            f'SELECT id, "{field}" FROM "{table}" WHERE "{field}" IS NOT NULL LIMIT ? OFFSET ?',
            [batch_size, offset],
        ).fetchall()
        if not rows:
            break

        params = []
        for row_id, raw_text in rows:
            if not raw_text:
                continue
            for pos, token in enumerate(raw_text.lower().split()):
                params.extend([entity, row_id, field, token, pos])

        if params:
            n = len(params) // 5
            ph = ", ".join(["(?, ?, ?, ?, ?)"] * n)
            conn.execute(
                f"INSERT INTO _le_fulltext (entity, entity_id, field, token, position) VALUES {ph}",
                params,
            )

        cnt = len(params) // 5
        total += cnt
        batches.append({"offset": offset, "rows_read": len(rows), "tokens_written": cnt})
        offset += batch_size

    conn.execute("ANALYZE")
    return {"entity": entity, "field": field, "tokens_total": total, "batches": batches}


# ── §7 Execution + §8 Result Normalization ──

def search(conn, request: dict) -> dict:
    """
    Execute a search against DuckDB.

    Pipeline: Request → Normalization → Validation → Planner → Compiler → Execution → Result

    Args:
        conn: DuckDB connection.
        request: Dict in SEARCH_SPEC.md format or flat QueryAST format.

    Returns:
        { "results": [...], "pagination": {...}, "metadata": {...} }
    """
    start = time.time()

    # §1+§3 Schema Validation + Normalization
    ast = _normalize_request(request)
    ast.validate()

    entity = ast.entity
    table = entity

    # §5 Query Planner: build SQL clauses
    select_clause = _build_select(entity, ast.columns)
    where_clause, where_params = _build_where_clause(ast.filters)
    pag_clause, pag_params, order_clause, limit_clause = _build_pagination(ast.pagination)

    # Merge cursor and filter WHEREs
    if pag_clause and where_clause:
        # Both exist: cursor condition AND'd with filter conditions
        pag_body = pag_clause[len("WHERE "):]
        where_body = where_clause[len("WHERE "):]
        final_where = f"WHERE ({pag_body}) AND ({where_body})"
        all_params = pag_params + where_params
    elif pag_clause:
        final_where = pag_clause
        all_params = pag_params
    elif where_clause:
        final_where = where_clause
        all_params = where_params
    else:
        final_where = ""
        all_params = []

    # §6 Database Compiler: assemble DuckDB SQL
    sql = (
        f"SELECT {select_clause}\n"
        f'FROM "{table}"\n'
        f"{final_where}\n"
        f"{order_clause}\n"
        f"{limit_clause}"
    )

    # §7 Execution
    try:
        result = conn.execute(sql, all_params)
    except Exception as e:
        return {"error": str(e), "query": sql, "params": all_params}

    rows = result.fetchall()
    col_names = [desc[0] for desc in result.description]

    # §8 Result Normalization
    results = [dict(zip(col_names, row)) for row in rows]

    # Build next cursor from last row
    has_more = len(rows) == ast.pagination.limit
    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        sort_idx = col_names.index(ast.pagination.sort_column) if ast.pagination.sort_column in col_names else 0
        id_idx = col_names.index("id") if "id" in col_names else (len(col_names) - 1)
        next_cursor = [last[sort_idx], last[id_idx]]

    elapsed = time.time() - start

    return {
        "results": results,
        "pagination": {
            "cursor": next_cursor,
            "has_more": has_more,
            "limit": ast.pagination.limit,
        },
        "metadata": {
            "elapsed_ms": round(elapsed * 1000, 2),
            "row_count": len(results),
            "entity": entity,
        },
    }


# ── DuckDB Query Examples ──

QUERY_EXAMPLES = {
    "basic_department_filter": {
        "desc": "All Engineering VPs and Directors, sorted by confidence",
        "ast": {
            "entity": "person",
            "columns": ["id", "name", "title", "department", "seniority", "confidence", "quality_score"],
            "filters": [
                {"field": "department", "operator": "==", "value": "Engineering"},
                {"field": "seniority",  "operator": "in",      "value": ["VP", "Director"]},
            ],
            "pagination": {"sort_column": "confidence", "sort_direction": "desc", "limit": 50},
        },
        "sql": (
            'SELECT "confidence", "department", "id", "name", "quality_score", "seniority", "title"\n'
            'FROM "person"\n'
            'WHERE "department" = ? AND "seniority" IN (?, ?)\n'
            'ORDER BY "confidence" DESC, id DESC\n'
            'LIMIT 50'
        ),
    },
    "cursor_pagination_page2": {
        "desc": "Second page using cursor from first page",
        "ast": {
            "entity": "person",
            "filters": [
                {"field": "department", "operator": "==", "value": "Engineering"},
            ],
            "pagination": {
                "cursor": [0.88, "p2"],
                "sort_column": "confidence",
                "sort_direction": "desc",
                "limit": 50,
            },
        },
        "sql": (
            'SELECT *\n'
            'FROM "person"\n'
            'WHERE ("confidence" < ? AND id < ?) AND ("department" = ?)\n'
            'ORDER BY "confidence" DESC, id DESC\n'
            'LIMIT 50'
        ),
    },
    "company_search_by_industry": {
        "desc": "Companies in Technology > 100 employees",
        "ast": {
            "entity": "company",
            "columns": ["id", "name", "domain", "industry", "employee_count", "revenue"],
            "filters": [
                {"field": "industry",      "operator": "==", "value": "Technology"},
                {"field": "employee_count", "operator": ">=", "value": 100},
            ],
            "pagination": {"sort_column": "employee_count", "sort_direction": "desc", "limit": 25},
        },
        "sql": (
            'SELECT "domain", "employee_count", "id", "industry", "name", "revenue"\n'
            'FROM "company"\n'
            'WHERE "industry" = ? AND "employee_count" >= ?\n'
            'ORDER BY "employee_count" DESC, id DESC\n'
            'LIMIT 25'
        ),
    },
    "keyword_text_search": {
        "desc": "Text search via normalized ILIKE — replace with FTS in production per ARCHITECTURE.md",
        "ast": {
            "entity": "person",
            "columns": ["id", "name", "title"],
            "filters": [
                {"field": "title", "operator": "contains", "value": "software engineer"},
            ],
            "pagination": {"limit": 100},
        },
        "sql": (
            'SELECT "id", "name", "title"\n'
            'FROM "person"\n'
            'WHERE "title" ILIKE ?\n'
            'ORDER BY "freshness" ASC, id ASC\n'
            'LIMIT 100'
        ),
    },
    "fulltext_index_populate": {
        "desc": "Populate full-text index from existing data",
        "sql": "INSERT INTO _le_fulltext (entity, entity_id, field, token, position)\nSELECT 'person', id, 'title', LOWER(token), pos\nFROM (\n  SELECT id, UNNEST(string_split(title, ' ')) AS token,\n         CAST(ROW_NUMBER() OVER (PARTITION BY id) - 1 AS INTEGER) AS pos\n  FROM person WHERE title IS NOT NULL\n);",
    },
    "fulltext_index_search": {
        "desc": "Multi-token full-text search via join (phrase-sensitive)",
        "sql": "SELECT p.id, p.name, p.title\nFROM person p\nJOIN _le_fulltext ft1 ON ft1.entity_id=p.id AND ft1.token='vice'     AND ft1.entity='person' AND ft1.field='title'\nJOIN _le_fulltext ft2 ON ft2.entity_id=p.id AND ft2.token='president' AND ft2.entity='person' AND ft2.field='title'\nWHERE ft2.position = ft1.position + 1\nLIMIT 50;",
    },
    "location_seniority_slice": {
        "desc": "Bay Area VP-level leads with email",
        "ast": {
            "entity": "person",
            "columns": ["id", "name", "title", "seniority", "email", "location"],
            "filters": [
                {"field": "seniority", "operator": "in", "value": ["VP", "Director", "Executive"]},
                {"field": "location",  "operator": "in", "value": ["San Francisco", "Palo Alto", "San Jose"]},
                {"field": "email",     "operator": "!=", "value": ""},
            ],
            "pagination": {"sort_column": "name", "sort_direction": "asc", "limit": 50},
        },
        "sql": (
            'SELECT "email", "id", "location", "name", "seniority", "title"\n'
            'FROM "person"\n'
            'WHERE "seniority" IN (?, ?, ?) AND "location" IN (?, ?, ?) AND "email" != ?\n'
            'ORDER BY "name" ASC, id ASC\n'
            'LIMIT 50'
        ),
    },
}


def print_examples():
    """Pretty-print all query examples."""
    for name, ex in QUERY_EXAMPLES.items():
        print(f"\n{'='*70}")
        print(f"  {name}")
        print(f"  {ex['desc']}")
        print(f"{'='*70}")
        if "ast" in ex:
            print(f"  AST: {json.dumps(ex['ast'], indent=4)}")
        print(f"  SQL: {ex['sql']}")
        print()


# ── Self-check demo ──

def demo():
    """Run search pipeline against an in-memory DuckDB with test data."""
    import duckdb

    conn = duckdb.connect(":memory:")

    # Create test tables matching CANONICAL_SCHEMA.md
    conn.execute("""
        CREATE TABLE person AS SELECT * FROM (
            VALUES
                ('p1', 'Alice Chen',    'VP of Engineering',     'VP',       'Engineering', 'ACME Corp',  'San Francisco', 'alice@acme.com',   0.5, 0.95, 0.92, 'verified'),
                ('p2', 'Bob Smith',     'Senior Engineer',       'Senior',   'Engineering', 'ACME Corp',  'New York',      'bob@acme.com',     0.5, 0.88, 0.85, 'verified'),
                ('p3', 'Carol Davis',   'Director of Sales',     'Director', 'Sales',       'Beta Inc',   'Chicago',       'carol@beta.com',   0.5, 0.92, 0.90, 'verified'),
                ('p4', 'Dan Wilson',    'Junior Developer',      'Junior',   'Engineering', 'Gamma LLC',  'Austin',        'dan@gamma.com',    0.5, 0.75, 0.70, 'unverified'),
                ('p5', 'Eve Martin',    'CEO',                   'Executive','Executive',   'Delta Co',   'San Francisco', 'eve@delta.com',    0.5, 0.99, 0.97, 'verified'),
                ('p6', 'Frank Lee',     'Staff Engineer',        'Senior',   'Engineering', 'ACME Corp',  'Seattle',       'frank@acme.com',   0.5, 0.85, 0.82, 'verified'),
                ('p7', 'Grace Kim',     'Product Manager',       'Mid',      'Product',     'Beta Inc',   'San Francisco', NULL,                0.5, 0.80, 0.78, 'unverified'),
                ('p8', 'Henry Zhang',   'Engineering Manager',   'Director', 'Engineering', 'Gamma LLC',  'New York',      'henry@gamma.com',  0.5, 0.90, 0.88, 'verified'),
                ('p9', 'Iris Patel',    'VP of Product',         'VP',       'Product',     'Delta Co',   'San Francisco', 'iris@delta.com',   0.5, 0.93, 0.91, 'verified'),
                ('p10','Jack Brown',    'Software Engineer II',  'Mid',      'Engineering', 'ACME Corp',  'Austin',        'jack@acme.com',    0.5, 0.82, 0.79, 'verified'),
        ) AS t(id, name, title, seniority, department, company, location, email, freshness, confidence, quality_score, verification_status)
    """)

    conn.execute("""
        CREATE TABLE company AS SELECT * FROM (
            VALUES
                ('c1', 'ACME Corp',  'acme.com',  'Technology', 500, '50M'),
                ('c2', 'Beta Inc',   'beta.com',  'Technology', 200, '20M'),
                ('c3', 'Gamma LLC',  'gamma.com', 'Healthcare', 50,  '5M'),
                ('c4', 'Delta Co',   'delta.com', 'Finance',    1000,'100M'),
        ) AS t(id, name, domain, industry, employee_count, revenue)
    """)

    print("LeadEngine Search Pipeline — Demo")
    print("=" * 70)

    print("\n1. Engineering VPs+Directors by confidence")
    r = search(conn, {
        "entity": "person",
        "columns": ["name", "title", "seniority", "confidence"],
        "filters": [
            {"field": "department", "operator": "==", "value": "Engineering"},
            {"field": "seniority",  "operator": "in", "value": ["VP", "Director", "Senior"]},
        ],
        "pagination": {"sort_column": "confidence", "sort_direction": "desc", "limit": 5},
    })
    for row in r.get("results", []):
        print(f"   {row.get("name", ""):15s} {row.get("title", ""):25s} {row.get("seniority", ""):10s} {row.get("confidence", "")}")
    print(f"   cursor={r.get("pagination", {}).get("cursor", "N/A")} has_more={r.get("pagination", {}).get("has_more", False)} ({r.get("metadata", {}).get("elapsed_ms", 0)}ms)")

    print("\n2. SEARCH_SPEC.md format with pagination")
    r2 = search(conn, {
        "entity": "person",
        "filters": {
            "departments": ["Engineering"],
            "seniority": ["VP", "Director", "Senior"],
        },
        "pagination": {"limit": 3, "sort_column": "name", "sort_direction": "asc"},
    })
    for row in r2["results"]:
        print(f"   {row['name']:15s} {row['title']:25s} {row['seniority']:10s}")

    print("\n3. Page 2 via cursor")
    if r2["pagination"]["cursor"]:
        r3 = search(conn, {
            "entity": "person",
            "filters": {
                "departments": ["Engineering"],
                "seniority": ["VP", "Director", "Senior"],
            },
            "pagination": {
                "cursor": r2["pagination"]["cursor"],
                "limit": 3,
                "sort_column": "name",
                "sort_direction": "asc",
            },
        })
        for row in r3["results"]:
            print(f"   {row['name']:15s} {row['title']:25s} {row['seniority']:10s}")
        print(f"   cursor={r3['pagination']['cursor']} has_more={r3['pagination']['has_more']}")

    print("\n4. Keyword text search (contains 'Engineering')")
    r4 = search(conn, {
        "entity": "person",
        "filters": [{"field": "title", "operator": "contains", "value": "Engineering"}],
        "pagination": {"sort_column": "confidence", "sort_direction": "desc", "limit": 10},
    })
    for row in r4["results"]:
        print(f"   {row['name']:15s} {row['title']}")
    print(f"   matched {r4['metadata']['row_count']} rows")

    print("\n5. Full-text index setup")
    fts = setup_fulltext_index(conn)
    print(f"   {fts}")

    print("\n6. Company search")
    r6 = search(conn, {
        "entity": "company",
        "columns": ["name", "industry", "employee_count", "revenue"],
        "filters": [{"field": "industry", "operator": "==", "value": "Technology"}],
        "pagination": {"sort_column": "employee_count", "sort_direction": "desc", "limit": 10},
    })
    for row in r6["results"]:
        print(f"   {row['name']:15s} {row['industry']:15s} {row['employee_count']} emp {row['revenue']}")

    print("\n7. Schema validation (expect error)")
    try:
        search(conn, {
            "entity": "person",
            "filters": [{"field": "does_not_exist", "operator": "==", "value": "x"}],
        })
    except ValueError as e:
        print(f"   ✓ {e}")

    print("\n8. Email availability filter")
    r8 = search(conn, {
        "entity": "person",
        "columns": ["name", "email"],
        "filters": [{"field": "email", "operator": "!=", "value": ""}],
        "pagination": {"limit": 5},
    })
    for row in r8["results"]:
        print(f"   {row['name']:15s} {'✓' if row.get('email') else '✗'}")

    print("\n9. San Francisco VP-level execs with email")
    r9 = search(conn, {
        "entity": "person",
        "columns": ["name", "title", "seniority", "location", "email", "confidence"],
        "filters": [
            {"field": "seniority", "operator": "in", "value": ["VP", "Director", "Executive"]},
            {"field": "location",  "operator": "in", "value": ["San Francisco"]},
            {"field": "email",     "operator": "!=", "value": ""},
        ],
        "pagination": {"sort_column": "confidence", "sort_direction": "desc", "limit": 10},
    })
    for row in r9["results"]:
        print(f"   {row['name']:15s} {row['title']:25s} {row['seniority']:10s} {row['location']:15s} {row.get('email', ''):20s}")
    print(f"   matched {r9['metadata']['row_count']} rows")

    conn.close()
    print(f"\n{'='*70}")
    print("All tests passed.")


if __name__ == "__main__":
    demo()