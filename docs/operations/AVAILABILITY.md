# Public availability and no-credit checks

The canonical application is https://querypilot-five.vercel.app/. Vercel serves the application independently of a local Mac or terminal. Do not stop or remove the existing production deployment to prepare a replacement. Test a preview first, pass the exact-head required CI and protected merge, then verify the promoted source and actual upload/result workflows. Retain the previous ready deployment for an explicit rollback if the replacement fails; do not repeatedly redeploy to conceal a failure.

## Synthetic monitor

[Public application health](../../.github/workflows/public-health.yml) checks the canonical application twice an hour, at minutes 25 and 55 UTC. It can also be dispatched manually. The standard-library [probe](../../scripts/checks/public_health.py) requires no provider key or third-party monitoring account. It exercises the actual home script, declared capabilities, CSV/TSV/XLSX/JSON/JSONL parsing, observed SSE stages, exact domain results, independent checks, report authenticity/tamper rejection, invalid-source rejection, cross-origin rejection and video range delivery. RelayOps additionally exercises explicit approval and four temporary-snapshot receipts. Only tiny original synthetic fixtures are submitted. No customer source, authorization cookies, reports or raw response payloads appear in the retained health summary. Failures exit nonzero and retain a seven-day artifact; GitHub notification delivery depends on the owner's configured notification preferences. No messages or issues are sent automatically.

```sh
python3 scripts/checks/public_health.py
```

The probe has per-request and aggregate deadlines, bounded responses and same-origin redirect checks. It performs no automatic retry that would hide a failed observation. Latencies are individual observations, not an SLA or a historical percentile. A successful monitor does not prove live AI quality, real-user feedback or durable tenant operation.

GitHub schedules can be delayed or dropped during high load and public-repository schedules can be disabled after 60 days of inactivity; scheduled workflows execute from the default branch. These limits come from [GitHub's schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule). This workflow detects sampled failures; it does not guarantee uninterrupted uptime or prevent serverless cold starts. Vercel platform/account limits remain applicable. A dedicated external uptime/SLO service is a separate operational decision.

## Stream recovery

Progress uses a 32-event mailbox with coalesced loop wakeups and an independent terminal slot. A progress burst cannot drop the final result/error. A 25-second response deadline yields an actionable failure rather than an unending heartbeat. Closing the browser or exceeding the deadline suppresses late report delivery/signing when the calculation has not finished. Already-running bounded read-only threads may finish; the application does not claim they were killed. No business-system writes run in this public path.

## Remaining gates

Live model credentials/budget and independent live benchmarks remain needed. Hosted authentication requires a real configured identity service. Durable monitored private workers, tenant isolation under representative load, recovery/restore SLOs and actual user feedback are not established by this public monitor.

## Native model boundary

The Responses API returns function arguments as a JSON string and correlates outputs using call_id; see [official OpenAI function-calling documentation](https://developers.openai.com/api/docs/guides/function-calling). QueryPilot validates the raw argument string before dictionary conversion, preserving duplicate-key detection. Native reasoning/call history stays intact. Missing or invalid usage stops the run and marks billing unknown; reported valid usage remains accounted even if argument validation fails. Actual SDK MockTransport tests exercise these boundaries without a provider request or key. No new model is selected or enabled.
