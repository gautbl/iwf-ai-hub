---
name: sovereign-ai
description: Data sovereignty guardrails - use before proposing any new dependency or service
---

## Hard prohibitions
- Managed cloud data services: BigQuery, SageMaker, Bedrock, Redshift
- Remote LLM APIs: OpenAI, Anthropic, Google, Mistral
- Remote embedding APIs
- SaaS observability shipping data outside managed infrastructure

## Approved alternatives
| Need            | Approved choice            |
|-----------------|----------------------------|
| LLM             | Ollama local               |
| Embeddings      | Ollama local               |
| SQL + vectors   | DuckDB + VSS               |
| Orchestration   | Airflow                    |
| Transformation  | dbt-duckdb                 |
| Observability   | Prometheus + Grafana       |
| Packaging       | Helm                       |

## Audit procedure
Before adding any dependency:
1. Does it transmit data outside the cluster? -> reject
2. Does it require an external account or API key? -> reject
3. Is it open source and self-hostable? -> approve