#!/bin/bash
# LeadEngine Benchmark Suite
# Compares DuckDB vs ClickHouse performance for LeadEngine search queries
# Usage: bash BENCHMARK_SUITE.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "[BENCHMARK] LeadEngine Performance Benchmark Suite"
echo "[BENCHMARK] $(date)"
echo "[BENCHMARK] Project root: $PROJECT_ROOT"
echo ""

# Run the Python benchmark engine
python bench_runner.py 2>&1

echo ""
echo "[BENCHMARK] Done. See benchmarks_report.txt for results."