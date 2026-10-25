# QueryPilot engineering documentation

[Working studio](https://querypilot-five.vercel.app/) · [Repository overview](../README.md)

| Read | What it establishes |
| --- | --- |
| [Technical report](TECHNICAL-REPORT.md) | Problem, architecture, execution flow, verification model and design tradeoffs |
| [System architecture](architecture/OVERVIEW.md) | Authority boundaries, graph actions, resource budgets and operating modes |
| [Semantic investigations](architecture/SEMANTIC-INVESTIGATIONS.md) | Metric compilation, weighted contributions and factor accounting |
| [Measured execution evidence](evaluation/EVIDENCE.md) | Actual test/browser/database results and exact-source evidence |
| [Evaluation methodology](evaluation/README.md) | Regression suites, independent oracles and scoring scope |
| [Repository and code map](development/LAYOUT.md) | Frontend/backend ownership and reproducible commands |
| [Product workspace](product/PRODUCT-WORKSPACE.md) | Navigation, reviewed rules, source retention and saved reports |
| [File formats](product/FILE-IMPORTS.md) | CSV, TSV, Excel, JSON and JSONL parsing and refusal boundaries |
| [Own-data contracts](product/USER-DATA.md) | Exact calculations, limits and report authentication |
| [Operations](operations/DEPLOYMENT.md) | Local persistent runtime and public serverless runtime |
| [Availability](operations/AVAILABILITY.md) | Synthetic health probes and recovery procedure |
| [Recordings](DEMO.md) | Actual browser videos, source hashes and reproducible capture |
| [Design decisions](DECISIONS.md) | Implementation choices and alternatives |

The public studio executes reviewed file analytics and synthetic guided warehouse investigations without provider calls. Private model transport and persistent workers are separate runtime components. Each report names the execution and verification scope it actually used.
