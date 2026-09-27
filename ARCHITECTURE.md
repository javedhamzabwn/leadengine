# LeadEngine Architecture

## Current MVP

```text
Browser
  ↓
FastAPI
  ↓
DuckDB
  ↓
Parquet
```

Use this for local development and early validation.

## Production Target

```text
Cloudflare / CDN
      ↓
Next.js frontend
      ↓
FastAPI API
      ↓
┌──────────────┬──────────────┬──────────────┐
PostgreSQL     Redis          ClickHouse
users/billing  cache/limits   lead search
      │              │              │
      └──────────────┴───────┬──────┘
                             ↓
                           Workers
                             ↓
                       Object Storage
                             ↓
                           Parquet
```

Elasticsearch remains optional for cases where search relevance/fuzzy/linguistic search becomes a major requirement.

## Data Flow

```text
RAW PARQUET
    ↓
profiling
    ↓
quality checks
    ↓
schema mapping
    ↓
normalization
    ↓
deduplication
    ↓
entity resolution
    ↓
canonical data model
    ↓
search indexes / ClickHouse
```

## Canonical Entities
- Person
- Company
- Employment
- Email
- Phone
- Domain
- Technology
- Location
- SocialProfile
- FundingEvent
- SourceRecord
- Verification
- Suppression

## Provenance
Important values should preserve:
- source
- source_record_id
- observed_at
- ingested_at
- verified_at
- confidence
- quality_score

## Search
Avoid broad wildcard `ILIKE` as final search architecture.

Preferred layers:
1. Exact structured filtering.
2. Full-text/inverted index.
3. Fuzzy matching.
4. Synonym/title normalization.
5. Validated query AST.
6. Database-specific query compiler.

## Pagination
Prefer keyset/cursor pagination.

## Facets
Use precomputed/materialized facet data plus caching rather than expensive full scans on every UI interaction.

## Caching
- L1 process cache for small metadata.
- Redis for query/facet/autocomplete cache and quotas.
- Database/index for authoritative results.

## Exports
Production export flow:

```text
POST /exports
  ↓
queue
  ↓
worker
  ↓
ClickHouse
  ↓
object storage
  ↓
signed download
```

## Server Starting Point
Early production benchmark target:
- 8 vCPU
- 32 GB RAM
- 500 GB NVMe
- 1 Gbps preferred

Larger workload target:
- 16 vCPU
- 64 GB RAM
- 1 TB NVMe

Actual sizing must come from workload benchmarks.

## API Structure

```text
GET  /api/v1/people/{person_id}
GET  /api/v1/companies/{company_id}
POST /api/v1/search/people
POST /api/v1/search/companies
POST /api/v1/enrichment/person
POST /api/v1/enrichment/company
POST /api/v1/exports
GET  /api/v1/exports/{id}
```

## Security
- Parameterized SQL values.
- Allowlisted SQL identifiers.
- Authentication.
- RBAC.
- Rate limits.
- API key rotation.
- Audit logs.
- Secure cookies.
- CSRF protection where applicable.
- CSP/HSTS.
- Export anomaly detection.
- Tenant isolation.
