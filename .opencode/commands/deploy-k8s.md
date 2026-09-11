---
description: Prepare or verify a Kubernetes deployment
---

Load the k8s-manifests skill.
Use the k8s-ops agent to: $ARGUMENTS

Before proposing any kubectl command:
1. Verify parity between k8s/*.yaml and helm/iwf-ai-hub/templates/
2. Flag resources missing a Helm equivalent
3. Note that .gitlab-ci.yml does not exist yet and propose creating it if relevant