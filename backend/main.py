"""LeadEngine FastAPI Application

Central API server connecting frontend (Next.js) to backend services.
Runs on http://127.0.0.1:8000

Endpoints:
- GET /health - Health check
- POST /auth/signup - User registration
- POST /auth/login - User login  
- GET /auth/me - Current user info
- GET /organizations - List organizations
- POST /organizations - Create organization
- GET /leads - Search/paginate leads
- POST /leads - Create lead
- GET /leads/{id} - Get single lead
- DELETE /leads/{id} - Soft-delete lead
- GET /search - Search leads (POST with filters)
- GET /benchmarks - Run benchmark suite
"""

import os
import sys
from pathlib import Path
from fastapi import FastAPI

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import search_leads, init_database

app = FastAPI(title="LeadEngine API", version="0.1.0")


@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "leadengine-api"}


# Search endpoint
@app.post("/search", tags=["search"])
async def search_leads_endpoint(
    payload: dict = ...,
):
    """Search leads with parameterized filters.

    Supported filters:
    - department: exact match
    - title: ILIKE partial match
    - seniority: exact match
    - location: ILIKE partial match
    - industry: ILIKE partial match
    - keyword: ILIKE on full_name, current_title, current_company
    - limit: int, default 50
    - offset: int, default 0
    """
    # Ensure database is initialized
    init_database()

    filters = payload.get("filters", {})
    limit = payload.get("limit", 50)
    offset = payload.get("offset", 0)

    # Search
    results = search_leads(filters=filters, limit=limit, offset=offset)

    return {
        "results": results,
        "total": len(results),
        "page": (offset // limit) + 1,
        "pages": 1,
    }
