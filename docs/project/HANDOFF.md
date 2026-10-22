## Current scoped increment — October21 pre-live contracts

See [current implementation status](STATUS.md) for this increment, its evidence boundaries and remaining gates. Earlier dated entries below are preserved history.

## October21 — no-credit reliability and availability

Public SSE delivery now retains terminal results/errors separately from a bounded progress mailbox, coalesces cross-thread wakeups and ends with actionable failure after 25 seconds. Slow/disconnected consumers do not receive late reports. Tests inject progress floods, worker faults, deadline expiry and disconnects; a running read-only thread may finish and is not claimed killed.

Agent boundary corrections are verified without model requests: VerifyOps rejects missing/partial usage in both controllers and marks incomplete receipt accounting unknown; RelayOps rejects malformed usage, non-finite/negative elapsed time and invalid tool names; QueryPilot rejects duplicate/non-finite/oversized/nontext model JSON and preserves complete valid tool transcripts. These are protocol reliability tests, not model quality measurements.

A credential-free public monitor checks five real upload formats, exact domain results, SSE progress, report authenticity/tamper rejection, rejection boundaries, current script delivery and recorded-video ranges. Required import/browser CI executes the actual monitor against its isolated local app. A separate twice-hourly canonical workflow retains bounded evidence. [Availability, schedule limitations and recovery](../operations/AVAILABILITY.md). Keep the last ready Vercel deployment serving while previews and protected CI run. Current publication results must be observed and recorded; older dated histories remain preserved.

Remaining gates: genuine private provider credentials/budget, live held-out/cost/latency benchmarks, configured hosted identity, durable isolated monitored tenant operation and actual-user feedback. No public provider enablement, external business writes, new cloud services or paid model calls.

# October16 — bounded multi-format import

The product accepts CSV, TSV, Excel .xlsx, JSON and JSONL, with explicit worksheet selection, deterministic normalization and unchanged domain rules. New parser/domain equivalence and actual five-format browser journeys are part of required CI. [Import contract](../product/FILE-IMPORTS.md). Publication status must be verified through the protected PR and canonical source metadata; live inference, hosted Auth and monitored durable customer execution remain separate gates. Previous release notes below are preserved.

# Active: complete own-data product workspace

QueryPilot now has domain-specific landing/workspace, source/rule review, real streamed execution, results/evidence, consented immutable device projects/history and portable restore. Overall average is weighted from the underlying included records; exact decimal strings remain inspectable. Optional account adapter/RLS is prepared and locally tested; genuine hosted authentication is not configured. Protected CI, source-bound deployment and media checks must pass before release is marked delivered. See [product documentation](../product/PRODUCT-WORKSPACE.md).

# Prior increment: visitor-owned CSV workspaces (superseded by product workspace)

Implementation adds `/uploads`, bounded own-data APIs, exact mapping/contracts, source-derived independently reconciled outputs and evidence exports. RelayOps retains exact-source human approval before export. Local verification: 145 tests passed, actual file-picker/checked-result/download/mobile/Clear/invalid-file browser journeys, plus refreshed original sample recordings. Protected CI and deployment checks are required before production promotion. Existing release-gate limitations remain. See [contracts](../product/USER-DATA.md).

# QueryPilot current handoff

Updated October 15, 2026. Start with the [README](../../README.md), [layout](../development/LAYOUT.md), [plan](PLAN.md) and [progress](PROGRESS.md).

React and FastAPI connect authenticated admission to separate PostgreSQL workers. A bounded LangGraph controller uses typed native SDK actions and an independent read-only warehouse connection. The comparison subgraph compiles reviewed semantics, executes one statement, reconciles weighted contributions and produces inspectable evidence.

Public app: https://querypilot-five.vercel.app. Recording: https://querypilot-five.vercel.app/recordings/. Synthetic claims/network data and a guided investigator execute guarded SQL within the HTTP request. Compare periods across five reviewed metric families, inspect contributions and fifteen checks, export evidence for offline recomputation, and withhold unsupported future-period conclusions. Both mode and dataset scope must stay visible. No live-model quality, customer feedback or monitored persistent cloud claim is established.

The `refactor/component-structure` increment groups modules/tests by capability, moves versioned data/dbt under backend, separates native frontend scripts/styles/media, consolidates infrastructure/tooling and refreshes actual source-bound recordings. Native suites pass 137cases; actual Linux/container/deployment conclusions belong to required CI and source-linked publication records, not prepared files. Publish only through the [protected branch workflow](../development/BRANCHING.md).

Keep data and ignored `.env`/runtime state unchanged. Do not copy provider keys between projects. The public entrypoint disables live model credentials. Interrupted model work requires explicit resubmission; the inner graph is not checkpointed.

Prior implementation and deployment narratives are retained in [dated handoff history](history/PRE-ORGANIZATION-HANDOFF.md). Current instructions and repository paths take precedence.
