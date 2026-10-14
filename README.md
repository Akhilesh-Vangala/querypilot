<p align="center"><img src="docs/assets/hero.svg" alt="QueryPilot — analytical questions, executed evidence" width="100%" /></p>

<p align="center">
<a href="https://github.com/Akhilesh-Vangala/querypilot/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/Akhilesh-Vangala/querypilot/actions/workflows/ci.yml/badge.svg" /></a>
<img alt="Python 3.13" src="https://img.shields.io/badge/Python-3.13-222?logo=python&amp;logoColor=white" />
<img alt="LangGraph" src="https://img.shields.io/badge/Agent-LangGraph-222" />
<img alt="PostgreSQL" src="https://img.shields.io/badge/Authority-PostgreSQL-222?logo=postgresql&amp;logoColor=white" />
<a href="LICENSE"><img alt="MIT" src="https://img.shields.io/badge/License-MIT-222" /></a>
</p>

**An agentic analytics workbench for claims and provider-network operations.** Investigate a metric, compare periods with executable definitions, reconcile the change, and retain the SQL and evidence behind the result.

**[Open the live synthetic demo](https://querypilot-five.vercel.app) · [Verified delivery](docs/EVIDENCE.md) · [Architecture](docs/ARCHITECTURE.md) · [Evaluation](docs/EVALUATION.md) · [Deployment](docs/DEPLOYMENT.md) · [Tradeoffs](docs/DECISIONS.md) · [Progress](PROGRESS.md)**

## The business problem

Claims spend, declined referrals, provider capacity and coordination costs have different grains and denominators. A plausible query can double-count spend or average the wrong rate. Analysts need a faster route to an answer with inspectable metric assumptions, SQL, completeness and evidence. QueryPilot supplies that workflow over an explicitly synthetic healthcare operations warehouse.

<details>
<summary>Explore the original analytical investigation</summary>

<img src="docs/assets/investigation.png" alt="Actual QueryPilot investigation showing specialty results, SQL and plan tabs, public workflow events and execution provenance. Synthetic data, deterministic investigator." width="100%" />

*Actual application capture. Guided deterministic investigator; no live model request or customer data.*

</details>

## Investigate what changed

**“What explains the change in claims paid between Q1 and Q2 2026?”**

The new **Compare periods** workspace compiles reviewed metric semantics into SQL, executes both periods in one snapshot, reconciles separate totals and segment aggregates, and produces descriptive volume/mix/unit-cost accounting for claims spend. Weighted-rate contributions use the correct overall denominator. Missing coverage, invalid data or undefined denominators withhold the conclusion.

<img src="docs/assets/comparison.png" alt="Actual synthetic QueryPilot period comparison with reconciled specialty contributions and three-factor claims change accounting. Guided compiler, no live model calls." width="100%" />

Five metric families · ten supported metric/dimension combinations · explicit calendar windows · deterministic verification · downloadable evidence with offline recheck. [Technical design and limits](docs/SEMANTIC-INVESTIGATIONS.md).

```mermaid
flowchart LR
  A[Model-selected typed scope] --> B[Compile approved metric]
  B --> C[Execute one read-only statement]
  C --> D[Reconcile totals and weighted contributions]
  D --> E{Checks pass?}
  E -->|yes| F[Descriptive change report and evidence]
  E -->|no| G[Withhold conclusion and request review]
```

Guided mode selects a deterministic template; a privately configured live investigator uses the same strict tool. Accounting never establishes causality. The public demo does not make live model calls.

## What is engineered here

| Layer | Owned behavior |
| --- | --- |
| Applied AI | Five reviewed metrics compile compatible dimensions, exact filters, calendar windows and weighted denominators into executable comparison SQL. |
| Agentic workflow | LangGraph coordinates typed actions, schema inspection, public planning, bounded correction and a compile → execute → reconcile → report subgraph. |
| Native generation | Official OpenAI Responses SDK, strict function schemas, native call-ID/function-result history, local Pydantic validation, context/token/round limits and no automatic paid replay. |
| Query authority | SQLGlot AST/scope checks, reviewed relation/function allowlists, raw fact fan-out rejection and separate SELECT-only PostgreSQL credentials. |
| Bounded execution | Independent read-only transaction, statement timeout and row/column/byte budgets. Displayed numeric summaries derive from executed rows. |
| Durable coordination | PostgreSQL admission, idempotency, four-worker rehearsal, user-scoped history, leases and owner-fenced publication. Interrupted work requires explicit resubmission. |
| Product | Monochrome overview, investigation composer, persistent detail routes, result/SQL/plan/verification tabs, period comparison page, contribution and factor reports, provenance dialog, offline-checkable export, searchable history, metric catalog and warehouse explorer. |
| Operations | Non-root API/worker/frontend images, one-shot migration/role bootstrap, Compose, health checks, privacy-conscious OTLP spans and actual container/browser/restart CI. |

```mermaid
flowchart LR
  Q[Business question] --> P[Metric contract + public plan]
  P --> A[Bounded LangGraph investigator]
  A --> S[AST policy + read-only database role]
  S --> E[Execute exact query]
  E --> R[Rows + completeness + hashed receipt]
  R --> U[Inspectable analyst result]
  A -. bounded corrective feedback .-> A
```

**Policy remains application-owned.** The model proposes queries; it cannot grant itself tables/tools, write warehouse data or read application identities. Successful query execution is evidence of execution, not a proof of arbitrary business semantics or causality.

## Run it

```sh
git clone https://github.com/Akhilesh-Vangala/querypilot.git
cd querypilot
docker compose up --build -d --wait db api worker frontend
```

Open **http://localhost:3007**. Select the analyst or evaluation demo. These known accounts and Compose passwords are for isolated synthetic development only. A separate worker processes investigations; PostgreSQL preserves their history across API restarts. Private production uses separate secrets/accounts and disables every demo/startup flag; see [deployment](docs/DEPLOYMENT.md).

For native Python 3.13 development, install hashed dependencies from `backend/requirements-dev.txt`, copy `.env.example` to ignored `.env`, create `.tools/`, run `uvicorn app.main:app --app-dir backend --port 8007`, then `npm ci && npm run dev` in `frontend/`.

### Choose the investigator explicitly

- **Guided baseline:** deterministic compiler for known development intents; no model cost.
- **Live model:** private `OPENAI_API_KEY`, `ALLOW_LIVE_AI=true`, and explicit live selection. Default model is `gpt-4o-mini`; provider calls use the official SDK. No key is required to reproduce the engineering checks.
- **Public Vercel demo:** forced synthetic guided mode, actual guarded SQL within the request, browser-session history. It is separate from the persistent PostgreSQL runtime; no durable serverless filesystem or background worker claim.

## Evidence, honestly scoped

| Check | Recorded local result |
| --- | --- |
| Original baseline | 30 backend tests passed before changes |
| Expanded policy/workflow/SDK/API suite | 137 tests passed locally; mocked transport, no paid calls |
| New graph on real PostgreSQL | 12/12 known development cases match independent gold results |
| Compiled comparisons on PostgreSQL | 10/10 reviewed cases across five metric families match independent quarterly SQL |
| Concurrent workers | Four claimants complete two admission-bounded batches: 12 legacy + 10 compiled comparisons; idempotency and stale-owner fencing pass |
| Independent database authority | Reader cannot read app identities or write warehouse; app role cannot read facts |
| Actual Chromium journey | Result/SQL/plan/modal/reload, comparison/contributions/verification/download/offline recheck, future-period withholding and mobile checks |
| Frontend dependency audit | Zero reported vulnerabilities after explicit upgrades |
| Live held-out AI quality | **Not run** |
| Persistent monitored cloud execution | **Not deployed** |

```sh
python -m pytest -q backend/tests
docker compose --profile test run --build --rm tests
python scripts/browser_smoke.py
python scripts/benchmark.py --mode baseline --suite regression --case-limit 12
python scripts/comparison_benchmark.py --mode baseline
python scripts/verify_report.py path/to/querypilot-run.json
```

The benchmark runner also defines **34 separate filtered/safety cases** and records execution accuracy, model usage, attempts, rounds, latency and source hashes. A live evaluation requires an explicit paid opt-in; no deterministic fallback or invented model score. See [evaluation design and limits](docs/EVALUATION.md).

## System boundaries and next release gates

The warehouse contains 80 weekly synthetic snapshots from January 6, 2025, two regions, three employer groups and five specialties. Original data/history are preserved. Monetary fixture fields remain floating point; the legacy last-12-month question uses 52 latest weekly snapshots.

Current limits: live-model quality is unverified; exploratory SQL has safety/execution checks; compiled comparisons bind reviewed semantics but do not prove model-selected intent or source completeness; inner graph state is not checkpointed; interrupted generation is not automatically resumed; user-owned investigations share one organization warehouse; OIDC/tenant data access, global dollar budgets, managed schema migrations, backup restore, load/SLO evidence and actual analyst feedback remain customer-release gates. Do not treat the public demo as a customer-production certification.

## Repository map

```text
backend/app/agent/   graph · strict actions · metrics · SDK · SQL policy
backend/app/         API · auth · run queue · worker · bootstrap · telemetry
backend/tests/      preserved regression + adversarial/workflow/transport checks
frontend/src/       React product pages, tables/charts and provenance interface
scripts/            PostgreSQL rehearsal · browser/restart smoke · benchmarks
docs/               architecture · tradeoffs · evaluation · deployment · actual captures
.github/            reproducible CI · dependency updates · review workflow
```

[Branch policy](BRANCHING.md): short-lived work branches → required backend/frontend/container checks → protected squash merge to main. Preserve original history. MIT; see [LICENSE](LICENSE).
