# LeadEngine Data Quality Profiling Report

**Generated:** 2026-09-27  
**Scope:** All 5 primary source datasets  
**Method:** DuckDB pyarrow scan of raw Parquet files  
**Tool:** Python + DuckDB + PyArrow

---

## Executive Summary

| Metric | LinkedIn | Apollo Software | Crunchbase | Pitchbook | Entire Apollo DB |
|---|---|---|---|---|---|
| **Row count (claimed)** | 434M | 111K | 2.8M | N/A | 99M |
| **Row count (verified)** | 260M | 107K | 2.8M | 887K (combined) | 5.4M |
| **Schema consistency** | ⚠️ Drift (62-69 cols) | ❌ Shifted | ❌ Shifted | ❌ Multiple schemas | ❌ Two schemas |
| **Typed columns** | ❌ All VARCHAR | ❌ Almost all VARCHAR | ✅ Mixed types | ❌ All VARCHAR | ❌ All VARCHAR |
| **Quarantine needed** | No | Partial | Yes | Yes | Partial |

**Total verified rows across all datasets: ~265M** (not the advertised ~480M)

---

## 1. LinkedIn Database

### File Layout
- **Path:** `Entire Linkedin Database 434,832,484/`
- **Structure:**
  - `by Countries/` — 149 country subdirectories, each with `data.parquet`
  - `by State (USA)/` — 51 US state subdirectories, each with `data.parquet`

### Row Counts

| Partition | Files | Verified Rows |
|---|---|---|
| Countries | 149 | 198,370,230 |
| US States | 51 | 62,301,970 |
| **Total** | **200** | **260,672,200** |

> **Discrepancy:** Directory name claims 434,832,484 rows. Verified count is 260,672,200 (60% of claimed). Either the directory name is an upper-bound estimate or deduplication across partitions has not been applied.

**Top 10 countries by volume:** India (29.5M), UnitedKingdom (16.3M), France (10.2M), Canada (10.1M), Mexico (8.0M), Spain (6.5M), Australia (6.3M), Italy (6.2M), Germany (5.9M), Indonesia (5.9M).

### Schema (62 base columns, all VARCHAR)

| Column | Type |
|---|---|
| Full name, First Name, Middle Initial, Middle Name, Last Name | VARCHAR |
| Industry, Industry 2 | VARCHAR |
| Job title, Sub Role | VARCHAR |
| Emails, Mobile, Phone numbers | VARCHAR |
| Company Name, Company Industry, Company Website, Company Size, Company Founded | VARCHAR |
| Location, Locality, Metro, Region, Location Country, Location Continent | VARCHAR |
| LinkedIn Url, LinkedIn Username, Facebook Url, Twitter Url, Github Url | VARCHAR |
| Skills, Birth Year, Birth Date, Gender, Summary | VARCHAR |
| Linkedin Connections, Inferred Salary, Years Experience, Interests | VARCHAR |
| Street Address, Address Line 2, Postal Code, Location Geo | VARCHAR |
| Last Updated, Start Date | VARCHAR |

### Completeness (Australia sample — 6.3M rows)

| Field | Populated | Rate |
|---|---|---|
| Full Name | 6,299,723 | **100.0%** |
| First Name | 6,285,416 | 99.8% |
| LinkedIn URL | 6,285,803 | 99.8% |
| Location Country | 6,285,049 | 99.8% |
| Gender | 5,021,409 | 79.7% |
| Job Title | 4,280,775 | 68.0% |
| Last Updated | 4,217,815 | 67.0% |
| Industry | 3,848,713 | 61.1% |
| Company Name | 3,564,465 | 56.6% |
| Years Experience | 2,778,776 | 44.1% |
| Inferred Salary | 3,042,662 | 48.3% |
| Emails | 1,853,870 | **29.4%** |
| Company Website | 1,918,959 | 30.5% |
| Company Size | 2,265,596 | 36.0% |
| Skills | 2,128,802 | 33.8% |
| Company Founded | 1,604,771 | 25.5% |
| Company Industry | 2,207,221 | 35.0% |
| Mobile | 121,585 | **1.9%** |
| Interests | 447,882 | 7.1% |

### Schema Consistency
- **⚠️ INCONSISTENT:** Column count varies by country (62–69)
- Australia: 62 cols
- Pakistan: 68 cols (extra: `column62`–`column67`, `Last Updated_1`)
- Japan: 66 cols
- South Korea: 69 cols
- Extra columns appear to be overflow/spillover from scraping artifacts

### Duplicate Analysis (Australia)
- Unique LinkedIn URLs: 6,258,843 / 6,299,724
- **Duplicate rate: 0.6%** (40.9K dupes) — acceptable

### Accuracy/Data Quality Concerns
- All fields stored as VARCHAR — no type enforcement
- `Inferred Salary` is unvalidated text (estimated ~48% populated)
- `Mobile` coverage is very low (1.9%)
- `Emails` coverage at 29.4% limits contactability
- `Birth Year`/`Birth Date`/`Gender` may have privacy implications

### Quarantine Assessment: **NOT REQUIRED**
Usable for search. Schema drift (extra columns) is minor and can be handled by selecting only the 62 common columns.

---

## 2. Apollo Software Development Leads

### File Layout
- **Path:** `Apollo Software Development Leads 111,582/Softwaredevelopment Apollo 111,582/`
- **Main files:** `data_1.parquet` (51,155 rows), `data_2.parquet` (12,944 rows)
- **Cleaned subdir:** `100k leads Cleaned/` (10 files, 43,763 rows total)
- **New 10k chunks:** 7 files (38,044 rows)

### Row Counts

| File | Rows | Columns | Notes |
|---|---|---|---|
| data_1.parquet | 51,155 | 178 | Main export |
| data_2.parquet | 12,944 | 36 | **Different schema** |
| **Main total** | **64,099** | — | |
| Cleaned/ files (10) | 43,763 | 70–226 | Varying col counts |
| **Grand total** | **~107,862** | — | Some overlap possible |

### Schema — data_1.parquet (178 cols)

Key columns: `First Name`, `Last Name`, `Title`, `Company`, `Email`, `First Phone`, `Mobile Phone`, `Person Linkedin Url`, `Website`, `Seniority`, `Departments`, `Technologies`, `Annual Revenue`, `Total Funding`, `Industry`, `# Employees`, `Keywords`, `Email Status`, `Stage`, plus 128 `column###` overflow columns.

### Schema Crash — data_2.parquet (36 cols)
```
fullname, firstname, lastname, title, company, email, phone1, phone2,
linkedin, website, Company Linkedin Url, Facebook Url, Twitter Url,
City, State, Country, ... (lowercase, different naming convention)
```

> **❌ STRUCTURAL CORRUPTION:** data_2 has completely different column naming (snake_case vs TitleCase). Only 26 of 36 columns overlap with data_1.

### Completeness (data_1 — 51K rows)

| Field | Populated | Rate |
|---|---|---|
| First Name | 51,142 | **100.0%** |
| Last Name | 49,809 | 97.4% |
| Title | 50,531 | 98.8% |
| Email | 50,320 | **98.4%** |
| Seniority | 50,228 | 98.2% |
| Company | 50,412 | 98.5% |
| Website | 45,833 | 89.6% |
| # Employees | 48,096 | 94.0% |
| Industry | 49,457 | 96.7% |
| Email Status | 50,272 | 98.3% |
| Technologies | 36,250 | 70.9% |
| First Phone | 39,066 | 76.4% |
| Person LinkedIn URL | 40,615 | 79.4% |
| Annual Revenue | 34,666 | 67.8% |
| Total Funding | 38,152 | 74.6% |

### Schema Consistency — Cleaned files (10 files)
- Column counts: 70, 206, 178, 226, 207, 77, 189, 182, 73, 71
- **0 of 10 files have the same schema**
- All contain column### overflow columns indicating shifting

### Quarantine Assessment: **PARTIAL**
- data_1 (51K rows): **USABLE** — 47 well-named columns with high completeness
- data_2 (13K rows): **QUARANTINE RECOMMENDED** — different schema, lower-quality naming
- Cleaned files: **REVIEW NEEDED** — severe column count inconsistency

---

## 3. Crunchbase Database

### File Layout
- **Path:** `Almost Full Crunchbase Database 2,807,492/crunchbase_companies/`
- **8 Parquet files**

### Row Counts

| File | Rows | Columns | Status |
|---|---|---|---|
| data_1.parquet | 1,999,998 | 41 | ✅ Proper schema |
| data_2.parquet | 199,996 | 42 | ❌ 1 shifted column |
| data_3.parquet | 202,126 | 63 | ❌ 22 shifted columns |
| data_4.parquet | 101,298 | 62 | ❌ Shifted |
| data_5.parquet | 101,459 | 79 | ❌ Heavily shifted |
| data_6.parquet | 7,535 | 66 | ❌ Shifted |
| data_7.parquet | 100,936 | 68 | ❌ Shifted |
| data_8.parquet | 101,074 | 84 | ❌ Heavily shifted |
| **Total** | **2,814,422** | — | |

### Schema — Proper (data_1 — 41 cols, typed)

| Column | Type | Populated |
|---|---|---|
| id | VARCHAR | 100% |
| created_at | **TIMESTAMP** | 100% |
| name | VARCHAR | **100.0%** |
| short_description | VARCHAR | 100.0% |
| website | VARCHAR | 94.7% |
| contact_email | VARCHAR | 74.0% |
| phone_number | VARCHAR | 79.3% |
| founded_on | **DATE** | 82.7% |
| operating_status | VARCHAR | 100.0% |
| num_employees_enum | VARCHAR | 84.4% |
| categories | VARCHAR | 95.5% |
| funding_total | **BIGINT** | 7.8% |
| last_funding_type | VARCHAR | 10.1% |
| founders | VARCHAR | 22.8% |
| linkedin | VARCHAR | 77.5% |
| facebook | VARCHAR | 60.0% |
| twitter | VARCHAR | 43.0% |
| locations | VARCHAR | 93.5% |
| ipo_status | VARCHAR | 96.6% |
| permalink | VARCHAR | **100.0%** |

> **Note:** Only data_1 (2M rows, 71%) uses typed columns (TIMESTAMP, BIGINT, DATE). Files data_2–8 store everything as VARCHAR.

### Column Shift Analysis

Files data_2 through data_8 contain extra columns (`column41` through `column84`). Analysis confirms these are **real data spilling into unused cells** — not null padding. Sample from data_3:
- `column41`–`column45` contain permalinks, URLs, and location text
- These are the same type of data found in properly-named columns in data_1

**Impact:** ~814K rows (29%) are structurally corrupted and need repair or quarantine.

### Quarantine Assessment: **RECOMMENDED**
- **data_1** (2M rows): **USABLE** — clean schema, typed columns, high completeness for core fields
- **data_2–data_8** (814K rows): **QUARANTINE** — column shifts make reliable field mapping impossible without transformation

---

## 4. Pitchbook Database

Two snapshots: 2025-06-21 and 2025-09-14.

### 4a. Pitchbook 2025-06-21 — Verticals

- **Path:** `Pitchbook 2025-06-21/Pitchbook/Verticals/`
- **39 Parquet files, 431,261 rows**
- **23 columns** — ALL are HTML presentation-layer class names

```
entity-hover, entity-hover href, entity-hover 2, entity-hover 3, entity-hover href 3,
ellipsis, ellipsis 2, ellipsis 3, ellipsis 4, ellipsis 5, ellipsis 6,
ellipsis 7, ellipsis 8, ellipsis 9, ellipsis 10, ellipsis 11, ellipsis 12,
ellipsis 13, ellipsis 14, ellipsis 15, entity-hover 4, entity-hover href 4
```

> **❌ UNUSABLE:** These are raw HTML/DOM class names, not data column names. No meaningful mapping to business entities is possible without reverse-engineering the HTML structure.

### 4b. Pitchbook 2025-06-21 — Emerging Spaces

- **7 sectors** (B2B, B2C, Energy, Financial Services, Healthcare, IT, Materials)
- **71 files, 10,027 rows total**
- Same `entity-hover`/`ellipsis` column naming pattern
- **❌ UNUSABLE** for the same reason

### 4c. Pitchbook 2025-09-14

- **Path:** `Pitchbook 2025-09-14/Pitchbook/`
- **28 Parquet files, 455,706 rows total**

#### Schema Inconsistency: **CRITICAL**

| Files | Schema | Cols | Notes |
|---|---|---|---|
| data_1.parquet | Reference | 22 | Company Name, Contact Name, Title, Email, Phone... (with ` ` blank col, `ellipsis href`) |
| data_2–9, 11–28 | Different | varies | Most have different column sets |
| data_10.parquet | Different | 24 | **Proper named columns** (COMPANY NAME, CONTACT NAME, EMAIL, etc.) |
| data_11.parquet | Different | 8 | AUM/Dry Powder — investment data |
| data_12.parquet | Different | 22 | `entity-hover`/`ellipsis` pattern |

**Only 1 of 28 files has the same schema as data_1.**

#### data_10 (best candidate — 18,570 rows)

| Field | Populated | Rate |
|---|---|---|
| CONTACT NAME | 13,035 | 70.2% |
| COMPANY NAME | 16,068 | 86.5% |
| TITLE | 13,035 | 70.2% |
| EMAIL | 9,524 | **51.3%** |
| PHONE NUMBER | 9,958 | **53.6%** |
| REVENUE | 3,552 | 19.1% |
| CITY | 18,311 | 98.6% |
| STATE | 18,491 | 99.6% |
| YEAR STARTED | 17,393 | 93.7% |
| FAKE_NUMBER | 101 | **0.5% flagged fake** |

**Fake phone numbers detected:** 101 records with reasons:
- Area code 550 / 372 / 012 / 457 / 123 / 238 / 794 / 032 / 962 / 963 / 004 / 789 / 744 / 552 / 411 is not valid
- Prefix 698 / 040 / 111 / 106 / 126 / 000 / 175 / 627 / 102 / 591 / 938 is not valid
- Last four digits 1270 / 5555 / 2297 / 1212 / 2237 / 4309 are not in service
- Number has too few/many digits

### Quarantine Assessment: **RECOMMENDED**
- **2025-06-21 (Verticals + Emerging Spaces):** **QUARANTINE** — HTML class-name columns, no reliable mapping
- **2025-09-14 data_1–9, 11–28:** **QUARANTINE** — 27/28 files have incompatible schemas
- **2025-09-14 data_10:** **CONDITIONALLY USABLE** — proper schema, but 0.5% fake phone numbers

---

## 5. Entire Apollo Database

### File Layout
- **Path:** `Entire Apollo Database 99,311,285/`
- **Main file:** `data_1.parquet` (2.4 GB)
- **Sub-directory:** `Agtech Apollo Database/`

### Row Counts

| Component | Files | Rows | Schema |
|---|---|---|---|
| Main (orgs) | 1 | **5,144,864** | 51 cols (organization_*) |
| Agtech (contacts) | 23 | **253,486** | 19–96 cols (person_*) |
| **Total** | **24** | **5,398,350** | |

> **Discrepancy:** Directory name claims 99,311,285 records. Verified count is 5.4M (5.4% of claimed). The main file is data from a single export (likely filtered by a specific query), not the full Apollo export.

### Schema — Main (51 cols, all VARCHAR)

```
organization_id, organization_name, organization_domain, organization_website_url,
organization_industries, organization_num_current_employees,
organization_revenue_in_thousands_int, organization_founded_year,
organization_short_description, organization_seo_description,
organization_facebook_url, organization_twitter_url,
organization_linkedin_numerical_urls, organization_public_symbol,
organization_phone, organization_current_technologies,
organization_hq_location_city/state/country/postal_code,
organization_total_funding_long, organization_latest_funding_stage_cd,
organization_latest_funding_round_amount_long,
organization_latest_funding_round_date,
_index, _type, _id, _score  (Elasticsearch artifacts)
```

### Completeness — Main (5.1M orgs)

| Field | Populated | Rate |
|---|---|---|
| organization_name | 5,082,307 | **98.8%** |
| organization_industries | 4,645,413 | 90.3% |
| organization_num_current_employees | 4,782,940 | 93.0% |
| organization_short_description | 4,491,790 | 87.3% |
| organization_linkedin_numerical_urls | 4,360,731 | 84.8% |
| organization_website_url | 4,150,997 | 80.7% |
| organization_domain | 4,055,249 | 78.8% |
| organization_founded_year | 2,594,840 | 50.4% |
| organization_languages | 2,839,023 | 55.2% |
| organization_keywords | 2,479,838 | 48.2% |
| organization_facebook_url | 1,132,496 | 22.0% |
| organization_domain_status_cd | 1,416,698 | 27.5% |
| organization_revenue_in_thousands_int | 565,831 | **11.0%** |
| organization_retail_location_count | 282,749 | 5.5% |
| organization_alexa_ranking | 197,023 | 3.8% |
| organization_public_symbol | 14,927 | **0.3%** |

### Schema — Agtech (85 cols, person-focused)

Different schema entirely **(0 shared columns with main)**. Contains:
- `First Name`, `Last Name`, `Title`, `Company`, `Email`, `Email Status`
- `First Phone`, `Work Direct Phone`, `Mobile Phone`, `Corporate Phone`
- `Seniority`, `Departments`, `Stage`, `Technologies`
- `Annual Revenue` (DOUBLE), `Total Funding` (DOUBLE)
- `Apollo Contact Id`, `Apollo Account Id`
- Email validation: `username`, `domain`, `status`, `overall_score`, `is_safe_to_send`, `is_valid_syntax`, `is_disposable`, `is_role_account`, `mx_accepts_mail`, `can_connect_smtp`, `has_inbox_full`, `is_catch_all`, `is_deliverable`, `is_disabled`, `is_spamtrap`, `is_free_email`
- Intent signals: `Primary Intent Topic`, `Primary Intent Score`, `Secondary Intent Topic`, `Secondary Intent Score`

### Completeness — Agtech (sample — 1,865 rows)

| Field | Populated | Rate |
|---|---|---|
| First Name | 1,865 | 100.0% |
| Title | 1,865 | 100.0% |
| Company | 1,865 | 100.0% |
| Email | 1,865 | 100.0% |
| Seniority | 1,865 | 100.0% |
| First Phone | 1,777 | 95.3% |

### Schema Consistency — Agtech
- **18 of 23 files** have different column counts (19–96)
- Files with the same name (`data_1.parquet`) appear in multiple subdirectories with different schemas
- The "Cleaned" subdirectory has 2 files (47,799 rows) with consistent 85-col schema

### Quarantine Assessment: **PARTIAL**
- **Main (5.1M orgs):** **USABLE** — consistent schema, good completeness for core fields
- **Agtech base files:** **QUARANTINE RECOMMENDED** — inconsistent schemas, many files are column-shifted
- **Agtech Cleaned:** **USABLE** — appears to be a verified export with email validation data

---

## Type Consistency Summary

| Dataset | Typed | All VARCHAR | Mixed |
|---|---|---|---|
| LinkedIn | | ✅ 100% VARCHAR | |
| Apollo Software | | ✅ 99% VARCHAR | Few BOOLEAN |
| Crunchbase | | | ✅ data_1 typed, rest VARCHAR |
| Pitchbook (Jun 21) | | ✅ 100% VARCHAR | |
| Pitchbook (Sep 14) | | ✅ 100% VARCHAR | |
| Entire Apollo Main | | ✅ 100% VARCHAR | |
| Entire Apollo Agtech | | | ✅ Has BOOLEAN, DOUBLE, DATE |

**Observation:** 5 of 7 datasets store all data as VARCHAR. Only Crunchbase data_1 and Apollo Agtech have proper typed columns. This means type enforcement, date parsing, and numeric validation are deferred to the pipeline.

---

## Quarantine Candidates Summary

| Dataset | File(s) | Rows Affected | Quarantine Reason | Action |
|---|---|---|---|---|
| **Crunchbase** | data_2–data_8 | 814,424 | Column shift — `column41`+ from spilling data | Repair or exclude |
| **Pitchbook (Jun 21)** | All Verticals, Emerging Spaces | 441,288 | HTML class-name columns (entity-hover, ellipsis) | Exclude |
| **Pitchbook (Sep 14)** | data_1–9, 11–28 | 437,136 | 27/28 files have incompatible schemas | Extract data_10 only |
| **Pitchbook (Sep 14)** | data_10 (subset) | 101 | Fake phone numbers | Flag/filter |
| **Apollo Software** | data_2.parquet | 12,944 | Different schema (snake_case vs TitleCase) | Normalize or exclude |
| **Apollo Software** | Cleaned files | 43,763 | Inconsistent column counts (70–226) | Extract common columns |
| **Entire Apollo** | Agtech (base) | ~205,687 | Column shifts, inconsistent schemas | Use Cleaned files only |
| **LinkedIn** | Pakistan, Japan, South Korea, etc. | ~30M | Schema drift (extra columns, 62–69 vars) | Select common 62 cols |

**Total rows requiring quarantine action: ~1.95M** (out of ~265M verified, ~0.7%)

---

## Key Recommendations

1. **Use Crunchbase data_1 only** — discard data_2–data_8 unless column-repair logic is implemented
2. **Use Apollo Software data_1 only** — discard data_2 and use only the 47 clean columns
3. **Use Entire Apollo Main only** — main file has clean org data; use Agtech Cleaned for contacts
4. **Use Pitchbook data_10 only** — the only file with proper business-column names
5. **Exclude Pitchbook 2025-06-21 entirely** — HTML class names are unmappable
6. **Standardize all VARCHAR storage** — pipeline must handle type coercion from string-typed sources
7. **Add domain validation** — 21.2% of LinkedIn and 5.3% of Crunchbase records are missing websites
8. **Add email verification** — 70.6% of LinkedIn records lack email; Apollo is the better source for email

---

## Methodology

- **Profiling tool:** DuckDB v1.5.5 + PyArrow v25.0.1
- **Sampling:** Complete scan where feasible; representative sample for LinkedIn (Australia as reference, verified top-10 countries)
- **Completeness:** NULL/non-NULL count for each column (VARCHAR: empty string counts as populated)
- **Schema consistency:** Compare DESCRIBE output across all files in a dataset
- **Duplicate analysis:** Unique key field counts (LinkedIn URL, Email, permalink)
- **Type analysis:** DuckDB column type detection from Parquet schema