# Verified progress

## October 14, 2026 — Analytics workbench upgrade

Original main 449398c: 30 backend tests and frontend build pass. Preserved original history, warehouse fixture and known-case evaluator.

Local upgraded verification: 12/12 known cases through the new LangGraph flow on actual PostgreSQL; four concurrent worker claimants, all 12 cases completed; three real database role denial checks; idempotency, cross-user history denial, stale lease fencing and application-session recovery pass. Actual Chromium analyst journey passes: five-row result, SQL and public plan, execution-hash drawer with Escape/focus behavior, retained history after reload, five metric cards and no mobile overflow or page errors. Frontend build passes and npm audit reports zero vulnerabilities after explicit dependency upgrades.

OpenTelemetry exports only operational span attributes; provider mock-transport tests make zero paid requests. Live model benchmark and persistent monitored cloud operation remain unverified. See PLAN for active publication gates; final commit/CI/deployment evidence is appended after verification.

Actual [PR CI38523033934](https://github.com/Akhilesh-Vangala/querypilot/actions/runs/38523033934) passes all required native/frontend/container jobs at b807b04. Container runtime and tests built/run;72tests also pass inside containers. Real Compose PostgreSQL role/4worker rehearsal, Chromium and API restart with preserved history all pass; downloaded reports retained locally. Initial YAML quote and Linux-only greenlet lock resolution failures were fixed and rerun without weakening hash verification.

Public synthetic demo deployed at https://querypilot-five.vercel.app. Preview API cookie login/query/five-row evidence/shared-history isolation pass. Final public browser/main-bound promotion checks and protected merge follow. Security follow-up blocks qualified custom functions/types and checks for executable custom public functions, strengthening the approved-builtins boundary. This does not add live-model or persistent-cloud claims.

Public [Vercel demo](https://querypilot-five.vercel.app) passes external readiness/cookie/five-row query/shared-history/live-gate HTTP checks. Browser captures are actual public synthetic/demo execution. The stricter public journey caught an Escape focus-return failure and asynchronous metric-load timing; final browser completion is pending those corrections. This supersedes the premature full-public-browser/focus completion claim. Native74tests and actual PostgreSQL custom-function-role-denial pass. Final protected-head/current-main checks remain pending.

Keyboard correction verified locally: explicit launcher focus restoration plus asynchronous browser expectations pass the complete native Chromium journey. Public redeployment and remote exact-head checks are pending before counting final browser completion.
