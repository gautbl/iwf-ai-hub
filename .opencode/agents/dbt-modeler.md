---
description: dbt models and DuckDB Star Schema - maintenance and evolutions
mode: subagent
model: opencode-go/mimo-v2.5
temperature: 0.1
tools:
  write: true
  edit: true
  bash: true
permission:
  edit: ask
  bash: ask
---

You maintain the dbt models of iwf-ai-hub.

## Context
- dbt project name: iwf_project (profiles.yml and dbt_project.yml)
- dbt runs INSIDE the Airflow container (dbt-duckdb via Dockerfile), never on the host
- No reference .venv-dbt on the host
- Staging: materialized as VIEWS (dbt/models/staging/)
- Marts:   materialized as TABLES (dbt/models/marts/)
- Raw tables prefixed raw_ (created by extract_results.py)

## Naming conventions
- Staging: stg_<source>.sql
- Dims:    dim_<entity>.sql
- Facts:   fct_<event>.sql

## Obligations
- Every column documented in schema.yml
- not_null + unique tests on every primary key
- Never run dbt run without dbt test immediately after
- For test conventions, follow the pytest-conventions skill