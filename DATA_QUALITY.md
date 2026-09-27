# LeadEngine Data Quality Plan

## Required Pipeline

```text
Raw source
  ↓
schema/profile inspection
  ↓
type validation
  ↓
schema mapping
  ↓
normalization
  ↓
quality checks
  ↓
deduplication
  ↓
entity resolution
  ↓
canonical records
  ↓
search index
```

## Required Normalization

### Email
- lowercase
- trim whitespace
- validate syntax
- classify role-based/disposable/catch-all where supported
- preserve original value
- record verification status

### Phone
- normalize to E.164 where country is known
- preserve original
- classify mobile/direct/office where possible
- validate country/type

### Domain
- lowercase
- remove protocol
- remove path
- normalize www
- derive root domain

### Title
- normalize case/punctuation
- expand known abbreviations
- map to department/function
- map to seniority
- preserve original title

### Location
- normalize country/state/city
- retain original text
- map aliases

## Quality Fields

```text
quality_score
confidence_score
source
source_record_id
observed_at
ingested_at
verified_at
```

## Quarantine Rules
Quarantine records/datasets when:
- columns are structurally shifted,
- required fields cannot be reliably mapped,
- JSON is fragmented across columns,
- row structure is inconsistent,
- values are demonstrably corrupted.

## Specific Blueprint Findings
- Apollo Software Development sample shows apparent column shifting.
- Getlanka sample shows fragmented/shifted JSON-like company data.
- Pitchbook exports contain presentation-layer column names.
- Some Pitchbook phone records are marked FAKE.
- LinkedIn records have mixed historical freshness.

These require profiling before production exposure.
