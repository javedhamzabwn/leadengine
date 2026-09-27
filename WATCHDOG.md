# LeadEngine Watchdog

Autonomous monitor for the LeadEngine 5-hour development session (and beyond).
Runs every 10 minutes via cron. Its job: detect problems early and keep work moving.

## What it checks (every run)

| # | Check | Source | Fail condition |
|---|-------|--------|----------------|
| 1 | Unfinished P0/P1 tasks | `TASKS.md` | any P0 not DONE/VERIFIED |
| 2 | Stalled work | git log + file mtimes vs state file | IN_PROGRESS task, no repo change in 30+ min |
| 3 | Tasks marked DONE without verification | `TASKS.md` | DONE with no test/verify evidence |
| 4 | Backend health | `data/leadengine.db`, imports | DB missing, `company` table empty, import errors |
| 5 | API liveness | `http://127.0.0.1:8000/health` (if server expected) | connection refused when flag file says running |
| 6 | Background jobs | `ps` | normalize/build/test process died unexpectedly |
| 7 | Recent tracebacks | `data/*.log`, `backend.log` | new `Traceback` lines since last run |
| 8 | Disk space | `df` | < 2 GB free on workspace volume |
| 9 | Dependency drift | `backend/requirements.txt` vs `.venv` | import of a required package fails |
| 10 | TODO/FIXME hotspots | `rg "TODO\|FIXME\|XXX\|HACK" backend/` | count changed since last run |

## State

`data/watchdog_state.json` — last run timestamp, last git HEAD, per-check results,
consecutive-failure counters. Never hand-edit; the script owns it.

## Alerting policy

- The cron handoff surfaces a message **only** when: a check newly fails,
  a stall is detected, or a P0 task is unfinished at a session milestone.
- Routine all-green runs stay silent (state file is the record).
- 3 consecutive failures on the same check → escalate: the handoff must say
  `ESCALATE:` and propose the fix, not just report.

## Continuation rule

If the session's todo list has pending items and no blocker is recorded,
the handoff ends with `CONTINUE:` naming the single next highest-value task
from `TASKS.md`. The agent picks that task up immediately.

## Manual run

```bash
~/workspace/leadengine/.venv/bin/python ~/workspace/leadengine/scripts/watchdog.py
~/workspace/leadengine/.venv/bin/python ~/workspace/leadengine/scripts/watchdog.py --verbose
```
