# LeadEngine API Contract v1

Base URL: `http://127.0.0.1:8000`. All product routes live under `/api/v1`.
Legacy `/search` (POST) is removed. Auth is Bearer JWT (standard base64url JSON, HS256).

## Conventions

- Errors: HTTP status + body `{ "error": { "code": "string", "message": "human readable", "details": {} } }`.
  Never 200-with-error, never stack traces to clients.
- Pagination: cursor-based. `limit` default 25, max 100. `cursor` is opaque base64url
  encoding of the last row's sort key + id. Response: `{ "items": [], "next_cursor": str|null, "limit": n }`.
  No OFFSET, no exact total counts on list endpoints (estimates allowed via facets).
- Sorting: `sort` param allowlisted per endpoint, `dir=asc|desc`. Identifiers never interpolated.
- All SQL parameterized. No string-built WHERE clauses.

## Endpoints

### GET /health
`{ "status": "ok", "service": "leadengine-api", "version": "1.0.0", "db_rows": 7519 }`

### POST /api/v1/auth/signup
Body `{ "email": str, "password": str (min 8), "name": str }` → 201 `{ "user": User }`.
409 `email_taken`. 422 validation.

### POST /api/v1/auth/login
Body `{ "email": str, "password": str }` → `{ "token": "jwt", "user": User }`.
401 `invalid_credentials` (same message for unknown email vs wrong password).

### GET /api/v1/auth/me
Bearer required → `{ "user": User }`. 401 `invalid_token` when missing/bad/expired.

`User = { id, email, name, org_id, role, created_at }`. Passwords: PBKDF2-HMAC-SHA256,
min 200k iterations, 16-byte salt, `salt_hex:dk_hex` storage. Secret from
`LEADENGINE_JWT_SECRET` env (dev fallback only, never committed).

### GET /api/v1/companies
Query params (all optional):
- `q`: keyword, matches `search_text` (ILIKE %q%), min 2 chars
- `industry`: exact match on `industry` (repeatable: `?industry=A&industry=B`)
- `location`: ILIKE on `hq_location`
- `employees_min`, `employees_max`: integer range overlap against `employees_min/max`
- `has_email`, `has_phone`, `has_linkedin`: `true|false`
- `min_quality`: float 0..1 on `quality_score`
- `operating_status`: exact (`active`, `closed`, ...)
- `sort`: one of `name|quality_score|employees_max|founded_year` (default `quality_score`)
- `dir`: `asc|desc` (default `desc`, except `name` → `asc`)
- `limit`, `cursor`

Item shape (CompanySummary):
`{ id, name, domain, website, industry, hq_location, employee_enum, employees_min,
   employees_max, founded_year, operating_status, has_email, has_phone, has_linkedin,
   quality_score, lead_score, verification_status }`
(`has_*` derived from underlying columns; never expose raw emails in list view —
full contact fields only on detail.)

### GET /api/v1/companies/{id}
Full Company: summary fields plus
`{ description, email, email_valid, phone, facebook, linkedin, twitter, industries,
   locations_raw, location_tail, funding_total_usd, funding_rounds, last_funding_type,
   last_funding_at, founded_on, company_type, ipo_status, crunchbase_url,
   score_signals, source, observed_at }`.
`verification_status` is always `unverified` until a real verification pipeline exists.
404 `not_found`.

### GET /api/v1/companies/facets
`{ "industries": [{value, count}...top 50], "locations": [...top 50],
   "operating_statuses": [...], "employee_ranges": [{value: enum, label, count}] }`
Counts are exact (cheap on 7.5k rows).

### GET /api/v1/companies/export
Same filters as list + `format=csv|json|xlsx` + optional `columns` (allowlisted).
Returns file download (`Content-Disposition: attachment`). Cap 5,000 rows; above that
→ 400 `export_too_large` with a message to narrow filters. (Async exports deferred.)

### Saved searches (persisted in DuckDB `saved_search` table)
- `GET /api/v1/saved-searches` → `{ items: [{id, name, filters, created_at}] }`
- `POST /api/v1/saved-searches` `{ name, filters }` → 201 item
- `DELETE /api/v1/saved-searches/{id}` → 204

### Favorites
- `POST /api/v1/companies/{id}/favorites` → 201 `{ company_id, created_at }`
- `DELETE /api/v1/companies/{id}/favorites` → 204
- `GET /api/v1/favorites` → cursor-paginated CompanySummary list

## Lead scoring (honest signals only)

`lead_score` 0..1, computed in `backend/scoring.py`, backfilled into `company.lead_score`
with `score_signals` as JSON list of `{signal, points, detail}`. Signals:
- has valid email: +0.25
- has linkedin: +0.15
- has phone: +0.10
- quality_score >= 0.9: +0.15 (0.7..0.9: +0.08)
- operating_status = active: +0.10
- website present: +0.10
- employees known: +0.05
- founded_year known: +0.05
- industry known: +0.05
Cap at 1.0. The UI must label this "fit score (unverified data)" and show the
signal breakdown. Never present as verified intent.

## Frontend expectations

- `GET /api/v1/companies?...` drives the search page; `facets` populates filters.
- Debounced search input (300ms), request cancellation on new keystroke.
- Table with column chooser, row selection, bulk export of selected ids
  (`POST /api/v1/companies/export` with `{ids: [...]}` — backend agent: add this).
- Detail drawer via `/companies/{id}`. Empty/error/loading states everywhere.
- API base URL from `NEXT_PUBLIC_API_URL` (default `http://127.0.0.1:8000`).
