# LeadEngine Agent Instructions

## Mission
Build LeadEngine as a reliable B2B lead-search SaaS over large pre-scraped datasets.

## Before Any Work
1. Read `PROJECT.md`.
2. Read `REQUIREMENTS.md`.
3. Read `ARCHITECTURE.md`.
4. Read `ROADMAP.md`.
5. Read `TASKS.md`.
6. Read relevant files under `SPECS/`.
7. Read `DECISIONS.md` and `KNOWN_ISSUES.md` when relevant.
8. Inspect existing code before changing it.

## Working Rules
- Preserve raw source data. Never mutate raw datasets in place.
- Treat raw source schemas as source-specific. Normalize into canonical semantic schemas.
- Never expose a field as verified unless verification actually happened.
- Preserve source provenance for important fields.
- Use parameterized SQL values. Never rely on string sanitization for SQL security.
- Allowlist SQL identifiers such as sort columns and dataset names.
- Prefer cursor/keyset pagination over large OFFSET pagination.
- Avoid expensive exact COUNT(*) when approximate/precomputed counts are sufficient.
- Keep exports asynchronous once workload becomes non-trivial.
- Never claim a task is complete without testing it.
- Update `TASKS.md` after meaningful task progress.
- Record important architectural choices in `DECISIONS.md`.
- Record known defects and limitations in `KNOWN_ISSUES.md`.
- Keep documentation synchronized with implementation.
- Prefer small, reversible changes.
- Do not introduce infrastructure merely for fashion. Benchmark first.

## Agent Workflow
Understand → Plan → Implement → Test → Review → Document → Verify.

## Subagents
Use specialized subagents when useful:
- data profiling
- schema normalization
- architecture review
- implementation
- testing
- security review
- documentation

Main agent owns final integration, task state, testing, and documentation.

## Definition of Done
A task is done only when:
- implementation exists,
- relevant tests pass,
- security/data implications are checked,
- documentation/state files are updated,
- no known regression is left unexplained.
