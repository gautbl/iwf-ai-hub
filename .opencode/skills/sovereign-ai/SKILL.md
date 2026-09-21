---
name: sovereign-ai
description: Data sovereignty guardrails - use before proposing any new dependency or service
---

## Hard prohibitions
- Managed cloud data services: BigQuery, SageMaker, Bedrock, Redshift
- Managed cloud storage/compute: AWS S3, AWS Lambda, CloudWatch
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
| Object storage  | MinIO (S3-compatible, self-hosted, boto3 via endpoint_url) |
| Distributed processing | PySpark (local: Docker pyspark-notebook, or dedicated .venv-spark with host JDK) |
| Observability   | Prometheus + Grafana       |
| Packaging       | Helm                       |

## Audit procedure
Before adding any dependency:
1. Does it transmit data outside the cluster? -> reject
2. Does it require an external account or API key? -> reject
3. Is it open source and self-hostable? -> approve