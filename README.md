# QueryPilot

Analytics questions over a claims and provider-network warehouse. A bounded LangGraph agent compiles guarded SQL against reviewed metrics. An independent check reconciles totals and contributions, and withholds a conclusion the query does not support.

[Open the app](https://querypilot-five.vercel.app/) · [Upload a file](https://querypilot-five.vercel.app/uploads) · [Architecture](docs/architecture/OVERVIEW.md) · [What the checks measure](docs/evaluation/README.md) · [Run locally](docs/operations/DEPLOYMENT.md)

<p align="center"><a href="https://github.com/Akhilesh-Vangala/querypilot/actions/workflows/ci.yml"><img src="https://github.com/Akhilesh-Vangala/querypilot/actions/workflows/ci.yml/badge.svg" alt="Required engineering checks"></a> &nbsp; Python · LangGraph · FastAPI · PostgreSQL</p>

The public app uses synthetic fixtures and does not call a model. A live benchmark has not been run, and no accuracy number is stated for one.

## Architecture

FastAPI admits the question and the metric scope. The agent may only compile and execute read-only SQL. Reconciliation of totals, weighted contributions, and factor accounting is separate from the model, and the report stays descriptive.

![System map: React workbench, FastAPI scope, bounded LangGraph, read-only SQL, independent reconciliation](docs/assets/diagrams/system-map.svg)

| Component | Responsibility |
| --- | --- |
| Frontend | Product pages, SQL/plan/verification tabs, comparison reports |
| Backend | FastAPI admission, bounded LangGraph actions, SQL policy |
| Independent checking | Read-only warehouse, receipts, contribution/Shapley accounting |
| Runtime | PostgreSQL workers and owner-fenced publication |

## Repository layout

```text
querypilot/
├── backend/          app, tests, requirements, docker
├── frontend/         React/TypeScript product UI
├── infrastructure/   containers
├── scripts/
├── docs/
└── .github/
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
