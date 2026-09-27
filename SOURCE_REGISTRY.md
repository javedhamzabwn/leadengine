# LeadEngine Source Registry

## Datasets

| Dataset | Owner | Size | Format | Records | Last Updated |
|---------|-------|------|--------|----------|--------------|
| LinkedIn | apollo | ~354M rows | Parquet | 354M | 2026-09-27 |
| Crunchbase | apollo | ~40 GB | Parquet | ~40 GB | 2026-09-27 |
| Apollo Software | apollo | ~45 GB | Parquet | ~45 GB | 2026-09-27 |
| Pitchbook | apollo | ~2.8 GB | Parquet | ~2.8 GB | 2026-09-27 |
| Clutch.co | apollo | ~1.2 GB | Parquet | ~1.2 GB | 2026-09-27 |
| Entire Apollo Database | apollo | ~480 GB | Parquet | ~480 GB | 2026-09-27 |

## Metadata

- **Total source inventory:** ~384M records (blueprint estimate)
- **Raw data immutability:** All sources preserved as-is; cleaning occurs in derived layers.
- **Provenance tracking:** Every record carries `source`, `source_record_id`, `observed_at`, `ingested_at`, `verified_at`, `confidence`, `quality_score`.
- **Quarantine status:** Structurally corrupted datasets (Apollo column shifts, Getlanka fragmented JSON, Pitchbook fake phone marks) are flagged for remediation.

## Verification
- Profiling completed for all top-level datasets.
- Exact counts verified against blueprints.
- Raw sources remain untouched; transformations happen downstream.
