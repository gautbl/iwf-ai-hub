---
description: Audit all agent/subagent models against cost and privacy rules
agent: iwf-lead
---

Re-evaluate the model assigned to every agent and subagent. The objective is to obtain the best performance/cost ratio and not risking to go over the monthly limit of the Opencode Go plan. The model has to be adapted to the agent's tasks. The agent .md files are in .opencode/agents. The models in the files are in the parameter "model".

1. Load the current OpenCode Go usage/privacy data (check URL https://opencode.ai/docs/fr/go/). If you cannot access the URL, don't go further and stop the task immediatly.
2. For each agent: list model, monthly $ limit, retention, training policy.
3. FLAG and reject any model that is not 0-day retention / no-training
   (forbidden: Grok 4.6, GPT 5.6 Luna, Muse Spark Contributor).
4. Recompute performance/cost ratio; propose cheaper substitutes at equal quality.
5. Watch the $15/month-limit models (Kimi K3, GLM-5.3): confirm they are only
   used for rare, hard tasks, not high-volume work.
6. Estimate usage vs the $12/5h, $30/week, $60/month caps, per model.
7. Output a diff table: current model -> recommended model, with reason.

Note: DeepSeek's ZDR agreement renews monthly (valid to 30/09/2026). Run monthly.
Consider Deepseek models in the possible choices as long as they meet the criteria.