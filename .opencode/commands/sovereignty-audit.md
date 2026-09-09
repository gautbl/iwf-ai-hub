---
description: Audit dependencies and code for sovereignty violations
---

Load the sovereign-ai skill.
Scan the project for:
- Remote LLM or embeddings API calls
- Managed cloud service references
- Dependencies that transmit data outside the cluster
Report every finding with file path and line number,
and propose an approved local alternative for each.