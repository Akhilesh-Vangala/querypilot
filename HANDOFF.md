# QueryPilot handoff

User explicitly authorized improving this existing repository, overriding the earlier no-existing-repository rule only for QueryPilot. Canonical workspace path: projects/applied-ai/querypilot. Original main 449398c is preserved; active work branch feat/verified-analytics-workbench. Read README, BRANCHING, PLAN and docs before continuing.

Implemented: bounded LangGraph/native OpenAI SDK analytics, strict public plans/actions, AST-scoped read-only SQL, reviewed metric catalog, PostgreSQL run queue/separate worker/fenced leases, user-scoped histories/idempotency, HttpOnly sessions/rate controls, redesigned monochrome React pages, benchmark CLI, OTLP privacy-aware spans, non-root Docker/Compose and CI.

Verified locally: original 30 tests; expanded suite and actual PostgreSQL four-worker/role-denial/lease/isolation checks; actual Chromium analyst journey, SQL/plan/provenance/mobile/reload. Final expanded test count and publication evidence are in PROGRESS. No paid model calls, live quality, persistent cloud deployment or actual customer feedback assumed. Demo mode is interactive synthetic deterministic SQL with browser-session history, not durable production storage.

Next: validate current-head remote CI/container/restart; protected PR and current-main checks; verify Vercel production demo; record exact hashes/URLs. Persistent production needs user cloud account and private database inputs. Live benchmark needs a privately configured OpenAI key and explicit opt-in. Never read another project's .env or copy its provider credentials. Original other flagship repos and portfolio remain untouched.
