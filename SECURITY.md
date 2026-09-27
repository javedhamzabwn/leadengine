# LeadEngine Security Plan

## SQL
- Parameterize all user-controlled values.
- Allowlist dataset identifiers.
- Allowlist columns.
- Allowlist sort fields and directions.
- Never concatenate arbitrary user SQL.

## Authentication
- Secure password hashing.
- Email verification.
- MFA for higher-risk plans.
- Secure session cookies.
- API key rotation.

## Authorization
- Organization isolation.
- Role-based access control.
- Per-user/per-team export permissions.
- Per-plan field access.

## Abuse Prevention
- IP rate limiting.
- Account rate limiting.
- Organization rate limiting.
- Concurrent query limits.
- Export limits.
- Reveal limits.
- Anomaly detection.

## Web Security
- CSP.
- HSTS.
- Secure headers.
- CSRF protection where applicable.
- Input validation.
- Output encoding.
- Dependency scanning.

## Audit
Record:
- login events
- API key events
- exports
- data reveals
- enrichment
- billing changes
- permission changes
- deletion requests

## Data Protection
- Encryption in transit.
- Encryption at rest where supported.
- Secrets outside source code.
- Backup protection.
- Least privilege.

## Suppression
Every search/reveal/export pipeline should honor suppression rules.
