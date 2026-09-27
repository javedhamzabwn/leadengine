"""Prepare data and stats for benchmark queries"""
import duckdb
import json

con = duckdb.connect()

# Fresh Apollo people schema
schema = con.execute("DESCRIBE SELECT * FROM 'D:/wsl-data/Fresh Apollo Leads 1,232,352/_formated/data_1.parquet'").fetchall()
print("=== Fresh Apollo schema ===")
for row in schema[:25]:
    print(row)
print(f"Total: {len(schema)} cols")

# Count Fresh Apollo
cnt = con.execute("SELECT count(*) FROM 'D:/wsl-data/Fresh Apollo Leads 1,232,352/_formated/data_1.parquet'").fetchone()
print(f"Fresh Apollo rows: {cnt[0]}")

# Combined people
cnt_p = con.execute("SELECT count(*) FROM read_parquet(['D:/wsl-data/Apollo Software Development Leads 111,582/Softwaredevelopment Apollo 111,582/100k leads Cleaned/data_*.parquet', 'D:/wsl-data/Fresh Apollo Leads 1,232,352/_formated/data_*.parquet'])").fetchone()
print(f"Total people rows: {cnt_p[0]}")

# Crunchbase count
cnt_c = con.execute("SELECT count(*) FROM read_parquet(['D:/wsl-data/Almost Full Crunchbase Database 2,807,492/crunchbase_companies/data_*.parquet'])").fetchone()
print(f"Crunchbase rows: {cnt_c[0]}")

# All datasets full scan
cnt_all = con.execute("SELECT count(*) FROM 'D:/wsl-data/Entire Apollo Database 99,311,285/data_1.parquet'").fetchone()
print(f"Full Apollo DB: {cnt_all[0]}")

# Revenue stats (that aren't dirty)
print("\n=== Clean numerical data check ===")
clean = con.execute("""
    SELECT count(*) as total,
           count(CASE WHEN try_cast(organization_total_funding_long AS BIGINT) IS NOT NULL 
                AND organization_total_funding_long ~ '^[0-9]+$' THEN 1 END) as clean_rev
    FROM 'D:/wsl-data/Entire Apollo Database 99,311,285/data_1.parquet'
""").fetchone()
print(f"Total: {clean[0]}, Clean revenue: {clean[1]}")

# Industry frequencies 
inds = con.execute("""
    SELECT organization_industries, count(*) as cnt
    FROM 'D:/wsl-data/Entire Apollo Database 99,311,285/data_1.parquet'
    WHERE organization_industries IS NOT NULL AND organization_industries != '[]'
    GROUP BY organization_industries
    ORDER BY cnt DESC
    LIMIT 15
""").fetchall()
print("\n=== Top industries ===")
for r in inds:
    print(r)