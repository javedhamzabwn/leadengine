"""LeadEngine configuration — environment variables with safe defaults.

Never commit secrets. Copy the variable names into your shell or a local
`.env` file (which is git-ignored) when you need to override defaults.
"""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

DATA_DIR = Path(os.environ.get("LEADENGINE_DATA_DIR", PROJECT_ROOT / "data"))
RAW_PARQUET = Path(os.environ.get("LEADENGINE_RAW_PARQUET", DATA_DIR / "companies_raw.parquet"))
DB_PATH = Path(os.environ.get("LEADENGINE_DB_PATH", DATA_DIR / "leadengine.db"))

API_HOST = os.environ.get("LEADENGINE_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("LEADENGINE_PORT", "8000"))

# Comma-separated origins allowed to call the API from a browser.
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("LEADENGINE_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if o.strip()
]

JWT_SECRET = os.environ.get("LEADENGINE_JWT_SECRET", "dev-secret-change-me")
JWT_TTL_SECONDS = int(os.environ.get("LEADENGINE_JWT_TTL", str(86400 * 7)))

# Export safety limits
EXPORT_MAX_ROWS = int(os.environ.get("LEADENGINE_EXPORT_MAX_ROWS", "10000"))
SEARCH_MAX_LIMIT = int(os.environ.get("LEADENGINE_SEARCH_MAX_LIMIT", "200"))
SEARCH_DEFAULT_LIMIT = int(os.environ.get("LEADENGINE_SEARCH_DEFAULT_LIMIT", "25"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
