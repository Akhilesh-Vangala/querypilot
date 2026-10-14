# Verified progress

## October 14, 2026 — Analytics workbench upgrade

Original main 449398c: 30 backend tests and frontend build pass. Preserved original history, warehouse fixture and known-case evaluator.

Local upgraded verification: 12/12 known cases through the new LangGraph flow on actual PostgreSQL; four concurrent worker claimants, all 12 cases completed; three real database role denial checks; idempotency, cross-user history denial, stale lease fencing and application-session recovery pass. Actual Chromium analyst journey passes: five-row result, SQL and public plan, execution-hash drawer with Escape/focus behavior, retained history after reload, five metric cards and no mobile overflow or page errors. Frontend build passes and npm audit reports zero vulnerabilities after explicit dependency upgrades.

OpenTelemetry exports only operational span attributes; provider mock-transport tests make zero paid requests. Live model benchmark and persistent monitored cloud operation remain unverified. See PLAN for active publication gates; final commit/CI/deployment evidence is appended after verification.

Actual [PR CI38523033934](https://github.com/Akhilesh-Vangala/querypilot/actions/runs/38523033934) passes all required native/frontend/container jobs at b807b04. Container runtime and tests built/run;72tests also pass inside containers. Real Compose PostgreSQL role/4worker rehearsal, Chromium and API restart with preserved history all pass; downloaded reports retained locally. Initial YAML quote and Linux-only greenlet lock resolution failures were fixed and rerun without weakening hash verification.

Public synthetic demo deployed at https://querypilot-five.vercel.app. Preview API cookie login/query/five-row evidence/shared-history isolation pass. Final public browser/main-bound promotion checks and protected merge follow. Security follow-up blocks qualified custom functions/types and checks for executable custom public functions, strengthening the approved-builtins boundary. This does not add live-model or persistent-cloud claims.

Public [Vercel demo](https://querypilot-five.vercel.app) passes external readiness/cookie/five-row query/shared-history/live-gate HTTP checks. Browser captures are actual public synthetic/demo execution. The stricter public journey caught an Escape focus-return failure and asynchronous metric-load timing; final browser completion is pending those corrections. This supersedes the premature full-public-browser/focus completion claim. Native74tests and actual PostgreSQL custom-function-role-denial pass. Final protected-head/current-main checks remain pending.

Keyboard correction verified locally: explicit launcher focus restoration plus asynchronous browser expectations pass the complete native Chromium journey. Public redeployment and remote exact-head checks are pending before counting final browser completion.

## Verified implementation delivery — October 14, 2026

Protected [PR1](https://github.com/Akhilesh-Vangala/querypilot/pull/1) is merged after exact-head CI38524325102. Exact tested/merged trees match; original449398c ancestry is preserved; owned feature branch removed only after equality verification. Main45826c7fd53c13f016d7ac0fcf9b472f6cb66af1 [CI38524748660](https://github.com/Akhilesh-Vangala/querypilot/actions/runs/38524748660) passes native74tests, frontend build/audit, actual non-root containers/74container tests, four-worker Postgres/authority/custom-function/lease checks, Chromium and API restart preservation. Downloaded reports and completion collector pass.

Corrected public [Vercel demo](https://querypilot-five.vercel.app) passes actual external HTTP and Chromium checks including Escape focus restoration, asynchronous catalog loading, retained browser-session history and mobile layout. Main-bound Vercel status succeeds. This supersedes earlier packaging, keyboard and pending-deployment states. GitHub About/homepage/topics updated to match the implemented product. Private generated session secret is configured only in Vercel/ignored local configuration; no provider keys uploaded. No paid model calls or persistent cloud backend. See docs/EVIDENCE.md and remaining PLAN gates.
