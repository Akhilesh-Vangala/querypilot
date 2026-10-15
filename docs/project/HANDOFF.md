# QueryPilot current handoff

Updated October 15, 2026. Start with the [README](../../README.md), [layout](../development/LAYOUT.md), [plan](PLAN.md) and [progress](PROGRESS.md).

React and FastAPI connect authenticated admission to separate PostgreSQL workers. A bounded LangGraph controller uses typed native SDK actions and an independent read-only warehouse connection. The comparison subgraph compiles reviewed semantics, executes one statement, reconciles weighted contributions and produces inspectable evidence.

Public app: https://querypilot-five.vercel.app. Recording: https://querypilot-five.vercel.app/recordings/. Synthetic claims/network data and a guided investigator execute guarded SQL within the HTTP request. Compare periods across five reviewed metric families, inspect contributions and fifteen checks, export evidence for offline recomputation, and withhold unsupported future-period conclusions. Both mode and dataset scope must stay visible. No live-model quality, customer feedback or monitored persistent cloud claim is established.

The `chore/repository-structure` increment moves sources/docs into explicit areas and refreshes actual recordings. Native suites pass 137cases; actual Linux/container/deployment conclusions belong to required CI and source-linked publication records, not prepared files. Publish only through the [protected branch workflow](../../BRANCHING.md).

Keep data and ignored `.env`/runtime state unchanged. Do not copy provider keys between projects. The public entrypoint disables live model credentials. Interrupted model work requires explicit resubmission; the inner graph is not checkpointed.

Prior implementation and deployment narratives are retained in [dated handoff history](history/PRE-ORGANIZATION-HANDOFF.md). Current instructions and repository paths take precedence.
