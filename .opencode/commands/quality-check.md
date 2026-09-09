---
description: Global quality review of recently modified code
---

1. Run pytest tests/ and report failures
2. Use sql-reviewer on dbt/models/ files changed since the last commit
3. Produce a final verdict: GO (ready for the next phase) or NO-GO
   with the list of blocking items