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

## ADR-009 — TASKS.md honesty reset (2026-09-27)
Status: Accepted

The pre-existing TASKS.md marked LEAD-001..005 VERIFIED with no evidence while its own
checkboxes were unchecked. Rewrote the tracker with a ledger rule: DONE = implemented,
VERIFIED = named evidence. Legacy entries corrected to honest states rather than deleted.

## ADR-010 — Standard JWT via stdlib (2026-09-27)
Status: Accepted

Replaced the nonstandard hex token format and eval()-based payload parsing with a
standard base64url(header).base64url(payload).HMAC-SHA256 JWT implemented in stdlib
(json/base64/hmac/hashlib). No new dependency; format is interoperable and inspectable.

## ADR-011 — Bad-id rows quarantined, not repaired (2026-09-27)
Status: Accepted

81 company rows whose ids failed UUID validation (reconstruction fragments: sentences
and comma-joined field shards) were moved to quarantine_raw with reason
bad_id_reconstruction_fragment. None had name+domain+email; all were unrecoverable as
companies. Raw data preserved in quarantine; company count is now 7438.

## ADR-012 — No-login collections for MVP (2026-09-27)
Status: Accepted

Saved searches and favorites require no authentication in the MVP (single-tenant local
product). Revisit with tenant isolation before SaaS launch.

## ADR-013 — Next.js replaces Alpine.js for MVP (2026-09-27)
Status: Accepted

ADR-007 proposed Alpine.js for MVP; the product surface (search, filters, drawer,
selection, exports) justified Next.js/React now. Implemented with App Router.

## ADR-014 — Public-tunnel browser E2E as the verification route (2026-09-27)
Status: Accepted

Every in-sandbox route to a real browser click-through was a proven dead end
(Chromium 152 Local Network Access checks on loopback, cloudflared quick tunnels,
LAN-IP veth route, runs #10-#13). The true click-through was instead performed in
the user's own browser against a public localtunnel URL, and LEAD-014 was marked
VERIFIED on that evidence (dashboard 7,438 companies, search q=software with
debounce, facets, cursor pagination, detail drawer with unverified-data label,
CSV export 200, signup 201 + JWT login). In-sandbox UI coverage remains the
wire-level flow simulation (18/18) exercising the exact URLs the frontend builds.

## ADR-015 — Conditional tunnel-bypass header (2026-09-27)
Status: Accepted

`frontend/lib/api.ts` sends `bypass-tunnel-reminder: 1` only when `API_BASE`
contains `.loca.lt` (localtunnel's browser-reminder interstitial). The header is
ignored by non-tunnel servers and is absent on every other host, so production
behavior is unchanged. `tsc --noEmit` clean.
