# LeadEngine Known Issues

## Data
- Some datasets contain malformed or shifted columns.
- Some source fields use presentation/CSS-derived names.
- Some contact values are invalid or explicitly marked invalid.
- LinkedIn data has significant freshness variation.
- Duplicate people/companies likely exist across sources.
- Source records may disagree on the same entity.

## Search
- Wildcard ILIKE is not a final large-scale full-text strategy.
- Exact COUNT(*) may become expensive.
- Dynamic facet counts may become expensive.
- OFFSET pagination does not scale for deep pages.
- Synonym handling must avoid false equivalence.

## Architecture
- Single-file FastAPI architecture should remain MVP-only.
- Production requires stronger separation of API, services, workers, and data layers.
- DuckDB concurrency needs workload benchmarking.

## Security
- String sanitization is not SQL security.
- Production needs parameterized queries and identifier allowlists.
- Tenant isolation is required before SaaS launch.

## Compliance
- Scraped LinkedIn/Apollo/etc. data may have contractual, copyright/database-rights, privacy, and data-broker implications.
- Legal review required before commercial launch.
- Suppression/deletion infrastructure required.
