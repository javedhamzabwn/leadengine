# LeadEngine Query AST

## Pipeline

```
Request → Schema Validation → Authorization → Query Normalization → Query AST → Query Planner → Database Compiler → Execution → Result Normalization
```

## Query Components

### 1. Schema Validation
- Validates all identifiers against allowed values (dataset names, column names, enum values).
- Rejects invalid queries early.

### 2. Authorization
- Checks user permissions (RBAC) before allowing query execution.
- Grants access to only authorized datasets.

### 3. Query Normalization
- Converts natural-language or AST queries into a standardized internal representation.
- Resolves aliases, standardizes field names.

### 4. Query AST
```
{
  "type": "SELECT",
  "columns": ["name", "title", "department", "seniority"],
  "filters": [
    {"field": "department", "operator": "==", "value": "Engineering"},
    {"field": "seniority", "operator": ">=", "value": "Senior"}
  ],
  "pagination": {
    "cursor": null,
    "limit": 50
  }
}
```

### 5. Query Planner
- Translates AST into database-specific SQL.
- Chooses join order, index usage, and optimization strategy.

### 6. Database Compiler
- Generates executable SQL for DuckDB (MVP) or ClickHouse (production).
- Handles dialect differences (e.g., ClickHouse's `GROUP BY` vs DuckDB's `GROUP BY`).

### 7. Execution
- Runs compiled query against the target database.
- Captures execution plan, timing, and resource usage.

### 8. Result Normalization
- Maps raw result rows to canonical entity objects.
- Attaches provenance metadata (source, quality score, confidence).
- Returns paginated results with `next_cursor` for infinite scroll.

## Constraints
- No wildcard `ILIKE` scans for production search (>100K rows).
- All filters must use parameterized values (no string concatenation).
- Maximum row limit per query: 1000 (configurable).
- Pagination uses cursor-based keyset (stable ordering).
