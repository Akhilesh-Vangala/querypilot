# Deployment and operations

## Local reproducible rehearsal

```sh
docker compose up --build -d --wait db api worker frontend
docker compose --profile test run --build --rm tests
```

Open `http://localhost:3007`. These are isolated development services with clearly labeled synthetic demo accounts and known local-only passwords. Database/API/UI ports bind to loopback. A one-shot owner process creates additive schema version 1, seeds synthetic warehouse/accounts and grants two unprivileged roles. API/worker startup does not reseed or create schema. Warehouse credentials permit SELECT on the eight approved relations; app credentials permit application state writes and cannot query facts. Images run as non-root. Docker volumes persist data across normal restarts. `docker compose down -v` **deletes this isolated database**; use it only for disposable rehearsal data.

Native development: Python 3.13, copy `.env.example` to ignored `.env`, create `.tools/`, install `backend/requirements-dev.txt` with `--require-hashes`, run `uvicorn app.main:app --app-dir backend --port 8007` from the repo root, and run `npm ci && npm run dev` under `frontend/`. The example uses SQLite and an embedded worker for development only. Production never uses that profile.

## Public Vercel demo

The root `index:app` entrypoint builds the actual React UI and serves a request-bounded synthetic investigation path. `pyproject.toml`/`uv.lock` select Python 3.13 and installed dependencies; container/native Python matches that minor. Configure a stable, randomly generated private `JWT_SECRET` in Vercel preview and production environments so sessions survive cold starts. Never upload `.env`, API keys, local databases or histories.

This demo allows actual guarded SQL over synthetic data, public plans, result provenance and browser-session history. Live AI is forcibly disabled in its entrypoint. Backend state is ephemeral, not durable production storage. Shared history reads are disabled. A ready Vercel build must still pass unauthenticated health/config, cookie login, actual investigation SQL, cross-browser history isolation and Chromium navigation checks before being promoted.

[Vercel FastAPI hosting](https://vercel.com/docs/frameworks/backend/fastapi) packages the app into one function; [Python runtime guidance](https://vercel.com/docs/functions/runtimes/python) documents packaging/runtime constraints. Persistent workers run in a container service, not inside the Vercel request lifecycle.

## Private production staging (account configuration required)

1. Provision persistent PostgreSQL with TLS and an owner credential used only by migration. Set unique secrets; copy `.env.production.example` locally and replace every placeholder. Default app and warehouse role passwords are unacceptable.
2. Run `python -m app.bootstrap` once with private migration URL and `APP_DATABASE_PASSWORD`/`WAREHOUSE_DATABASE_PASSWORD`; **omit `--demo-users`**. This bootstraps the documented synthetic dataset, not an arbitrary existing customer warehouse. Rotate/provision grants deliberately; do not point it blindly at a customer's existing schema.
3. Set `APP_ENVIRONMENT=production`, separate private application/warehouse URLs, private JWT secret, allowed frontend origin and all demo/startup flags false. API/worker require unprivileged, SELECT-only warehouse access; the API checks this at startup. Provision actual users through `python -m app.provision_user --email ... --name ...` with an interactive password prompt. No known demo users in production.
4. Deploy the non-root runtime image with separate API/worker commands on a persistent container service. Terminate TLS at the ingress. Route frontend `/api` to that service at the same public origin so HttpOnly/SameSite cookies work. Multiple API/worker replicas share Postgres state; a worker lease interruption fails closed and requires explicit resubmission.
5. Connect a private OTLP collector, database backups/PITR, restore drill, worker health checks and queue/error/latency alerts. API `/health` is liveness; `/ready` tests DB connectivity. Worker `python -m app.worker --health` checks its process heartbeat, not warehouse correctness or queue freshness.
6. Add the model key privately and explicitly opt into live mode. Run a bounded benchmark before allowing end users live requests. Aggregate per-run limits are not an organization-wide paid usage quota.

The repository provides deployment foundations and reproducible container checks; it does not provision AWS/Neon/Supabase accounts, purchase a plan or claim monitored persistent cloud execution. Backend provider/account, region, recurring budget and secret-manager configuration remain required inputs.

## Migration / rollback / recovery

Version 1 is additive `create_all` initialization plus a schema-version marker, not an Alembic upgrade chain. Preserve original warehouse tables/data. Further schema changes require explicit migrations, backup/restore verification and application compatibility tests. Do not use `seed_all(refresh_warehouse=True)` against persistent user data.

Rollback the API/worker image only to a version compatible with the current schema; pause new admissions, drain or mark affected jobs interrupted, take a database backup and preserve tables. Worker crash recovery retains public events and marks expired work `interrupted`; graph execution does not checkpoint or auto-replay live generation. Refreshing/restarting an API does not lose queued/completed investigations.

## Customer-release gates

Live held-out model quality and prompt-injection tests; general semantic correctness; organization/tenant identity and warehouse row permissions; OIDC/session revocation; global token/dollar admission budgets; managed migrations; retention/export/deletion; high-volume load/SLO tests; backup restore; observed cloud operation; actual analyst feedback. Current origin/content-length controls are useful foundations, not a comprehensive internet-facing security review. Infrastructure and model transport checks cannot replace these gates.
