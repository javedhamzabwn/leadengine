# LeadEngine Design

## Product Shell

```text
Search
Lists
Companies
Contacts
Saved Searches
Enrichment
Integrations
API
Usage
Billing
Settings
```

## Search Screen

```text
SEARCH
────────────────────────────────

Search people / companies

[ Search / natural-language query ]

Filters
  Location
  Title
  Seniority
  Department
  Industry
  Company
  Employees
  Revenue
  Funding
  Technology
  Contact availability
  Freshness

────────────────────────────────

[results count]

[Select] [Save Search] [Add to List] [Export]

Results table
```

## Profile
Profile should show:
- canonical person/company identity
- contact information
- employment
- social links
- source/provenance
- freshness
- verification status
- confidence
- related company
- available enrichment actions

## Design Principles
- Fast search-first workflow.
- Clear filter state.
- Explain why a field is present/verified.
- Never imply uncertain data is verified.
- Keep bulk actions visible.
- Make export/credit cost visible before expensive actions.
- Preserve accessibility and keyboard navigation.

## Future AI Search

```text
Natural language
      ↓
validated query AST
      ↓
editable filters
      ↓
search engine
```

LLM must never directly generate executable SQL.
