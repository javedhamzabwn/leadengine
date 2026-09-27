# LeadEngine Known Issues

## Data (updated 2026-09-27)
- The single available source (data_6.parquet) was mis-split on quoted commas;
  reconstruction is best-effort. 81 bad-id fragments quarantined on 2026-09-27
  (quarantine_raw now 97 rows); 7438 canonical companies remain.
- `verification_status` is `unverified` for all rows: no value is presented as verified.
- Duplicate companies may exist across the source; no dedup pass has run yet.
- Source records may disagree on the same entity; provenance is preserved per row.

## Search
- Keyword search is ILIKE over `search_text`; not a final large-scale full-text strategy.
- No exact total counts on list endpoints (by design); facets carry the counts.
- Synonym handling must avoid false equivalence (not implemented).

## Architecture
- Single-process FastAPI + DuckDB is MVP-only. Multi-worker deploys need a persistent
  user store (auth users are currently in-memory) and workload benchmarking.
- DuckDB write transactions are very slow on this VM's btrfs writeback; reads are fast.
  Keep writes small and transactional.

## Security
- JWT secret falls back to a dev default when `LEADENGINE_JWT_SECRET` is unset;
  production must set it.
- Saved searches/favorites require no login (deliberate single-tenant MVP choice).
- Tenant isolation is required before any SaaS launch.

## Compliance
- Source/licensing review not done; suppression/deletion/retention workflows not built.
- Legal review required before commercial launch.
- LEAD-004 tracks this; out of scope for the build session.
