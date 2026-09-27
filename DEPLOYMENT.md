# LeadEngine Deployment Plan

## Local

```text
FastAPI
DuckDB
Parquet
Alpine.js
```

## Early VPS

```text
Reverse proxy
  ↓
FastAPI
  ↓
DuckDB
  ↓
local NVMe Parquet
```

Minimum starting benchmark target:
- 8 vCPU
- 32 GB RAM
- 500 GB NVMe

## Production

```text
CDN/WAF
 ↓
Next.js
 ↓
FastAPI
 ├── PostgreSQL
 ├── Redis
 ├── ClickHouse
 └── Worker queue
        ↓
    Object storage
```

## Object Storage
Use for:
- raw Parquet archive
- ETL input
- backups
- completed exports
- historical snapshots

Avoid remote object storage as the only interactive search layer.

## Backups
- PostgreSQL backups.
- ClickHouse backups/snapshots.
- Raw Parquet versioning.
- Export expiration.
- Restore tests.

## Observability
Track:
- p50/p95/p99 search latency
- database latency
- rows scanned
- cache hit rate
- export duration
- error rate
- CPU/RAM/disk
- queue depth

## Scaling Trigger
Migrate DuckDB to ClickHouse based on measured workload:
- concurrency
- latency
- query volume
- memory pressure
- storage/IO behavior
