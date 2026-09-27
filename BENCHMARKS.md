# LeadEngine Benchmark Plan

## Benchmark Queries

B01 exact domain
B02 country
B03 country + title
B04 country + seniority
B05 title text
B06 fuzzy title
B07 company name
B08 technology
B09 multiple filters
B10 broad query
B11 facets
B12 sorting
B13 profile lookup
B14 export 1K
B15 export 10K

## Concurrency

Run each at:

```text
1
5
10
25
50
100
```

## Record

```text
p50
p95
p99
CPU
RAM
disk IO
rows scanned
rows returned
cache hit/miss
query duration
```

## Compare

```text
DuckDB + Parquet
ClickHouse
optional Elasticsearch
```

## Acceptance
Do not claim "<500ms" globally.

Define separate targets:

```text
autocomplete
simple exact filter
normal search
complex search
facet load
profile
export submission
```

Each target must be benchmark-backed.
