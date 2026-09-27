# LeadEngine Operating Workflow

## Standard Agent Cycle

```text
1. Read context files
2. Inspect current implementation
3. Define task
4. Check dependencies
5. Plan
6. Delegate useful subtasks
7. Implement
8. Test
9. Review
10. Update documentation
11. Update task state
12. Report evidence
```

## Project State Files
- AGENTS.md = rules
- PROJECT.md = project identity/context
- REQUIREMENTS.md = required behavior
- ARCHITECTURE.md = technical structure
- DESIGN.md = product/UI direction
- ROADMAP.md = phases
- TASKS.md = current work
- DECISIONS.md = architectural decisions
- KNOWN_ISSUES.md = unresolved problems
- CHANGELOG.md = delivered changes

## Subagent Handoff
Every subagent should return:
- task completed
- files changed
- tests run
- findings
- blockers
- follow-up recommendations

Main agent integrates and verifies.

## Never
- overwrite raw datasets
- invent data
- mark unverified data verified
- skip tests
- claim completion without evidence
- let LLM output become raw SQL
- silently ignore known data-quality defects
