# LeadEngine Session Report — 2026-09-27

Autonomous 5-hour engineering mission on `javedhamzabwn/leadengine` (baseline `c4b8563`),
plus watchdog close-out runs through 10:20 UTC. Local clone at `~/workspace/leadengine`.

## Git state (reviewed 2026-09-27 ~10:20 UTC)
- 7 commits ahead of `origin/main` (tree clean, `git status` empty):
  00c10f7-equivalents through 38a1b86 were replayed onto `origin/main` via the
  GitHub git-database API (user-authorized 2026-09-27 ~06:30 UTC); byte-identical
  trees confirmed. Local HEAD `1a2792c` ("LEAD-014: mark VERIFIED after public
  browser test; make tunnel header conditional") and the replay-duplicates
  (`b5f9ff5`, `99abe7f`, `06cbe95`, `bf43240`, `c25c7b3`, `e37f011`) are not yet
  pushed — push is pending the user's go-ahead.
- Secrets scan: no credentials committed. The only secret-like value in the tree
  is the documented dev-fallback JWT secret (`LEADENGINE_JWT_SECRET` env with
  dev default; flagged in KNOWN_ISSUES.md as production-must-set).
- `data/leadengine.db` is gitignored by design; the build input
  `data/companies_raw.parquet` is tracked. Raw parquet byte-untouched.

## What was delivered

**Data layer (VERIFIED)**
- `data_6.parquet` (7,535 rows, 66 raw cols) normalized into `data/leadengine.db` via
  `backend/normalize.py` (248s). Raw parquet preserved untouched.
- 7,438 canonical companies; 97 rows quarantined (16 unrecoverable + 81 bad-id
  reconstruction fragments moved on 2026-09-27; zero bad-id rows remain).
- Avg quality score 0.959; 5,749 with email; 7,112 with website; 5,350 with LinkedIn.
- Source was mis-split on quoted commas; reconstruction is best-effort.
  `verification_status` = `unverified` everywhere. Nothing is presented as verified.

**Backend API v1 (VERIFIED)**
- `backend/main.py`: FastAPI app implementing `SPECS/API_CONTRACT.md` —
  `/health`, auth (signup/login/me), `GET /api/v1/companies` (keyword, industry,
  location, employee range, has_email/phone/linkedin, min_quality, status filters;
  allowlisted sorts; opaque cursor pagination; no OFFSET; no totals),
  `GET /api/v1/companies/{id}`, `/facets`, `/companies/export` (csv/json/xlsx,
  5000-row cap → 400), `POST /companies/export` {ids} for bulk selection,
  saved-search CRUD, favorites CRUD. Consistent `{error:{code,message}}` bodies.
- P0 security fix: `eval()` token parsing removed; standard base64url JSON JWT
  (HS256, stdlib only); PBKDF2-HMAC-SHA256 at 200,000 iterations.
- `backend/scoring.py`: honest 9-signal fit score backfilled (7438 rows, avg 0.82).
- `backend/tests/`: 56/56 pytest passing. Parent re-ran the suite independently.
- Dead code deleted: `search_service.py`, `lead_service.py`, `organization_service.py`.

**Frontend (VERIFIED build; E2E see below)**
- Next.js App Router: dashboard (`/`), search (`/search`), favorites, login, signup.
- Typed API client (`lib/api.ts`), 300ms debounced search with AbortController,
  cursor pagination, filter panel from `/facets`, results table with selection and
  bulk export, detail drawer with score-signal breakdown labeled
  "fit score (unverified data)", saved searches UI, loading/empty/error states.
- `tsc --noEmit` clean; `next build` green.

**Tracking + watchdog (VERIFIED)**
- `TASKS.md` rewritten with an honesty ledger (DONE = implemented, VERIFIED = named
  evidence); prior false VERIFIED marks corrected, not deleted.
- `WATCHDOG.md`, executable `scripts/watchdog.py`, 10-minute cron `leadengine-watchdog`
  (run #5 all-green; parses the new TASKS.md format).
- `KNOWN_ISSUES.md` and `DECISIONS.md` updated (ADR-009 through ADR-013).
- `.gitignore` fixed: `.venv/`, `data/*.db`, watchdog state excluded.

## Live verification (2026-09-27, backend :8000 + frontend :3000)
- curl pass: search (disjoint cursor pages), filters, facets (50 industries /
  34 locations), detail (9 signals), CSV export (attachment, 1325 lines for
  q=software), auth round-trip (3-segment JWT), 401/404/400/422 error paths,
  saved-search and favorites CRUD.
- UI-flow simulation (watchdog run #9, 18/18 pass): SSR shells 200 on
  /, /search, /favorites, /login, /signup; search q=software (20 rows);
  industry+has_email+min_quality filters; ordered sort; disjoint cursor page 2;
  detail; selection export via POST {ids,format} (200, exactly the selected
  rows); filter export CSV 1325 lines; facets = 50 industries; saved-search
  and favorites CRUD; empty search -> [] null cursor; SQL-injection sort -> 422.
  Viewport meta present.
- True browser click-through (LEAD-014, VERIFIED 2026-09-27): performed in the
  user's own browser against a public localtunnel URL (in-sandbox browser
  routes were proven dead ends — Chromium 152 LNA checks, cloudflared tunnels,
  LAN-IP veth route; documented in KNOWN_ISSUES.md). Dashboard populated:
  7,438 companies, 50 industries, 34 locations, API status ok. Search page:
  q=software with 300ms debounce returned results (welance, viind, wpxpo,
  etc.) with industry/location/employees/founded/quality/fit-score columns.
  Industry facets loaded with counts (Advertising 428, E-Commerce 412, etc.).
  Cursor pagination Page 1 -> Page 2 verified. Company detail drawer opened
  (welance: 100% fit score, unverified-data label). Export all matching (CSV)
  -> 200. Public signup (201) + login (JWT) verified via terminal.
- Tunnel support (2026-09-27, commit 1a2792c): `frontend/lib/api.ts` now sends
  `bypass-tunnel-reminder: 1` only when `API_BASE` is a `.loca.lt` host
  (localtunnel's browser-reminder interstitial); the header is inert on all
  other hosts. `tsc --noEmit` clean (re-verified 2026-09-27 ~10:18 UTC).
- Fresh re-verification (2026-09-27 ~10:15-10:18 UTC, watchdog run #22):
  pytest 56/56 passed; DuckDB live: company 7438, quarantine_raw 97
  (7438+97=7535 = raw parquet count), 0 NULL lead_scores; 0 TODO/FIXME
  markers; no tracebacks in data/*.log; git tree clean.

## Known limitations (not hidden)
- Single-process MVP: auth users in-memory; DuckDB writes slow on this VM (btrfs);
  reads fast. Multi-worker deploy needs a persistent user store.
- JWT dev-secret fallback; set `LEADENGINE_JWT_SECRET` in production.
- Saved searches/favorites need no login (deliberate single-tenant choice).
- Compliance (LEAD-004), benchmarking (LEAD-005): not started, tracked honestly.
- No dedup pass yet; keyword search is ILIKE, not full-text.

## What was NOT done
- No credentials in chat, files, logs, or commits. No fabricated data.
- 7 local commits (incl. LEAD-014 VERIFIED + tunnel-header support) not yet
  pushed; push pending the user's go-ahead (6 earlier commits were pushed
  2026-09-27 ~06:30 UTC, trees byte-identical).
- No fabricated data. Compliance (LEAD-004) and benchmarking (LEAD-005):
  not started, tracked honestly as TODO in TASKS.md.
