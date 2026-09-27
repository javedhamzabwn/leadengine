# LeadEngine Canonical Schema

## Entity Definitions

### Person
- **id** (UUID) – Primary key
- **name** (string) – Full name
- **title** (string) – Job title
- **seniority** (enum) – e.g., Junior, Mid, Senior, VP, Director
- **department** (string) – Functional group
- **company** (Person/Company reference)
- **location** (string) – City/region
- **email** (string) – Verified email
- **phone** (string) – Verified phone
- **contact_availability** (bool) – Availability flag
- **freshness** (float) – Days since last update
- **confidence** (float) – 0.0–1.0 quality score
- **related_company** (Person reference)
- **verification_status** (enum) – Verified/Unverified

### Company
- **id** (UUID)
- **name** (string)
- **domain** (string)
- **industry** (string)
- **employee_count** (int)
- **revenue** (float)
- **funding_stage** (enum) – Seed, Series A, etc.
- **founded_year** (int)
- **hq_location** (string)
- **technologies** (array of strings)
- **social_profiles** (array of strings)
- **verification_status** (enum) – Verified/Unverified

### Technology
- **id** (UUID)
- **name** (string)
- **version** (string)
- **description** (string)
- **source** (Person/Company reference)

### Location
- **id** (UUID)
- **city** (string)
- **country** (string)
- **timezone** (string)

## Relationships
- Person ↔ Company (many-to-one)
- Company ↔ Technology (many-to-many via enrichment)
- Location → Person/Company (many-to-one)

## Provenance
All entities retain `source_record_id` linking to the original raw Parquet record. Changes are tracked via `updated_at` timestamp and `quality_score` decay.
