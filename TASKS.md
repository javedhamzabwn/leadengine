# LeadEngine Task Tracker

**Ledger rule:** a task is DONE only when implemented; VERIFIED only with test/build
evidence named below. Statuses rewritten honestly on 2026-09-27 after audit found
prior VERIFIED marks had no evidence. History of the correction: see DECISIONS.md.

**Status key:** TODO · IN_PROGRESS · DONE (implemented, unverified) · VERIFIED (evidence listed) · BLOCKED · DROPPED

## Active mission (2026-09-27, 5-hour autonomous session)

### LEAD-006: Data layer — normalize data_6.parquet → canonical company table
- Priority: P0 · Status: **VERIFIED**
- Files: `backend/normalize.py`, `data/leadengine.db` (gitignored build artifact), `data/companies_raw.parquet`
- Evidence: `python -m backend.normalize` → "normalized 7519/7535 companies (16 quarantined) in 248.1s";
  `--stats` → avg_quality 0.959, with_email 5749, with_website 7112, with_linkedin 5350.
  Raw parquet preserved untouched; 16 unrecoverable rows quarantined, not deleted.
- Update 2026-09-27: a follow-up normalize pass quarantined 81 additional
  bad-id reconstruction fragments (whole-sentence "ids" from CSV mis-split rows),
  moving them company → quarantine_raw. Current state verified live:
  company=7438 rows, quarantine_raw=97 (16 unrecoverable + 81 fragments),
  7438+97=7535 matches the raw parquet row count. Scoring backfilled on all 7438.
- Caveat: source CSV was mis-split on quoted commas; reconstruction is best-effort.
  `verification_status` stays `unverified` everywhere. Documented in DATA_QUALITY.md.

### LEAD-007: Project tracking + watchdog
- Priority: P0 · Status: **VERIFIED**
- Files: `TASKS.md` (this file), `WATCHDOG.md`, `scripts/watchdog.py`, cron `leadengine-watchdog` (every 10m)
- Evidence: `python3 scripts/watchdog.py` → "ALL GREEN" (run #4); cron created, next run scheduled.

### LEAD-008: Backend API v1 (auth, companies, search, exports, saved searches, favorites)
- Priority: P0 · Status: **VERIFIED** (independent live re-verification 2026-09-27)
- Files: `backend/main.py`, `backend/auth_service.py`, `backend/scoring.py`, `backend/database.py`, `backend/tests/`
- Contract: `SPECS/API_CONTRACT.md`
- Included P0 security fix: removed `eval()` token parsing, standard base64url JSON JWT,
  PBKDF2 bumped to 200k iterations.
- Evidence: 56/56 pytest passing (`.venv/bin/python -m pytest backend/tests/ -q`);
  live curl pass on 2026-09-27: /health (db_rows 7438), search + disjoint cursor pages,
  industry/email/quality filters, facets (50 industries, 34 locations), detail
  (9 signals, unverified), CSV export (attachment, correct headers), signup→login→me
  (3-segment JWT), 401 bad login, 404 detail, saved-search CRUD, favorites CRUD,
  400 export_too_large on uncapped export, 422 bad sort.
- Data fix by parent: 81 bad-id reconstruction fragments moved company → quarantine_raw
  (verified 2026-09-27: company=7438, quarantine_raw=97 = 16 unrecoverable + 81
  bad_id_reconstruction_fragment, 7438+97=7535 = raw parquet count; raw untouched).
- Watchdog re-verification (run #6, 2026-09-27 ~02:05 UTC): pytest 56/56 green
  (one transient DuckDB lock error from a stale writer PID, cleared on re-run);
  independent live pass on 127.0.0.1:8000: health/signup/login/me, search +
  disjoint cursor pages, filters, detail, facets, CSV/JSON/XLSX exports,
  export_too_large 400, sort-injection 422, saved-search/favorite CRUD, 404 shapes.
  No `eval(` in backend. Matches contract v1.
  (company 7519 → 7438, quarantine 16 → 97). Zero bad-id rows remain.

### LEAD-009: Frontend product shell + search UI
- Priority: P0 · Status: **DONE** (implemented; browser E2E in progress)
- Files: `frontend/**` (app/page.tsx dashboard, app/search/page.tsx, app/favorites,
  app/login, app/signup, lib/api.ts, lib/types.ts, lib/auth.tsx)
- Contract: `SPECS/API_CONTRACT.md`
- Evidence: `tsc --noEmit` clean; `next build` green (routes /, /search, /favorites,
  /login, /signup); parent code review confirmed 300ms debounce, AbortController
  cancellation, cursor pagination, loading/empty/error states.

### LEAD-010: Honest lead scoring + backfill
- Priority: P1 · Status: **VERIFIED**
- Files: `backend/scoring.py`
- Evidence: backfill over 7438 rows, 0 NULLs, range 0.0-1.0, avg 0.82; `score_signals`
  JSON present; UI labels it "fit score (unverified data)" with signal breakdown.

### LEAD-011: Export (CSV/JSON/XLSX) with row cap
- Priority: P1 · Status: **VERIFIED**
- Evidence: CSV export returns attachment with correct header row (1325 lines for
  q=software); XLSX correct content-type; uncapped export → 400 `export_too_large`;
  POST /api/v1/companies/export with {ids} for bulk selection.

### LEAD-012: Saved searches + favorites
- Priority: P1 · Status: **VERIFIED**
- Evidence: live curl pass 2026-09-27 — saved search create/list/delete (204 on delete);
  favorite add (201)/list/delete (204), list empty after delete. No login required
  (deliberate single-tenant choice, documented in API contract notes).

### LEAD-013: Test suite (backend pytest, frontend build/typecheck)
- Priority: P1 · Status: **VERIFIED**
- Evidence: `pytest backend/tests/ -q` → 56 passed (auth, companies, exports, collections,
  scoring); `tsc --noEmit` clean; `next build` green. Parent re-ran the suite independently.

### LEAD-014: Live end-to-end verification
- Priority: P0 · Status: **TODO** (after LEAD-008 + LEAD-009)
- Acceptance: real browser/curl run of search, filters, sorting, pagination, detail,
  selection, export, empty/error states, responsive layout. Evidence recorded.

### LEAD-015: Session close-out
- Priority: P1 · Status: **TODO**
- Files: `SESSION_REPORT.md`, `KNOWN_ISSUES.md`, `DECISIONS.md` updates
- Acceptance: report lists only verified functionality; git log reviewed; no secrets committed.

## Legacy tasks (pre-2026-09-27) — corrected states

### LEAD-001: Data Quality Profiling — **DONE** (partial, honest scope)
Was marked VERIFIED with no evidence. Reality: profiling artifacts exist
(`backend/profiling_report.md`, `SOURCE_REGISTRY.md`, canonical schema docs), but they
reference datasets not present in this repo. The one available dataset is profiled,
normalized, and verified under LEAD-006. No further action; scope corrected, not deleted.

### LEAD-002: Search Implementation — **IN_PROGRESS** (superseded by LEAD-008)
Was marked VERIFIED. Reality: the old `/search` was broken (OFFSET pagination,
`total=len(results)`, filter on nonexistent `job_functions` column, disconnected
`search_service.py`). Being rebuilt properly under LEAD-008 with cursor pagination,
parameterized queries, allowlisted sort. Old code to be removed or fixed, not kept.

### LEAD-003: SaaS Foundation — **IN_PROGRESS** (superseded by LEAD-008)
Was marked VERIFIED. Reality: auth used `eval()` on token payloads (P0 security bug),
nonstandard hex token format, in-memory stores, nothing wired to FastAPI.
Being rebuilt under LEAD-008.

### LEAD-004: Compliance & Legal — **TODO** (no evidence of prior completion)
Was marked VERIFIED with "Tests: None (process-oriented)" and no artifacts.
Honest state: not started. Suppression/deletion/retention workflows remain future work;
tracked here so it is not forgotten. Out of scope for the 5-hour build session.

### LEAD-005: Benchmarking & Performance — **TODO**
Was marked VERIFIED; no benchmark report exists in the repo. `BENCHMARK_SUITE.sh`
exists but was never run against real data here. Deferred; optional if time remains.

## Sprint checkboxes (archived 2026-09-27)

The old "P0 — Architecture (DONE)" / "P0 — Data Quality (DONE)" / "P0 — Search (VERIFIED)" /
"P1 — SaaS (VERIFIED)" / "P1 — Compliance (VERIFIED)" sections mixed DONE marks with
unchecked boxes and VERIFIED marks with no evidence. They are superseded by the ledger
above. Kept in git history; not repeated here.
