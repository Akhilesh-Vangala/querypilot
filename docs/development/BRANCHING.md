# Repository workflow

`main` contains verified shared work. Create a short-lived `feat/`, `fix/`, `docs/` or `chore/` branch from synchronized main and open a pull request. Required checks are **Backend and policy**, **Frontend build**, and **Containers and PostgreSQL**. Squash merge only after the exact head passes all required checks and review conversations are resolved. Administrator bypass, force pushes and main deletion are disallowed.

The solo-maintainer workflow requires zero independent approving reviews; add reviewers when there is an actual collaborator. Preserve the original history. Automatically delete merged task branches; synchronize local main and remove only the task-owned branch after verifying tree equivalence. No empty long-lived development/release branches. Tags require a scoped, verified release; a public synthetic demo is not a production certification.

Dependabot groups `react`, `react-dom`, `@types/react` and `@types/react-dom` together for both version and security updates. Review their peer requirements as one compatibility boundary, including runtime and development dependencies. Validate with `npm ci`, `npm ls --all` and `npm run build` in `frontend/`; do not bypass conflicts with `--force` or `--legacy-peer-deps`. Major upgrades still require the normal CI and browser checks.
