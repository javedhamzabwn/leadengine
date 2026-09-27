import os
import duckdb
from contextlib import contextmanager

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PARQUET_PATH = os.path.join(PROJECT_ROOT, "..", "Entire Apollo Database 99,311,285", "data_1.parquet")
DB_PATH = os.path.join(PROJECT_ROOT, "leadengine.db")

@contextmanager
def get_connection():
    """Provide a transactional scope around a series of operations."""
    # Create database if it doesn't exist (DuckDB creates on first connect)
    conn = duckdb.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """Initialize the database with required views over Parquet data."""
    with get_connection() as conn:
        # Create a view that extracts lead-relevant fields from the parquet
        # The parquet has organization records + people_v7 person records
        conn.execute(f"""
            CREATE OR REPLACE VIEW leads_view AS
            SELECT
                p.id AS lead_id,
                p.person AS full_name,
                NULL AS current_title,
                NULL AS current_company,
                NULL AS department,
                NULL AS seniority,
                p.organization_hq_location_city AS location,
                NULL AS industry,
                p.organization_phone AS phone,
                NULL AS email,
                NULL AS linkedin_url,
                NULL AS source,
                NULL AS created_at,
                NULL AS updated_at
            FROM read_parquet('{PARQUET_PATH}') AS o
            CROSS JOIN LATERAL (
                SELECT
                    person_id AS id,
                    person_name AS person,
                    job_functions,
                    organization_hq_location_city,
                    organization_phone
                FROM UNNEST(o.people_v7) AS t(person_id, person, job_functions, organization_hq_location_city, organization_phone)
            ) AS p
        """)
        
        # Create organizations view
        conn.execute(f"""
            CREATE OR REPLACE VIEW organizations_view AS
            SELECT
                organization_id AS org_id,
                organization_name AS name,
                organization_industries AS industries,
                organization_hq_location_city AS hq_city,
                organization_phone AS phone,
                organization_revenue_in_thousands_int AS revenue
            FROM read_parquet('{PARQUET_PATH}')
        """)
        
        # Verification
        lead_count = conn.execute("SELECT COUNT(*) FROM leads_view").fetchone()[0]
        org_count = conn.execute("SELECT COUNT(*) FROM organizations_view").fetchone()[0]
        print(f"Database initialized:")
        print(f"  Leads view: {lead_count} records")
        print(f"  Organizations view: {org_count} records")
        
        sample = conn.execute("SELECT * FROM leads_view LIMIT 1").fetchone()
        if sample:
            print(f"  Sample lead: {sample}")
        
        return True

def search_leads(filters=None, limit=50, offset=0):
    """Search leads with parameterized filters."""
    if filters is None:
        filters = {}
    
    base_query = """SELECT * FROM leads_view WHERE 1=1"""
    params = []
    
    if filters:
        if filters.get('keyword'):
            base_query += " AND (full_name ILIKE ? OR job_functions ILIKE ?)"
            k = f"%{filters['keyword']}%"
            params.extend([k, k])
        if filters.get('location'):
            base_query += " AND location ILIKE ?"
            l = f"%{filters['location']}%"
            params.append(l)
    
    base_query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    with get_connection() as conn:
        result = conn.execute(base_query, params).fetchall()
        columns = [desc[0] for desc in conn.description] if conn.description else []
        return [dict(zip(columns, row)) for row in result]

def get_lead(lead_id):
    """Retrieve a single lead by ID."""
    with get_connection() as conn:
        result = conn.execute(
            "SELECT * FROM leads_view WHERE lead_id = ?", 
            [lead_id]
        ).fetchone()
        if result:
            columns = [desc[0] for desc in conn.description] if conn.description else []
            return dict(zip(columns, result))
    return None

__all__ = ['get_connection', 'init_database', 'search_leads', 'get_lead']
