# QueryPilot repository layout

The checkout separates browser code, backend authority, reproducible tooling and documentation. Run commands from the repository root unless a command states otherwise.

| Directory/file | Responsibility |
| --- | --- |
| `backend/app/` | API, agent workflow, typed contracts, verification and persistent-runtime services. |
| `backend/tests/` | Unit, protocol, authority and recovery tests. |
| `backend/tests/` | Backend regression and integration cases. |
| `frontend/src/` | React product components, pages and styling. |
| `frontend/public/recordings/` | Native recording player, static poster and actual continuous WebM. |
| `scripts/browser_smoke.py` | Browser journeys across both sides of the application. |
| `scripts/` | Structural checks, benchmarks, deployment smoke and reproducible capture. |
| `docs/architecture/` | Current system/agent flow and authority boundaries. |
| `docs/operations/` | Development, deployment and public/private operating boundaries. |
| `docs/evaluation/` | Evaluation design, limits and linked engineering evidence. |
| `docs/project/` | Current handoff, release gates and progress; dated predecessors live under `history/`. |
| `docs/assets/`, `docs/demos/` | Documentation figures, actual capture previews and provenance manifests. |
| `docker-compose.yml`, `vercel.json` | Root deployment wiring; the Vercel launcher remains at the root for framework discovery. |

The React/Vite frontend has its own dependency lock and image. The Python backend has hashed runtime/development locks and its own image. Root Python metadata and the thin index.py entrypoint support the cohosted Vercel demonstration.

## Reorganization compatibility

Source moves update ASGI imports, asset resolution, dependency locks, test discovery, Docker context/copies, CI, source exports and Vercel includes. Existing HTTP routes, data directories and ignored runtime histories remain in place. Agent, SQL policy and warehouse semantics are unchanged by this layout increment.

The current paths supersede the dated commands in historical records. [Current quick start](../../README.md#run-locally) · [Branch workflow](../../BRANCHING.md).
