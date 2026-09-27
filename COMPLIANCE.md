# LeadEngine Compliance Requirements

This is an engineering checklist, not legal advice.

## Core Questions Before Commercial Launch
- What is source/licensing basis for each dataset?
- Does source agreement prohibit scraping, redistribution, or resale?
- What jurisdiction applies?
- What personal data is stored?
- What lawful basis applies?
- What notices are required?
- What deletion/correction rights apply?
- What retention period applies?
- Are data-broker obligations triggered?

## GDPR/UK GDPR-Oriented Engineering
Potential controls:
- source/provenance
- lawful-basis record
- privacy notice
- access workflow
- correction workflow
- deletion workflow
- objection/suppression workflow
- retention policy
- data minimization
- security controls

## California-Oriented Engineering
Potential controls:
- suppression/opt-out
- deletion workflow
- data inventory
- data-source records
- retention controls
- consumer request tracking

## Suppression Schema

```text
suppression_id
email
phone
person_id
company_id
domain
social_url
reason
source
created_at
expires_at
```

Every search/reveal/export should apply suppression rules where required.

## Important
Do not assume:
- public data = unrestricted resale
- B2B contact = outside privacy law
- scraped data = licensed data

Obtain qualified legal review before commercial launch.
