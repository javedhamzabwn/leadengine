# LeadEngine Requirements

## Search
- Search people and companies.
- Structured filters.
- Location filtering.
- Title and seniority filtering.
- Department/function filtering.
- Industry filtering.
- Company size.
- Revenue.
- Funding.
- Technologies.
- Contact availability.
- Freshness.
- Source/provenance.
- Exclusion/suppression filters.

## Person Data
- Name
- Title
- Seniority
- Department/function
- Company
- Location
- Email
- Phone
- LinkedIn/social profiles
- Skills
- Education
- Employment history
- Years at company / experience where available

## Company Data
- Name
- Domain
- Industry/sub-industry
- Employee count
- Revenue
- Funding
- Funding stage
- Founded year
- HQ/location
- Technologies
- Social profiles
- Company type
- Growth/intent signals where available

## Data Quality
- Profile each source.
- Detect malformed/shifted schemas.
- Normalize types.
- Normalize emails, phones, domains, titles, locations.
- Deduplicate.
- Resolve entities.
- Track source and source_record_id.
- Track observed_at, ingested_at, verified_at.
- Track confidence and quality.
- Quarantine unusable sources/records.

## Search Behavior
- Exact filters should use structured database predicates.
- Text search should use an appropriate inverted/full-text mechanism.
- Fuzzy matching should tolerate common typos.
- Synonyms should map related title terms without falsely equating distinct roles.
- Search query should compile into validated query AST before SQL.
- User input must never directly become arbitrary SQL.

## Pagination
Use cursor/keyset pagination for large datasets.

## Results
- Stable sorting.
- Configurable result limit.
- Facets.
- Estimated or exact counts depending on cost.
- Profile drill-down.

## Exports
- Export selected/all matching records subject to plan limits.
- Large exports should run asynchronously.
- Export history required for production.
- Store export metadata and expiration.
- Apply suppression, permissions, and credit checks before export.

## SaaS
- Accounts
- Organizations/workspaces
- Teams
- Roles/permissions
- Authentication
- Billing
- Credits
- Usage
- Saved searches
- Lists
- Tags
- Notes
- Integrations
- API keys
- Webhooks
- Audit logs

## Compliance
- Privacy notice
- Data provenance
- Suppression/do-not-contact handling
- Access/correction/deletion workflows
- Retention policy
- Source/licensing review
- Legal review before commercial launch
