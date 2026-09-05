# QueryPilot

[![CI](https://github.com/Akhilesh-Vangala/querypilot/actions/workflows/ci.yml/badge.svg)](https://github.com/Akhilesh-Vangala/querypilot/actions/workflows/ci.yml)

Natural-language-to-SQL copilot over a healthcare claims and provider-network star schema. The agent inspects tables, drafts a read-only `SELECT`, runs guardrails, executes the query, and returns an answer plus the SQL.

Scoring is execution accuracy: predicted SQL and gold SQL are both run against the warehouse, and the result sets are compared. A `DROP TABLE` prompt counts as a pass only if the agent refuses.

When `OPENAI_API_KEY` is unset, `StubLLM` compiles SQL from `app/agent/intents.py`. That compiler is not a copy of `eval/golden.py`; CI fails if the two SQL strings match.

## Guardrails

`run_sql` always calls `validate_sql` first. Rejected before execution:

- Anything that is not a single `SELECT` or `WITH ... SELECT`
- DML/DDL (`INSERT`, `UPDATE`, `DELETE`, `DROP`, …)
- Multiple statements and comment-smuggled writes
- Reads of `users` / `ask_logs`
- Unbounded `SELECT *` (capped at `LIMIT 500`)

## Warehouse

80 weeks from 2025-01-06, seed `42`. Regions: Northeast, West Coast. Employer groups: Acme Manufacturing, Northwind Retail, Vertex Technologies. Specialties: Primary Care, Cardiology, Orthopedic Surgery, Endocrinology, Oncology.

Planted patterns used by the golden set: Orthopedic Surgery has the highest declined-referral rate; the Northeast has a denser primary-care network than the West Coast; Q4 claims paid > Q1.

## Stack

- Python 3.13, FastAPI, SQLAlchemy 2, PostgreSQL (SQLite in pytest)
- React 18, TypeScript, Vite
- Ports: UI 3007, API 8007, Postgres 5437

## Quick start

```bash
git clone https://github.com/Akhilesh-Vangala/querypilot.git
cd querypilot
cp .env.example .env
docker compose up --build
```

Open http://localhost:3007. API: http://localhost:8007. Postgres: localhost:5437.

```bash
python3.13 -m venv .venv
./.venv/bin/python -m pip install -r backend/requirements.txt
cd backend && ../.venv/bin/python -m pytest -q
```

### Demo accounts

| Email | Password | Role |
|---|---|---|
| analyst@querypilot.example.com | analyst-password | analyst |
| admin@querypilot.example.com | admin-password | admin |

Default JWT secret is `change-me-in-production`. Local use only.

## Tests

`backend/tests/test_agent.py` requires 12/12 execution accuracy with the stub, including the refused DROP.

## License

MIT. See [LICENSE](LICENSE).
