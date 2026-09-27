# LeadEngine Architecture Decision Records

## ADR-001 — MVP Query Engine
Status: Accepted

Use DuckDB + Parquet for local MVP.

Reason:
- minimal infrastructure
- direct Parquet querying
- strong analytical performance
- easy Python integration

Revisit when:
- concurrency grows
- latency becomes inconsistent
- workload requires production-scale serving

Candidate production engine: ClickHouse.

## ADR-002 — Raw Data Immutability
Status: Accepted

Never mutate raw source files.

All cleaning happens in derived layers.

## ADR-003 — Canonical Data Model
Status: Accepted

Create canonical Person/Company/etc. entities while retaining source provenance.

## ADR-004 — SQL Security
Status: Accepted

Use parameterized values and allowlists. Do not depend on string sanitization.

## ADR-005 — Pagination
Status: Accepted

Use cursor/keyset pagination for large result sets.

## ADR-006 — Production Search
Status: Proposed

Evaluate ClickHouse first. Evaluate Elasticsearch only if relevance/fuzzy search requirements justify separate search infrastructure.

## ADR-007 — Frontend
Status: Proposed

Keep Alpine.js for MVP. Move to Next.js/React when product surface and client state justify it.

## ADR-008 — Object Storage
Status: Proposed

Use S3/R2-style object storage for raw/archive/backup/ETL inputs, not as the primary interactive query layer.
