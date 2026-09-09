---
name: medallion-arch
description: Bronze/Silver/Gold medallion architecture as applied to iwf-ai-hub
---

## Layers
- **Bronze**: raw data, raw_* tables (extract_results.py)
- **Silver**: cleaning and typing, staging/stg_*.sql models (dbt views)
- **Gold**:   BI-ready Star Schema, marts/ models (dbt tables)

## Rules
- Never write directly to Silver or Gold from Python
- Every transformation goes through dbt
- Staging models only type and rename, never aggregate
- Facts hold metrics, dims hold attributes

## DuckDB / dbt lineage
- raw_ow_event_117 -> stg_results        -> fct_results
- raw_ow_event_117 -> stg_results        -> dim_athletes
- raw_ow_event_117 -> stg_results        -> dim_weight_classes