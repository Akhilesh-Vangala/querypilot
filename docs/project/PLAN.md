# October15 product workspace verification

Implemented and locally verified QueryPilot product landing, guided own-data source/rules/results, real observed stages, explicit immutable device projects/history, backup restore and signed saved-report checks. 159 native backend tests; the original claims/comparison browser journey; 11 grouped product checks and 14 axe views pass. Both actual owner-RLS/concurrent quota checks pass in disposable PostgreSQL. Recordings use current source and real browser pixels. Publication must use protected required CI and exact-source deployment verification; these local checks do not establish hosted Auth, live-model quality, real users or monitored durable operations. See [product implementation](../product/PRODUCT-WORKSPACE.md). Existing release gates and history below remain applicable.

# QueryPilot delivery gates

## Repository organization increment — October 15, 2026

- [x] Inspect clean source boundaries and preserve original history/data.
- [x] Separate backend, frontend, browser checks, operations and project documentation.
- [x] Update runtime, test, dependency and deployment path references.
- [x] Run native regression suites and capture actual browser demonstrations.
Publication gates: pass all required checks on the exact PR head; merge through protected main; verify deployed routes, workflows, player and recording bytes after promotion. The merged PR and current workflow provide the observed status.

Required publication results are recorded in [progress](PROGRESS.md) and the merged PR. The current workflow badge links to the latest checks; a pending result is not a pass.

## Subsequent product gates

- Live-model regression and independent held-out/safety evaluation.
- Measured quality, cost and latency comparisons; actual operator feedback.
- Individual/tenant identity and scoped real integrations.
- Monitored persistent cloud operation, isolation, restore and load/SLO evidence.

A working public synthetic app does not complete these customer/live-model gates. [Previous detailed plans](history/PRE-ORGANIZATION-PLAN.md) remain historical context.
