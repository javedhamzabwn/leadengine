"""
LeadEngine Organization Service
Organization CRUD, user membership, role assignment.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from auth_service import User, get_user, _users, _email_index


# ── Models ──────────────────────────────────────────────────────────────

@dataclass
class Organization:
    id: str
    name: str
    slug: str
    owner_id: str  # user id of creator
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


# ── Storage ─────────────────────────────────────────────────────────────
# ponytail: in-memory; scale to DuckDB/Postgres
_orgs: dict[str, Organization] = {}
_slug_index: dict[str, str] = {}  # slug -> org_id


def _slugify(name: str) -> str:
    return name.strip().lower().replace(" ", "-").replace("_", "-")


def _ensure_unique_slug(base: str, exclude_id: Optional[str] = None) -> str:
    slug = _slugify(base)
    candidate = slug
    n = 1
    while candidate in _slug_index and _slug_index[candidate] != exclude_id:
        candidate = f"{slug}-{n}"
        n += 1
    return candidate


# ── Public API ──────────────────────────────────────────────────────────

def create_organization(name: str, owner_id: str) -> dict:
    """Create an org and set the owner as its first member (role=owner)."""
    owner = get_user(owner_id)
    if not owner:
        raise ValueError("owner user not found")

    org_id = str(uuid.uuid4())
    slug = _ensure_unique_slug(name)
    org = Organization(id=org_id, name=name.strip(), slug=slug, owner_id=owner_id)
    _orgs[org_id] = org
    _slug_index[slug] = org_id

    # Assign owner to org
    owner.org_id = org_id
    owner.role = "owner"

    return {
        "id": org_id,
        "name": org.name,
        "slug": org.slug,
        "owner_id": owner_id,
        "created_at": org.created_at,
    }


def get_organization(org_id: str) -> Optional[Organization]:
    return _orgs.get(org_id)


def get_organization_by_slug(slug: str) -> Optional[Organization]:
    org_id = _slug_index.get(slug)
    return _orgs.get(org_id) if org_id else None


def update_organization(org_id: str, name: Optional[str] = None, actor_id: Optional[str] = None) -> dict:
    """Update org name. Only owner or admin can rename."""
    org = get_organization(org_id)
    if not org:
        raise ValueError("organization not found")

    if actor_id:
        actor = get_user(actor_id)
        if not actor or actor.org_id != org_id or actor.role not in ("owner", "admin"):
            raise ValueError("insufficient permissions")

    if name:
        org.name = name.strip()
        org.slug = _ensure_unique_slug(name, exclude_id=org_id)
        _slug_index[org.slug] = org_id
    org.updated_at = time.time()

    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "owner_id": org.owner_id,
        "updated_at": org.updated_at,
    }


def list_organization_members(org_id: str) -> list[dict]:
    """Return all users belonging to an org."""
    org = get_organization(org_id)
    if not org:
        raise ValueError("organization not found")
    return [
        {"id": u.id, "email": u.email, "name": u.name, "role": u.role}
        for u in _users.values()
        if u.org_id == org_id
    ]


def assign_role(org_id: str, target_user_id: str, role: str, actor_id: str) -> dict:
    """Change a user's role within an org. Only owner can assign roles."""
    if role not in ("owner", "admin", "member"):
        raise ValueError("role must be owner, admin, or member")

    actor = get_user(actor_id)
    if not actor or actor.org_id != org_id or actor.role != "owner":
        raise ValueError("only org owner can assign roles")

    target = get_user(target_user_id)
    if not target or target.org_id != org_id:
        raise ValueError("target user not in this organization")

    target.role = role
    return {"id": target.id, "email": target.email, "name": target.name, "role": target.role}


def add_member(org_id: str, user_id: str, role: str = "member") -> dict:
    """Add an existing user to an org (used after signup or invite)."""
    org = get_organization(org_id)
    if not org:
        raise ValueError("organization not found")
    user = get_user(user_id)
    if not user:
        raise ValueError("user not found")
    if role not in ("admin", "member"):
        raise ValueError("new members can be admin or member")

    user.org_id = org_id
    user.role = role
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}


# ── Self-test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    from auth_service import signup
    u = signup("owner@acme.com", "secret123", "Owner")
    org = create_organization("Acme Corp", u["id"])
    assert org["slug"] == "acme-corp"
    members = list_organization_members(org["id"])
    assert len(members) == 1
    assert members[0]["role"] == "owner"
    print("organization_service.py OK")