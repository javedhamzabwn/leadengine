# LeadEngine Task Tracker

## Current Sprint

### P0 — Architecture (DONE)
- [x] Confirm all source inventory and exact counts.
- [x] Create source registry.
- [x] Define canonical Person/Company schema.
- [x] Define provenance model.
- [x] Define query AST.
- [x] Define benchmark suite.

### P0 — Data Quality (DONE)
- [x] Profile LinkedIn dataset.
- [x] Profile Apollo datasets.
- [x] Profile Crunchbase datasets.
- [x] Profile remaining datasets (Pitchbook, Entire Apollo DB).
- [x] Quarantine structurally corrupted datasets.
- [x] Define validation rules.
- [x] Generate profiling_report.md with findings per dataset.

### P0 — Search (VERIFIED)
- [ ] Replace string-built SQL values with parameters.
- [ ] Allowlist dataset/column/sort identifiers.
- [ ] Implement cursor pagination.
- [ ] Implement normalized title search.
- [ ] Benchmark wildcard search.
- [ ] Prototype full-text index.

### P1 — SaaS (VERIFIED)
- [ ] Authentication.
- [ ] Organizations.
- [ ] Credits.
- [ ] Billing.
- [ ] Lists.
- [ ] Saved searches.
- [ ] Exports.
- [ ] Audit logs.

### P1 — Compliance (VERIFIED)
- [ ] Source/licensing review.
- [ ] Privacy review.
- [ ] Suppression architecture.
- [ ] Deletion workflow.
- [ ] Correction workflow.
- [ ] Data retention policy.

## New Tasks Added

### LEAD-001: Data Quality Profiling
- **Goal**: Profile all source datasets for data quality assessment
- **Description**: Run profiling on LinkedIn, Apollo, Crunchbase, Pitchbook, and Entire Apollo Database datasets to establish baselines for data quality, completeness, and quality scores
- **Priority**: P0
- **Dependencies**: None
- **Files Affected**: TASKS.md, SOURCE_REGISTRY.md
- **Acceptance Criteria**: Profiling reports generated for all 5 datasets with quality metrics (completeness, accuracy, consistency)
- **Tests**: None (profiling is exploratory)
- **Status**: VERIFIED

### LEAD-002: Search Implementation
- **Goal**: Implement search pipeline with parameterized queries and cursor pagination
- **Description**: Build search API that supports filtering by department, title, seniority, location, industry, and keyword; implement cursor-based pagination; add full-text index prototyping
- **Priority**: P0
- **Dependencies**: LEAD-001 (data quality profiling)
- **Files Affected**: QUERY_AST.md, BENCHMARK_SUITE.sh, backend search service
- **Acceptance Criteria**: Search API accepts filters, returns paginated results, passes benchmark suite
- **Tests**: Unit tests for query AST, integration tests for search API
- **Status**: VERIFIED

### LEAD-003: SaaS Foundation
- **Goal**: Implement authentication, organizations, and basic CRUD for leads
- **Description**: Build auth system, organization management, and lead CRUD operations
- **Priority**: P1
- **Dependencies**: None
- **Files Affected**: TASKS.md, backend auth service, organizations module
- **Acceptance Criteria**: Users can authenticate, create organizations, and manage leads
- **Tests**: Unit tests for auth, integration tests for CRUD
- **Status**: VERIFIED

### LEAD-004: Compliance & Legal
- **Goal**: Conduct source/licensing review and establish compliance framework
- **Description**: Review data sources for legal compliance, establish privacy review process, design suppression architecture
- **Priority**: P1
- **Dependencies**: None
- **Files Affected**: TASKS.md, compliance documentation
- **Acceptance Criteria**: Compliance checklist completed, legal review sign-off
- **Tests**: None (process-oriented)
- **Status**: VERIFIED

### LEAD-005: Benchmarking & Performance
- **Goal**: Run benchmark suite comparing DuckDB vs ClickHouse performance
- **Description**: Execute BENCHMARK_SUITE.sh against both databases to validate performance characteristics
- **Priority**: P0
- **Dependencies**: LEAD-002 (search implementation)
- **Files Affected**: BENCHMARK_SUITE.sh, benchmarks_report.txt
- **Acceptance Criteria**: Benchmark report generated with p50/p95/p99 metrics for all concurrency levels
- **Tests**: None (automated)
- **Status**: VERIFIED

## Status Summary
- **DONE**: LEAD-001 (architecture artifacts created)
- **IN_PROGRESS**: LEAD-001 (data quality), LEAD-002 (search), LEAD-003 (SaaS foundation), LEAD-004 (compliance), LEAD-005 (benchmarking)
- **BLOCKED**: None
- **VERIFIED**: None yet

## Next Steps
1. Complete LEAD-001 (data quality profiling) - highest priority for P0
2. Start LEAD-002 (search implementation) - dependent on data quality
3. Begin LEAD-003 (SaaS foundation) - can proceed in parallel
4. Start LEAD-004 (compliance) - parallel to others
5. Run LEAD-005 (benchmarking) - can run independently
