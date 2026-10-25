# QueryPilot product workspace

## Evidence studio interface

The landing page offers two explicit workflows: file analysis and guided warehouse investigation. A persistent indigo rail owns file workspace navigation and links to the separate plum investigation studio. Overview task cards lead to source analysis or period comparison; counts reflect explicitly saved work rather than illustrative activity.

Reports use labelled source/rules/review/result stages, exact-value metric cards, colour-coded positive/negative contributions, source-quality and SQL/check tabs, and a run-provenance strip populated from the signed report. Older reports without run metadata remain readable. Responsive navigation, visible keyboard focus and reduced-motion preferences apply across both surfaces. Colour reinforces text; it never supplies the only verification indicator.

Design implementation: `frontend/src/features/product/studio.css`, `frontend/src/components/layout/StudioIcon.tsx` and the scoped warehouse theme in `frontend/src/styles/index.css`. Continuous demos use the actual built product. The additional `scripts/demos/studio_browser.py` checks both route surfaces, inter-workspace navigation and mobile accessibility.

## Prompt-led warehouse interaction

A question composer on the landing and warehouse overview links to `/new?question=…`. Reviewed starters populate text; the investigator runs only after explicit submission on the question brief. Sign-in retains the intended internal route and query. An allowlist restricts return destinations to known UI routes and rejects external/API/backslash targets.

The brief shows actual configured round/query/row budgets and guided/live availability. Ctrl/Command+Enter submits the same validated form. The execution explorer provides observed sequence numbers, tool and verification filters, selected public JSON, cumulative event timestamps, reported token usage and a link to the published plan. Guided mode remains explicit. Follow-ups reference the previous run while starting independent execution; comparison links preselect supported reviewed metrics.

Mobile query tabs scroll within the viewport. Executed-row tables and selected JSON are keyboard focusable. `scripts/demos/agent_desk_browser.py` checks actual prompt/auth/tool/evidence/follow-up behavior and ten accessible desktop/mobile views.

## Multiple tabular formats — October16

CSV, TSV, Excel .xlsx, JSON and JSONL are accepted through the guided product. [Formats, worksheet selection, exact conversion and limits](FILE-IMPORTS.md). Existing domain contracts and result/approval checks remain applicable; PDFs/images are unsupported. Earlier CSV-specific implementation descriptions below remain historical context for the normalized analysis engine.


The public product offers a real source-to-result journey. The original guided synthetic application remains at `/demo`; its sample datasets and history are separate. [Own-data contract](USER-DATA.md).

## Pages and workflow

`/` is the public landing. `/workspace` starts with actual empty state and reflects only deliberately saved work. `/uploads` guides source, rules, confirmation and execution. `/workspace/projects`, `/workspace/history`, `/workspace/settings`, `/workspace/guide` and `/workspace/login` provide organization, recovery and honest account status. Individual saved snapshots have stable detail URLs.

Source CSV → searchable paginated row/quality preview → choose sum/count/average, measure, grouping and case-sensitive exact filter → explicitly review the definition → observed SQL/reference stages → inspect exact values, group contributions, SQL and independent checks → export evidence.

Contract-driven descriptive analytics over at most 5,000 source records, not natural-language interpretation or arbitrary uploaded SQL. SQL aggregates integer micros/counts and is independently reconciled against Decimal arithmetic. Overall average uses the sum and count of all included records, never the unweighted mean of group averages. Results retain exact decimal strings; chart widths alone are approximate. No implicit duplicate removal, imputation or causal claim. Invalid included numeric cells, excessive groups or an empty filter withhold the result.

## Progress, integrity and recovery

`POST /api/uploads/analyze-stream` publishes actual running/completed callbacks and exactly one terminal result or problem. It supplies no synthetic percentage. Stopping the browser wait does not claim to kill a running bounded read-only thread. Structured errors identify source record/column; selected-record preview can inspect errors beyond the first page. File contents render as text. JSON and CSV exports contain actual source-derived results, with formula-safe text exports.

A purpose-specific HMAC authenticates report contents and their past computation time. Before reopening or restoring a completed snapshot, the browser checks source fingerprint, contract equality and server report authentication. Altered or stale receipts return to review instead of acquiring a verified badge. Receipt authentication is not a current warehouse check or proof that the declared business rules are correct. Stable signing keys must be consistent across deployment instances; rotation deliberately invalidates older receipts.

## Deliberate device storage

Unsaved source and results remain in browser memory and bounded request/temporary processing. Explicit save consent enables IndexedDB projects and immutable source/rule/report snapshots in this browser. Every edited rerun saves a new ID; prior results remain. Atomic writes enforce 20 projects and 50 device snapshots. Browser cleanup may remove local work. Clear active work and delete saved history are separate, confirmed actions. Do not upload unnecessary confidential fields.

Settings exports a portable JSON backup. Restore needs fresh consent, validates the complete bundle, reparses each source and checks completed report receipts before one atomic import. New IDs avoid overwriting existing snapshots. This is manual transfer between browsers/Macs, not automatic cloud synchronization. Backups themselves contain source business data; store them accordingly.

## Optional cloud accounts

Cloud accounts default to an explicit unavailable state. The prepared adapter requires HTTPS `QUERY_SUPABASE_URL` and a genuine publishable/anon `QUERY_SUPABASE_PUBLISHABLE_KEY`; service/admin keys are refused. `QUERY_ACCOUNT_SIGNUP=1` enables self-registration only when intentionally configured. The actual [migration](../../infrastructure/supabase/migrations/001_product_workspace.sql) supplies owner-isolated immutable project/investigation tables, forced RLS, owner-project foreign keys and serialized per-owner quotas. Apply it to the intended provider before enabling the adapter.

Identity is validated server-side with the provider. HttpOnly host/session cookies carry provider sessions; PostgREST receives the user's token rather than an admin credential. Cloud saves need consent; source retention is a separate opt-in. Completed results are recomputed or authenticated by the server, never trusted from a client flag. Source omission requires a matching re-upload to rerun. Signup/email/real hosted login, refresh and backups remain unverified until a real provider is configured and rehearsed.

`QUERY_REPORT_SIGNING_KEY` is the private purpose-specific signing setting (at least 48 characters). A separate stable signing key is required across serverless instances; the JWT access-token key is not reused. Never commit secrets.

## Implementation and validation

Product frontend: `frontend/src/features/product/`. Backend account boundary: `backend/app/product/`. Upload processing stays in `uploads/`. The product reuses this workspace's owned VerifyOps storage/HTTP patterns, with domain-specific frontend and analytical/operational contracts.

- `scripts/demos/product_browser.py`: real Chromium file upload, reviewed rules, exports, device snapshots/reload, tamper denial, backup restore, network recovery, keyboard dialogs/tabs, mobile sizes and optional pinned axe audits. `uploads_browser.py` delegates to this complete journey.
- `backend/tests/api/test_product.py`: provider-verified identity, consent, owner-scoped access and redacted error contracts with a controlled provider transport. These are not hosted-auth proofs.
- `backend/tests/api/test_product_evidence.py`: actual SSE terminal behavior, nested-report tamper/key rotation, precise invalid-cell errors and selected late-record preview. An unequal-group average regression rejects averaging group means.
- `scripts/checks/product_rls.py`: applies the actual migration to its own random disposable PostgreSQL database, exercises two owners, anonymous/spoof/update denial and concurrent quota enforcement, then drops only that owned database. Requires an explicit test administrative URL.

Automated rehearsals are not actual customer feedback or a production reliability certification. These checks establish the exercised software contracts; they do not measure live-model quality or hosted tenant operation. Canonical app: https://querypilot-five.vercel.app/.
