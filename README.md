# QueryPilot

Analytics questions over a claims and provider-network warehouse. A bounded LangGraph agent compiles guarded SQL against reviewed metrics. An independent check reconciles totals and contributions, and withholds a conclusion the query does not support.

[Open the app](https://querypilot-five.vercel.app/) · [Upload a file](https://querypilot-five.vercel.app/uploads) · [Architecture](docs/architecture/OVERVIEW.md) · [What the checks measure](docs/evaluation/README.md) · [Run locally](docs/operations/DEPLOYMENT.md)

<p align="center"><a href="https://github.com/Akhilesh-Vangala/querypilot/actions/workflows/ci.yml"><img src="https://github.com/Akhilesh-Vangala/querypilot/actions/workflows/ci.yml/badge.svg" alt="Required engineering checks"></a> &nbsp; Python · LangGraph · FastAPI · PostgreSQL</p>

The public app uses synthetic fixtures and does not call a model. A live benchmark has not been run, and no accuracy number is stated for one.

## Architecture

FastAPI admits the question and the metric scope. The agent may only compile and execute read-only SQL. Reconciliation of totals, weighted contributions, and factor accounting is separate from the model, and the report stays descriptive.

![System map: React workbench, FastAPI scope, bounded LangGraph, read-only SQL, independent reconciliation](docs/assets/diagrams/system-map.svg)

| Layer | Where | Responsibility |
| --- | --- | --- |
| Frontend | `frontend/` | Question, SQL, plan, and verification views |
| Agent | `backend/app/agents/analytics/` | Bounded LangGraph actions and model transport |
| Backend | `backend/app/` | Admission, guarded SQL, reconciliation, warehouse |

The agent package stays inside the backend import root. Reconciliation does not run inside the model.

## Repository layout

```text
frontend/                          React workbench
backend/app/agents/analytics/      LangGraph, tools, model transport
backend/app/                       API, warehouse, persistence, workers
```

## Run locally

```sh
git clone https://github.com/Akhilesh-Vangala/querypilot.git
cd querypilot
scripts/deployment/compose.sh up --build -d --wait db api worker frontend
```

Open **http://127.0.0.1:3007**. [Full deployment guide](docs/operations/DEPLOYMENT.md).

## Checks

```sh
python -m pytest -q backend/tests
npm ci --prefix frontend && npm run build --prefix frontend
python scripts/checks/check_repository.py
```

Public demos use guided synthetic fixtures (no live inference claim). Live model quality and customer production certification remain out of scope. [Evaluation](docs/evaluation/README.md) · [Demo notes](docs/DEMO.md)
