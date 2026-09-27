# LeadEngine Architecture Review Guide

## Executive Verdict

Current local architecture:

```text
FastAPI + DuckDB + Parquet + Alpine.js
```

is appropriate for MVP/prototyping.

Production target:

```text
Next.js/React
+
FastAPI
+
ClickHouse
+
PostgreSQL
+
Redis
+
workers
+
object storage
```

Elasticsearch remains optional.

## 1. DuckDB

### Strengths
- Excellent Parquet integration.
- Minimal infrastructure.
- Strong analytical execution.
- Great local development.
- Good preprocessing engine.

### Weaknesses
- Not purpose-built for high-concurrency SaaS serving.
- Repeated wildcard text scans are poor final search architecture.
- Operational scaling is less straightforward than dedicated serving databases.

### Decision
Keep DuckDB for MVP and ETL. Benchmark before migration.

## 2. ClickHouse

Strong production candidate because workload combines:
- huge datasets
- structured filters
- aggregations
- facets
- analytics
- increasingly capable full-text search.

Use it as primary production lead-search engine after benchmark validation.

## 3. Elasticsearch

Excellent when:
- relevance is core,
- fuzzy search is extensive,
- synonyms/analyzers matter,
- search behavior needs deep tuning.

Cost: another infrastructure system.

Recommendation: do not add until requirements justify it.

## 4. Frontend

Alpine.js is fine for MVP.

Move to Next.js/React when product grows to:
- auth
- teams
- billing
- lists
- workflows
- integrations
- complex state
- multiple dashboards.

Do not rewrite early without need.

## 5. Data Architecture

Critical improvement:

```text
raw source
 ↓
profiling
 ↓
normalization
 ↓
entity resolution
 ↓
canonical model
 ↓
search index
```

Keep raw sources immutable.

Canonical entities:
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

## 6. Data Quality

Known blueprint concerns include:
- Apollo Software Development sample showing apparent column shifts.
- Getlanka sample showing fragmented/shifted JSON-like fields.
- Pitchbook presentation-layer field names.
- Pitchbook phone records marked FAKE.
- LinkedIn data with mixed freshness.

Quarantine structurally corrupted data until reliable reconstruction.

## 7. Search

Current broad wildcard search:

```sql
ILIKE '%query%'
```

should not be final architecture for 354M+ rows.

Use:
- structured predicates
- full-text index
- fuzzy layer
- controlled synonyms
- validated query AST

## 8. SQL Security

Do not rely on string removal such as:

```python
value.replace(";", "").replace("--", "").replace("/*", "")
```

Use:
- parameterized values
- identifier allowlists
- strict dataset/column/sort validation.

## 9. Pagination

Replace deep OFFSET pagination with keyset/cursor pagination.

Concept:

```sql
WHERE (sort_value, id) > (?, ?)
ORDER BY sort_value, id
LIMIT 50
```

## 10. Facets

Precompute/materialize common facets and cache them.

Do not scan 354M rows for every filter interaction.

## 11. Counts

Exact `COUNT(*)` should not be mandatory for every search.

Use estimated/precomputed counts where appropriate.

## 12. Exports

Production exports should be asynchronous:

```text
request
 ↓
job
 ↓
worker
 ↓
database
 ↓
object storage
 ↓
signed URL
```

## 13. SaaS Features Missing From Initial Blueprint

Add:
- organizations
- teams
- RBAC
- lists
- tags
- notes
- saved searches
- search history
- suppression lists
- API keys
- webhooks
- usage analytics
- audit logs
- export history
- enrichment
- verification
- CRM integrations
- freshness
- provenance
- confidence scores.

## 14. Monetization

Potential credit categories:
- search
- email reveal
- phone reveal
- export
- API
- enrichment.

Plans can progress from individual/basic usage to team/enterprise functionality.

## 15. Enrichment

Build separate person/company enrichment actions.

Person:
- email
- phone
- company
- title
- social
- verification.

Company:
- domain
- employees
- revenue
- funding
- technology
- social
- hiring/growth signals.

## 16. Verification

Potential:
- email syntax
- MX
- SMTP where legally/technically appropriate
- disposable detection
- catch-all detection
- phone validation
- domain validation.

Never call scraped values verified without verification.

## 17. Security

Add:
- RBAC
- MFA
- secure cookies
- CSRF where applicable
- CSP
- HSTS
- audit logs
- API key rotation
- anomaly detection
- tenant isolation
- export controls
- field-level access.

## 18. Legal/Privacy

Scraped data can create:
- contractual restrictions
- privacy obligations
- database-rights/copyright issues
- data-broker obligations
- source-specific restrictions.

LinkedIn terms prohibit automated scraping/copying through specified methods. Public visibility does not automatically grant resale rights.

GDPR/UK GDPR and California rules can apply to business contact data.

Before commercialization, obtain legal review of:
- source rights
- licensing
- lawful basis
- notices
- deletion
- correction
- opt-out/suppression
- retention.

## 19. Infrastructure

Early benchmark target:

```text
8 vCPU
32 GB RAM
500 GB NVMe
```

Better growth target:

```text
16 vCPU
64 GB RAM
1 TB NVMe
```

Use object storage for raw/archive/backup/ETL inputs.

Do not make every interactive user query depend on remote Parquet scans.

## 20. Benchmark Before Migration

Run:
- exact domain
- country
- country + title
- seniority
- text search
- fuzzy search
- company search
- technology
- multiple filters
- broad query
- facets
- sorting
- profile
- 1K export
- 10K export

Test concurrency:

```text
1
5
10
25
50
100
```

Measure:
- p50
- p95
- p99
- CPU
- RAM
- disk I/O
- rows scanned
- rows returned
- cache hit rate.

Do not promise global sub-second performance without measured evidence.

## 21. Build-From-Scratch Recommendation

Start small:

```text
FastAPI
DuckDB
Parquet
Alpine
```

But build abstraction seams now:

```text
query AST
database adapter
canonical schema
source registry
provenance
quality layer
benchmark suite
```

Then migrate:

```text
DuckDB → ClickHouse
Alpine → Next.js
local Parquet → object storage
sync export → worker queue
```

without rebuilding product logic.
