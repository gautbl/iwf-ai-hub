---
name: k8s-manifests
description: Kubernetes checklist and standards for iwf-ai-hub
---

## Checklist before any manifest
- [ ] Namespace `iwf-ai-hub` declared
- [ ] No `:latest` tag
- [ ] Resource requests and limits set
- [ ] Liveness and readiness probes present
- [ ] Secrets: empty values or references (never real data)
- [ ] Helm equivalent present in helm/iwf-ai-hub/templates/

## DuckDB StatefulSet
- Always with a PersistentVolumeClaim
- Volume mounted at /data/duckdb
- Must match the Docker Compose path: data/duckdb/

## ConfigMap vs Secret
- ConfigMap: ports, URLs, service names (non-sensitive)
- Secret:    credentials, tokens, API keys (empty values in templates)