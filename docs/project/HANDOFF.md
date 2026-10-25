# QueryPilot implementation handoff

[Technical report](../TECHNICAL-REPORT.md) · [Architecture](../architecture/OVERVIEW.md) · [Layout](../development/LAYOUT.md)

React owns the evidence studio, file workspace, investigation and comparison views. FastAPI owns input validation, identity, SQL authority, deterministic reconciliation and report authentication. LangGraph owns orchestration inside that authority. Private execution uses separate PostgreSQL workers; the Vercel public workflow executes reviewed files and a guided synthetic investigator in-request.

Read [branching](../development/BRANCHING.md) before tracked changes. Keep runtime files, ignored configuration and private datasets unchanged. Never copy provider credentials between projects. Public mode disables model credentials. Rebuild the frontend and refresh both actual source-bound recordings after application changes.

[Current execution evidence](../evaluation/EVIDENCE.md) is the review record. Dated implementation narratives are preserved under `history/`.
