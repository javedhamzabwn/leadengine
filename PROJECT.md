# LeadEngine Project

## Product
LeadEngine is a web-based B2B lead search platform powered by a large collection of pre-scraped B2B records stored primarily as Apache Parquet files.

## Current Scale
- Overall source inventory: approximately 384M records according to project blueprint.
- Main LinkedIn dataset: approximately 354M rows and about 40 GB.
- Total Parquet footprint discussed in blueprint: approximately 45 GB.
- Smaller source datasets range down to tens of MB.

## Product Goal
Provide fast B2B people/company discovery with:
- structured filters,
- text search,
- profile views,
- facets,
- saved searches,
- lead lists,
- exports,
- enrichment/verification,
- API access,
- subscription/credit monetization,
- provenance and freshness information.

## Current MVP Direction
FastAPI + DuckDB + Parquet + lightweight HTML/Alpine.js frontend.

## Target Production Direction
Next.js/React + FastAPI + ClickHouse + PostgreSQL + Redis + workers + object storage, with Elasticsearch optional if search relevance requires it.

## Core Principle
Raw data is immutable source material. Product-facing data must be normalized, quality-checked, provenance-aware, and searchable.

## Non-Goals
- Do not treat raw scraped data as automatically accurate.
- Do not treat publicly visible information as automatically legal to resell.
- Do not promise fixed sub-second performance before benchmarking.
