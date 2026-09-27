import duckdb
con = duckdb.connect()
con.execute('PRAGMA threads=4')

# B01 test
sql = "SELECT count(*) FROM read_parquet(['D:/wsl-data/Apollo Software Development Leads 111,582/Softwaredevelopment Apollo 111,582/100k leads Cleaned/data_1.parquet'], union_by_name=true) WHERE Country = 'United States' AND Title LIKE '%Engineer%'"
print(f"SQL: {sql}")
result = con.execute(sql).fetchone()
print(f"Result: {result}")
print("B03 query works!")

# B06 test
sql2 = "SELECT count(*) FROM read_parquet(['D:/wsl-data/Apollo Software Development Leads 111,582/Softwaredevelopment Apollo 111,582/100k leads Cleaned/data_1.parquet'], union_by_name=true) WHERE Title ILIKE '%market%'"
result2 = con.execute(sql2).fetchone()
print(f"B06 result: {result2}")

# B09 test - multiple filters
sql3 = "SELECT count(*) FROM 'D:/wsl-data/Entire Apollo Database 99,311,285/data_1.parquet' WHERE organization_industries LIKE '%information technology%' AND organization_hq_location_country = 'United States'"
result3 = con.execute(sql3).fetchone()
print(f"B09 count: {result3[0]}")

# B10 - broad
sql4 = "SELECT organization_industries, count(*) as cnt FROM 'D:/wsl-data/Entire Apollo Database 99,311,285/data_1.parquet' WHERE organization_industries IS NOT NULL AND organization_industries != '[]' GROUP BY organization_industries ORDER BY cnt DESC LIMIT 5"
result4 = con.execute(sql4).fetchall()
print(f"B10 top industries: {result4}")

# B12 - sorting with try_cast
sql5 = "SELECT count(*) FROM 'D:/wsl-data/Entire Apollo Database 99,311,285/data_1.parquet' WHERE try_cast(organization_total_funding_long AS BIGINT) IS NOT NULL AND organization_total_funding_long ~ '^[0-9]+$'"
result5 = con.execute(sql5).fetchone()
print(f"B12 clean revenue rows: {result5[0]}")

print("\nAll queries verified OK!")