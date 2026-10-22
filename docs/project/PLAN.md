## Current scoped increment — October21 pre-live contracts

See [current implementation status](STATUS.md) for this increment, its evidence boundaries and remaining gates. Earlier dated entries below are preserved history.

## October21 — no-credit reliability and availability

Public SSE delivery now retains terminal results/errors separately from a bounded progress mailbox, coalesces cross-thread wakeups and ends with actionable failure after 25 seconds. Slow/disconnected consumers do not receive late reports. Tests inject progress floods, worker faults, deadline expiry and disconnects; a running read-only thread may finish and is not claimed killed.

Agent boundary corrections are verified without model requests: VerifyOps rejects missing/partial usage in both controllers and marks incomplete receipt accounting unknown; RelayOps rejects malformed usage, non-finite/negative elapsed time and invalid tool names; QueryPilot rejects duplicate/non-finite/oversized/nontext model JSON and preserves complete valid tool transcripts. These are protocol reliability tests, not model quality measurements.

A credential-free public monitor checks five real upload formats, exact domain results, SSE progress, report authenticity/tamper rejection, rejection boundaries, current script delivery and recorded-video ranges. Required import/browser CI executes the actual monitor against its isolated local app. A separate twice-hourly canonical workflow retains bounded evidence. [Availability, schedule limitations and recovery](../operations/AVAILABILITY.md). Keep the last ready Vercel deployment serving while previews and protected CI run. Current publication results must be observed and recorded; older dated histories remain preserved.

Remaining gates: genuine private provider credentials/budget, live held-out/cost/latency benchmarks, configured hosted identity, durable isolated monitored tenant operation and actual-user feedback. No public provider enablement, external business writes, new cloud services or paid model calls.

# October16 — bounded multi-format import

The product accepts CSV, TSV, Excel .xlsx, JSON and JSONL, with explicit worksheet selection, deterministic normalization and unchanged domain rules. New parser/domain equivalence and actual five-format browser journeys are part of required CI. [Import contract](../product/FILE-IMPORTS.md). Publication status must be verified through the protected PR and canonical source metadata; live inference, hosted Auth and monitored durable customer execution remain separate gates. Previous release notes below are preserved.

# October15 product workspace verification

Implemented and locally verified QueryPilot product landing, guided own-data source/rules/results, real observed stages, explicit immutable device projects/history, backup restore and signed saved-report checks. 160 native backend tests; the original claims/comparison browser journey; 11 grouped product checks and 14 axe views pass. Both actual owner-RLS/concurrent quota checks pass in disposable PostgreSQL. Recordings use current source and real browser pixels. Publication must use protected required CI and exact-source deployment verification; these local checks do not establish hosted Auth, live-model quality, real users or monitored durable operations. See [product implementation](../product/PRODUCT-WORKSPACE.md). Existing release gates and history below remain applicable.

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
