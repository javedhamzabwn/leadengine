# LeadEngine Search Specification

## Query Model

```json
{
  "entity": "person",
  "text": {
    "query": "software engineer"
  },
  "filters": {
    "countries": ["US"],
    "seniority": ["VP", "Director"],
    "departments": ["Engineering"],
    "company_size": {
      "min": 51,
      "max": 200
    },
    "has_email": true
  },
  "exclude": {
    "titles": ["intern"]
  },
  "pagination": {
    "cursor": null,
    "limit": 50
  }
}
```

## Query Pipeline

```text
request
 ↓
schema validation
 ↓
authorization
 ↓
query normalization
 ↓
query AST
 ↓
query planner
 ↓
database-specific compiler
 ↓
execution
 ↓
result normalization
```

## Text Search
Use:
- exact matching for identifiers
- normalized lexical matching for titles/company names
- full-text index for broad text
- fuzzy matching for typo tolerance
- synonyms for controlled vocabulary

Do not use broad `%query%` wildcard scans as the final strategy for 354M+ records.

## Title Taxonomy

Store:
- original_title
- normalized_title
- department
- function
- seniority

Example:

```text
VP of Engineering
→ normalized_title: vice president engineering
→ department: engineering
→ seniority: vp
```

Do not automatically treat Director, Head, and VP as identical.

## Pagination
Use stable ordering with a unique tie-breaker.

Example concept:

```sql
WHERE (sort_value, id) > (?, ?)
ORDER BY sort_value, id
LIMIT 50
```

## Counts
Use exact count only when cost is acceptable. Otherwise return estimated/precomputed count.

## Facets
Cache and/or precompute common facets.
