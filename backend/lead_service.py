"""
LeadEngine Lead Service
CRUD for leads (people + company references) within an organization.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from auth_service import get_user
from organization_service import get_organization


# ── Enums ───────────────────────────────────────────────────────────────

class Seniority(str, Enum):
    junior = "junior"
    mid = "mid"
    senior = "senior"
    vp = "vp"
    director = "director"
    cxo = "cxo"


class VerificationStatus(str, Enum):
    verified = "verified"
    unverified = "unverified"


# ── Models ──────────────────────────────────────────────────────────────

@dataclass
class Lead:
    id: str
    org_id: str
    created_by: str  # user id

    # Person fields
    name: str
    title: Optional[str] = None
    seniority: Optional[Seniority] = None
    department: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    contact_availability: bool = False
    verification_status: VerificationStatus = VerificationStatus.unverified
    confidence: float = 0.0

    # Company ref
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    company_industry: Optional[str] = None
    company_employee_count: Optional[int] = None
    company_revenue: Optional[float] = None

    # Metadata
    notes: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


# ── Storage ─────────────────────────────────────────────────────────────
# ponytail: in-memory dict; scale to DuckDB/ClickHouse
_leads: dict[str, Lead] = {}


def _check_org_access(org_id: str) -> None:
    if not get_organization(org_id):
        raise ValueError("organization not found")


def _check_user_in_org(user_id: str, org_id: str) -> None:
    user = get_user(user_id)
    if not user or user.org_id != org_id:
        raise ValueError("user not in this organization")


# ── Public API ──────────────────────────────────────────────────────────

def create_lead(
    org_id: str,
    created_by: str,
    *,
    name: str,
    title: Optional[str] = None,
    seniority: Optional[Seniority] = None,
    department: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    location: Optional[str] = None,
    contact_availability: bool = False,
    company_name: Optional[str] = None,
    company_domain: Optional[str] = None,
    company_industry: Optional[str] = None,
    company_employee_count: Optional[int] = None,
    company_revenue: Optional[float] = None,
    notes: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> dict:
    """Create a new lead within an organization."""
    _check_org_access(org_id)
    _check_user_in_org(created_by, org_id)

    if not name:
        raise ValueError("lead name is required")

    lead = Lead(
        id=str(uuid.uuid4()),
        org_id=org_id,
        created_by=created_by,
        name=name.strip(),
        title=title.strip() if title else None,
        seniority=seniority,
        department=department.strip() if department else None,
        email=email.strip().lower() if email else None,
        phone=phone.strip() if phone else None,
        location=location.strip() if location else None,
        contact_availability=contact_availability,
        company_name=company_name.strip() if company_name else None,
        company_domain=company_domain.strip().lower() if company_domain else None,
        company_industry=company_industry.strip() if company_industry else None,
        company_employee_count=company_employee_count,
        company_revenue=company_revenue,
        notes=notes.strip() if notes else None,
        tags=tags or [],
    )
    _leads[lead.id] = lead
    return _lead_to_dict(lead)


def get_lead(lead_id: str, org_id: str) -> dict:
    """Retrieve a lead by ID within an org context."""
    lead = _leads.get(lead_id)
    if not lead or lead.org_id != org_id:
        raise ValueError("lead not found")
    return _lead_to_dict(lead)


def update_lead(
    lead_id: str,
    org_id: str,
    updated_by: str,
    **kwargs,
) -> dict:
    """Update one or more fields on a lead. Only provided fields change."""
    lead = _leads.get(lead_id)
    if not lead or lead.org_id != org_id:
        raise ValueError("lead not found")
    _check_user_in_org(updated_by, org_id)

    # Allowed mutable fields
    allowed = {
        "title", "seniority", "department", "email", "phone", "location",
        "contact_availability", "confidence", "company_name", "company_domain",
        "company_industry", "company_employee_count", "company_revenue",
        "notes", "tags", "verification_status",
    }

    for key, value in kwargs.items():
        if key not in allowed:
            continue
        if value is not None and isinstance(getattr(lead, key, None), str):
            setattr(lead, key, value.strip())
        else:
            setattr(lead, key, value)

    lead.updated_at = time.time()
    return _lead_to_dict(lead)


def list_leads(
    org_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
    seniority: Optional[Seniority] = None,
    department: Optional[str] = None,
    company_name: Optional[str] = None,
) -> dict:
    """List leads in an org with optional filters."""
    _check_org_access(org_id)

    results = [l for l in _leads.values() if l.org_id == org_id]

    # Basic filtering
    if search:
        search_lower = search.lower()
        results = [
            l for l in results
            if search_lower in l.name.lower()
            or (l.title and search_lower in l.title.lower())
            or (l.email and search_lower in l.email)
        ]
    if seniority:
        results = [l for l in results if l.seniority == seniority]
    if department:
        results = [l for l in results if l.department and department.lower() in l.department.lower()]
    if company_name:
        results = [l for l in results if l.company_name and company_name.lower() in l.company_name.lower()]

    total = len(results)
    page = results[offset:offset + limit]

    return {
        "leads": [_lead_to_dict(l) for l in page],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def delete_lead(lead_id: str, org_id: str, deleted_by: str) -> dict:
    """Soft-delete a lead by removing it from the store."""
    _check_user_in_org(deleted_by, org_id)
    lead = _leads.pop(lead_id, None)
    if not lead or lead.org_id != org_id:
        raise ValueError("lead not found")
    return {"deleted": lead_id}


# ── Helpers ─────────────────────────────────────────────────────────────

def _lead_to_dict(lead: Lead) -> dict:
    return {
        "id": lead.id,
        "org_id": lead.org_id,
        "created_by": lead.created_by,
        "name": lead.name,
        "title": lead.title,
        "seniority": lead.seniority.value if lead.seniority else None,
        "department": lead.department,
        "email": lead.email,
        "phone": lead.phone,
        "location": lead.location,
        "contact_availability": lead.contact_availability,
        "verification_status": lead.verification_status.value,
        "confidence": lead.confidence,
        "company_name": lead.company_name,
        "company_domain": lead.company_domain,
        "company_industry": lead.company_industry,
        "company_employee_count": lead.company_employee_count,
        "company_revenue": lead.company_revenue,
        "notes": lead.notes,
        "tags": lead.tags,
        "created_at": lead.created_at,
        "updated_at": lead.updated_at,
    }


# ── Self-test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    from auth_service import signup
    from organization_service import create_organization

    u = signup("leaduser@acme.com", "secret123", "Lead User")
    org = create_organization("DataCorp", u["id"])

    lead = create_lead(org["id"], u["id"], name="Jane Doe", title="CTO",
                       company_name="DataCorp", seniority=Seniority.cxo)
    assert lead["name"] == "Jane Doe"

    fetched = get_lead(lead["id"], org["id"])
    assert fetched["title"] == "CTO"

    updated = update_lead(lead["id"], org["id"], u["id"], title="CEO")
    assert updated["title"] == "CEO"

    listing = list_leads(org["id"], search="jane")
    assert listing["total"] == 1

    deleted = delete_lead(lead["id"], org["id"], u["id"])
    assert deleted["deleted"] == lead["id"]

    print("lead_service.py OK")